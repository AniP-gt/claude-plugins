#!/usr/bin/env python3
"""Codex セッション要約失敗のリトライキュー操作 CLI / ライブラリ。

`~/.local/share/episodic/state/session-retry-queue.jsonl` を atomic rewrite で
管理する（最終行勝ち方式の append-only ではなく、effective state を 1 entry/session_id で保持）。
同時実行は `state/retry-queue.lock.d` の mkdir 方式で直列化する（macOS に flock がないため）。

CLI:
  retry_queue.py upsert <session_id> --cwd ... --transcript ... --first-ts ... \
                                     --report-path ... [--is-staged] --reason ...
  retry_queue.py remove <session_id>
  retry_queue.py list [--max-attempts N]   # active のみ JSONL で出力
  retry_queue.py promote-dead-letter <session_id>  # active から外し dead-letter ファイルへ追記

エントリ形式:
  {
    "session_id": "...",
    "cwd": "...",
    "transcript_path": "...",
    "first_ts": "...",
    "report_path": "...",
    "is_staged": false,
    "failure_reason": "usage_limit",
    "attempt_count": 1,
    "first_failed_at": "...",
    "last_attempted_at": "..."
  }
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".local" / "share" / "episodic" / "state"
QUEUE_PATH = STATE_DIR / "session-retry-queue.jsonl"
DEAD_LETTER_PATH = STATE_DIR / "session-retry-deadletter.jsonl"
LOCK_DIR = STATE_DIR / "retry-queue.lock.d"

LOCK_TIMEOUT_SEC = 10
LOCK_STALE_SEC = 60  # PID 不明かつ 60 秒以上経過したロックは奪取


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _acquire_lock() -> None:
    """mkdir 方式で QUEUE 全体の排他ロックを取得する。stale ロックは PID と age で判定して奪取。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + LOCK_TIMEOUT_SEC
    while True:
        try:
            LOCK_DIR.mkdir(parents=False, exist_ok=False)
            (LOCK_DIR / "pid").write_text(str(os.getpid()), encoding="utf-8")
            return
        except FileExistsError:
            pid_file = LOCK_DIR / "pid"
            stale = False
            try:
                old_pid = int(pid_file.read_text(encoding="utf-8").strip() or "0")
            except (OSError, ValueError):
                old_pid = 0
            if old_pid > 0:
                try:
                    os.kill(old_pid, 0)
                except OSError as exc:
                    if exc.errno == errno.ESRCH:
                        stale = True
            try:
                age = time.time() - LOCK_DIR.stat().st_mtime
            except OSError:
                age = 0.0
            if stale or age > LOCK_STALE_SEC:
                try:
                    if pid_file.exists():
                        pid_file.unlink()
                    LOCK_DIR.rmdir()
                except OSError:
                    pass
                continue
            if time.time() > deadline:
                raise TimeoutError(f"could not acquire {LOCK_DIR} within {LOCK_TIMEOUT_SEC}s (held by pid={old_pid})")
            time.sleep(0.1)


def _release_lock() -> None:
    try:
        pid_file = LOCK_DIR / "pid"
        if pid_file.exists():
            pid_file.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        pass


def _read_entries() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in QUEUE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _write_entries(entries: list[dict[str, Any]]) -> None:
    """tmp + rename で atomic に置き換える。"""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not entries:
        # 空でも 0 byte ファイルとして残す（呼び元が「ファイル存在 = キュー有効」を判定する場合への配慮）。
        QUEUE_PATH.write_text("", encoding="utf-8")
        return
    tmp = QUEUE_PATH.with_suffix(QUEUE_PATH.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, QUEUE_PATH)


def _append_dead_letter(entry: dict[str, Any]) -> None:
    DEAD_LETTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEAD_LETTER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cmd_upsert(args: argparse.Namespace) -> int:
    _acquire_lock()
    try:
        entries = _read_entries()
        existing = next((e for e in entries if e.get("session_id") == args.session_id), None)
        now = _now_iso()
        if existing is None:
            new_entry: dict[str, Any] = {
                "session_id": args.session_id,
                "cwd": args.cwd,
                "transcript_path": args.transcript,
                "first_ts": args.first_ts,
                "report_path": args.report_path,
                "is_staged": bool(args.is_staged),
                "failure_reason": args.reason,
                "attempt_count": 1,
                "first_failed_at": now,
                "last_attempted_at": now,
            }
            entries.append(new_entry)
        else:
            existing["cwd"] = args.cwd or existing.get("cwd", "")
            existing["transcript_path"] = args.transcript or existing.get("transcript_path", "")
            existing["first_ts"] = args.first_ts or existing.get("first_ts", "")
            existing["report_path"] = args.report_path or existing.get("report_path", "")
            existing["is_staged"] = bool(args.is_staged)
            existing["failure_reason"] = args.reason or existing.get("failure_reason", "unknown")
            existing["attempt_count"] = int(existing.get("attempt_count", 0)) + 1
            existing["last_attempted_at"] = now
            existing.setdefault("first_failed_at", now)
        _write_entries(entries)
    finally:
        _release_lock()
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    _acquire_lock()
    try:
        entries = _read_entries()
        before = len(entries)
        entries = [e for e in entries if e.get("session_id") != args.session_id]
        if len(entries) != before:
            _write_entries(entries)
    finally:
        _release_lock()
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    # 読みは lock 不要だが、書き込み中の中間状態を避けるため軽くロックする。
    _acquire_lock()
    try:
        entries = _read_entries()
    finally:
        _release_lock()
    for e in entries:
        if int(e.get("attempt_count", 0)) > args.max_attempts:
            continue
        sys.stdout.write(json.dumps(e, ensure_ascii=False) + "\n")
    return 0


def cmd_promote_dead_letter(args: argparse.Namespace) -> int:
    _acquire_lock()
    try:
        entries = _read_entries()
        target = next((e for e in entries if e.get("session_id") == args.session_id), None)
        if target is None:
            return 0
        entries = [e for e in entries if e.get("session_id") != args.session_id]
        target["promoted_at"] = _now_iso()
        _append_dead_letter(target)
        _write_entries(entries)
    finally:
        _release_lock()
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upsert")
    up.add_argument("session_id")
    up.add_argument("--cwd", default="")
    up.add_argument("--transcript", default="")
    up.add_argument("--first-ts", dest="first_ts", default="")
    up.add_argument("--report-path", dest="report_path", default="")
    up.add_argument("--is-staged", action="store_true")
    up.add_argument("--reason", default="unknown")
    up.set_defaults(func=cmd_upsert)

    rm = sub.add_parser("remove")
    rm.add_argument("session_id")
    rm.set_defaults(func=cmd_remove)

    ls = sub.add_parser("list")
    ls.add_argument("--max-attempts", type=int, default=5)
    ls.set_defaults(func=cmd_list)

    dl = sub.add_parser("promote-dead-letter")
    dl.add_argument("session_id")
    dl.set_defaults(func=cmd_promote_dead_letter)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
