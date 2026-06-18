#!/usr/bin/env python3
"""fallback_dir に staged 済みの Raw を MEMORIES_DIR/raw/<kind>/ へ移送する。

bash bin/sync-pending.sh の完全 Python 化。

起動条件:
  - SessionStart hook（fire-and-forget で呼ばれる）
  - 手動実行: bin/sync_pending.py
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib import config as cfg
from lib import resolve_collision
from lib.lockfile import MkdirLock
from lib.log_rotate import rotate_log_if_needed
from lib.notify import Notifier, default_notifier
from lib.staging_scanner import StagedEntry, scan_staged_files


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _strip_staged_suffix(name: str) -> str:
    for suf in ("__staged.md", "__staged.jsonl.zst", "__staged.jsonl"):
        if name.endswith(suf):
            return name[: -len(suf)] + suf[len("__staged"):]
    return name


def _paired_key(src: Path) -> str:
    date_dir = src.parent.name
    base = src.name
    for suf in ("__staged.md", "__staged.jsonl.zst", "__staged.jsonl"):
        if base.endswith(suf):
            stem = base[: -len(suf)]
            return f"{date_dir}/{stem}"
    return f"{date_dir}/{base}"


class Logger:
    def __init__(self, log_file: Path) -> None:
        self.log_file = log_file
        log_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(log_file.parent, 0o700)
        except OSError:
            pass

    def __call__(self, msg: str) -> None:
        try:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{_now_iso()}] {msg}\n")
        except OSError:
            pass


def _enqueue(plugin_root: Path, target: Path, kind: str, log: Logger) -> None:
    enqueue_py = plugin_root / "wiki" / "enqueue.py"
    if not enqueue_py.is_file():
        log(f"warn: enqueue script not found: {enqueue_py}")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(enqueue_py), str(target), "--kind", kind],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            log(f"warn: enqueue failed (kind={kind}) for {target}: {result.stderr.strip()}")
    except (OSError, subprocess.SubprocessError) as e:
        log(f"warn: enqueue exception (kind={kind}) for {target}: {e}")


def _kick_wiki_runner(plugin_root: Path, log_dir: Path) -> None:
    """wiki kick-runner を detached で起動。Python 版優先 + bash fallback。"""
    py_kick = plugin_root / "wiki" / "kick_runner.py"
    sh_kick = plugin_root / "wiki" / "kick-runner.sh"
    runner_log = log_dir / "wiki-runner.log"
    cmd: list[str] | None = None
    if py_kick.is_file():
        cmd = [sys.executable, str(py_kick)]
    elif sh_kick.is_file() and os.access(sh_kick, os.X_OK):
        cmd = [str(sh_kick)]
    if cmd is None:
        return
    try:
        with runner_log.open("ab") as logf:
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
    except (OSError, FileNotFoundError):
        pass


def _process_entry(
    entry: StagedEntry,
    memories_dir: Path,
    paired_winners: dict[str, str],
    log: Logger,
    counters: dict[str, int],
    moved: list[tuple[Path, str]],
) -> None:
    src = entry.path
    kind = entry.kind
    if not src.is_file():
        return
    date_dir = src.parent.name
    base = src.name
    normal_base = _strip_staged_suffix(base)
    dst_dir = memories_dir / "raw" / kind / date_dir
    dst = dst_dir / normal_base
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if dst.exists():
        # dst は SMB 越しで全読みが高いため、まずサイズ比較で短絡する。
        # サイズが異なれば内容も必ず異なるので SHA-256 計算を省く。
        try:
            same_size = src.stat().st_size == dst.stat().st_size
        except OSError:
            same_size = False
        if same_size:
            src_hash = _sha256(src)
            dst_hash = _sha256(dst)
        else:
            src_hash = dst_hash = None
        if src_hash and src_hash == dst_hash:
            try:
                src.unlink()
            except OSError:
                pass
            counters["duplicate"] += 1
            log(f"duplicate, removed staging (kind={kind}): {src}")
            return
        paired = None
        if kind == "session-source":
            paired = paired_winners.get(_paired_key(src))
        try:
            result = resolve_collision.resolve(src, dst, kind, paired)
            counters["collision_resolved"] += 1
            log(f"auto-resolved (kind={kind}): {result}")
            if result.get("winner") == "src":
                counters["moved"] += 1
                moved.append((dst, kind))
            if kind != "session-source" and result.get("winner"):
                paired_winners[_paired_key(src)] = result["winner"]
        except (RuntimeError, ValueError, FileNotFoundError, OSError) as e:
            counters["collision_unresolved"] += 1
            counters["collided"] += 1
            log(f"COLLISION unresolved (kind={kind}): {src} vs {dst}: {e}")
        return

    # 移送
    try:
        shutil.move(str(src), str(dst))
        counters["moved"] += 1
        moved.append((dst, kind))
        log(f"moved (kind={kind}): {src} -> {dst}")
    except OSError:
        # cross-FS fallback
        try:
            shutil.copy2(str(src), str(dst))
            src.unlink()
            counters["moved"] += 1
            moved.append((dst, kind))
            log(f"copied(cross-fs, kind={kind}): {src} -> {dst}")
        except OSError as e:
            counters["failed"] += 1
            log(f"FAILED (kind={kind}): {src} -> {dst}: {e}")


def _cleanup_empty_dirs(root: Path) -> None:
    if not root.is_dir():
        return
    for dirpath in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        try:
            dirpath.rmdir()
        except OSError:
            pass


def run(notifier: Notifier | None = None) -> int:
    plugin_root = REPO_ROOT
    log_dir = Path.home() / ".local" / "state" / "episodic" / "logs"
    state_dir = Path.home() / ".local" / "share" / "episodic" / "state"
    log_file = log_dir / "session-sync.log"
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(log_dir, 0o700)
    except OSError:
        pass
    rotate_log_if_needed(log_file)
    log = Logger(log_file)

    lock = MkdirLock(state_dir / "sync-pending.lock.d")
    if not lock.acquire():
        log("skip: sync-pending lock held")
        return 0

    try:
        memories_dir = cfg.resolve_memories_dir()
        fallback_dir = cfg.resolve_fallback_dir()
        mount_ok = cfg.is_mount_active(memories_dir)
        if not mount_ok:
            log(f"skip: canary not present at $MEMORIES_DIR ({memories_dir})")
            return 0
        if not fallback_dir.is_dir():
            log(f"skip: fallback dir does not exist: {fallback_dir}")
            return 0

        entries = scan_staged_files(fallback_dir)
        if not entries:
            log(f"skip: no staged files in {fallback_dir}")
            return 0

        log(f"sync start: {len(entries)} staged file(s) across session/web/minutes/diary")
        counters = {
            "moved": 0,
            "collided": 0,
            "collision_resolved": 0,
            "collision_unresolved": 0,
            "duplicate": 0,
            "failed": 0,
        }
        moved: list[tuple[Path, str]] = []
        paired_winners: dict[str, str] = {}

        for entry in entries:
            _process_entry(entry, memories_dir, paired_winners, log, counters, moved)

        _cleanup_empty_dirs(fallback_dir)

        log(
            "sync done: "
            f"moved={counters['moved']} duplicate={counters['duplicate']} "
            f"collided={counters['collided']} auto_resolved={counters['collision_resolved']} "
            f"failed={counters['failed']}"
        )

        if moved:
            for target, kind in moved:
                if kind == "session-source":
                    continue
                _enqueue(plugin_root, target, kind, log)
            _kick_wiki_runner(plugin_root, log_dir)

        notifier = notifier or default_notifier()
        if counters["collided"] > 0 or counters["failed"] > 0:
            notifier.notify(
                "衝突あり",
                f"{counters['collided']} 件衝突 / {counters['failed']} 件失敗。手動確認が必要です。ログ: {log_file}",
                sound="Basso",
            )
        elif counters["collision_resolved"] > 0 and counters["moved"] > 0:
            notifier.notify(
                "同期完了（自動解決あり）",
                f"{counters['moved']} 件移送 / {counters['collision_resolved']} 件は新旧判定して旧版をリビジョン化。",
            )
        elif counters["collision_resolved"] > 0:
            notifier.notify(
                "衝突を自動解決",
                f"{counters['collision_resolved']} 件の重複を新旧判定して旧版をリビジョン化しました。",
            )
        elif counters["moved"] > 0:
            notifier.notify(
                "同期完了",
                f"{counters['moved']} 件の staged を共有へ移送しました。",
            )

        return 0
    finally:
        lock.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync staged files to MEMORIES_DIR.")
    parser.parse_args(argv)
    return run()


if __name__ == "__main__":
    sys.exit(main())
