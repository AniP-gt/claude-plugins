"""wiki-runner の ingest-queue.jsonl 操作。

bash wiki-runner.sh の 4 関数を Python 化:
  - purge_missing_entries: raw_path 不在エントリを dead-letter へ移送
  - read_pending_entries:  pending（retry_after 経過 / processing timeout 超過）エントリを取得
  - mark_processing:       指定 identity を status=processing に
  - update_queue_after_results: 結果に応じて成功削除 / 失敗 retry / max 超過 deadletter

queue ファイルは fcntl.flock で排他制御し、複数プロセス並行操作でも整合性を保つ。
identity tuple は (raw_path, kind, slug) で、kind=person のみ slug を区別子に使う。
"""
from __future__ import annotations

import fcntl
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


def _now_iso() -> str:
    return datetime.fromtimestamp(time.time(), timezone.utc).astimezone().isoformat(timespec="seconds")


def _parse_retry_epoch(value) -> float:
    """retry_after_epoch / retry_after / processing_started_at を秒単位の epoch に変換。

    数値ならそのまま、ISO 8601 文字列ならパースする。失敗時は 0.0。
    """
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _identity(entry: dict) -> tuple[str, str, str]:
    kind = entry.get("kind") or ""
    slug = entry.get("slug", "") if kind == "person" else ""
    return (entry.get("raw_path") or "", kind, slug)


def purge_missing_entries(queue_path: Path, log: Callable[[str], None] | None = None) -> int:
    """pending / processing で raw_path が不在のエントリを deadletter へ移送する。

    返り値: 移送した件数。
    deadletter path は queue_path と同じ親ディレクトリの ingest-deadletter.jsonl。
    """
    q = Path(queue_path)
    dead = q.parent / "ingest-deadletter.jsonl"
    if not q.exists():
        return 0

    now_dt = datetime.fromtimestamp(time.time(), timezone.utc).astimezone()
    remaining: list[str] = []
    dead_rows: list[str] = []

    with q.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        for line in f.read().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                remaining.append(line)
                continue
            status = d.get("status") or "pending"
            raw = d.get("raw_path", "")
            if status in ("pending", "processing") and raw and not Path(raw).is_file():
                d["status"] = "dead_letter"
                d["last_error"] = "raw_missing"
                d["last_failed_at"] = now_dt.isoformat(timespec="seconds")
                d["dead_lettered_at"] = now_dt.isoformat(timespec="seconds")
                for k in (
                    "processing_started_at",
                    "processing_started_epoch",
                    "runner_pid",
                    "retry_after",
                    "retry_after_epoch",
                ):
                    d.pop(k, None)
                dead_rows.append(json.dumps(d, ensure_ascii=False))
                continue
            remaining.append(json.dumps(d, ensure_ascii=False))
        f.seek(0)
        f.truncate()
        if remaining:
            f.write("\n".join(remaining) + "\n")

    if dead_rows:
        dead.parent.mkdir(parents=True, exist_ok=True)
        with dead.open("a", encoding="utf-8") as f:
            for row in dead_rows:
                f.write(row + "\n")
        if log:
            log(f"purge: dead-lettered {len(dead_rows)} raw_missing entries")
    return len(dead_rows)


def read_pending_entries(
    queue_path: Path,
    now_epoch: float | None = None,
    processing_timeout_seconds: int = 3600,
) -> list[dict]:
    """pending（retry 経過済み）+ processing（timeout 超過済み）エントリを返す。

    重複 identity (raw_path, kind, slug) は最初の 1 件だけ採用する（codex 二重実行防止）。
    """
    q = Path(queue_path)
    if not q.exists():
        return []
    now = float(now_epoch) if now_epoch is not None else time.time()

    seen: set[tuple[str, str, str]] = set()
    out: list[dict] = []
    with q.open(encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        lines = f.read().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = d.get("status") or "pending"
        if status == "pending":
            if _parse_retry_epoch(d.get("retry_after_epoch") or d.get("retry_after")) > now:
                continue
        elif status == "processing":
            started = _parse_retry_epoch(
                d.get("processing_started_epoch") or d.get("processing_started_at")
            )
            if started and now - started < processing_timeout_seconds:
                continue
        else:
            continue
        ident = _identity(d)
        if ident in seen:
            continue
        seen.add(ident)
        out.append(d)
    return out


def mark_processing(
    queue_path: Path,
    identities: list[tuple[str, str, str]],
    now_epoch: float | None = None,
    runner_pid: int | None = None,
) -> int:
    """指定 identity の status を processing に更新する。"""
    q = Path(queue_path)
    if not identities:
        return 0
    ids = set(identities)
    now = float(now_epoch) if now_epoch is not None else time.time()
    now_iso = datetime.fromtimestamp(now, timezone.utc).astimezone().isoformat(timespec="seconds")
    import os as _os

    pid = runner_pid if runner_pid is not None else _os.getpid()
    updated = 0

    q.parent.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    with q.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        for line in f.read().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                out.append(line)
                continue
            ident = _identity(d)
            if ident in ids and (d.get("status") or "pending") in ("pending", "processing"):
                d["status"] = "processing"
                d["processing_started_at"] = now_iso
                d["processing_started_epoch"] = now
                d["runner_pid"] = str(pid)
                updated += 1
            out.append(json.dumps(d, ensure_ascii=False))
        f.seek(0)
        f.truncate()
        if out:
            f.write("\n".join(out) + "\n")
    return updated


def update_queue_after_results(
    queue_path: Path,
    results: list[dict],
    max_attempts: int,
    retry_base_seconds: int = 300,
    now_epoch: float | None = None,
) -> tuple[int, int]:
    """codex 実行結果を反映する。

    results[i] = {"status": "success"|"failed", "label": str, "raw_path": str,
                  "kind": str, "slug": str}
    返り値: (deleted_count, deadletter_count)
    """
    q = Path(queue_path)
    dead = q.parent / "ingest-deadletter.jsonl"
    now = float(now_epoch) if now_epoch is not None else time.time()
    now_dt = datetime.fromtimestamp(now, timezone.utc).astimezone()

    successes: set[tuple[str, str, str]] = set()
    failures: dict[tuple[str, str, str], str] = {}
    for r in results:
        ident = (r.get("raw_path", ""), r.get("kind", ""), r.get("slug", ""))
        if r.get("status") == "success":
            successes.add(ident)
        elif r.get("status") == "failed":
            failures[ident] = r.get("label", "")

    if not successes and not failures:
        return 0, 0

    remaining: list[str] = []
    dead_rows: list[str] = []
    deleted = 0

    q.parent.mkdir(parents=True, exist_ok=True)
    with q.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        for line in f.read().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                remaining.append(line)
                continue
            ident = _identity(d)
            if ident in successes:
                deleted += 1
                continue
            if ident in failures:
                label = failures.get(ident, "")
                for k in ("processing_started_at", "processing_started_epoch", "runner_pid"):
                    d.pop(k, None)
                # raw 不在は永続失敗。attempt_count を増やさず即 dead-letter
                if label.startswith("missing:"):
                    d["last_error"] = "raw_missing"
                    d["last_failed_at"] = now_dt.isoformat(timespec="seconds")
                    d.pop("retry_after", None)
                    d.pop("retry_after_epoch", None)
                    dead_row = dict(d)
                    dead_row["status"] = "dead_letter"
                    dead_row["dead_lettered_at"] = now_dt.isoformat(timespec="seconds")
                    dead_rows.append(json.dumps(dead_row, ensure_ascii=False))
                    continue
                attempts = int(d.get("attempt_count") or 0) + 1
                d["attempt_count"] = attempts
                d["last_error"] = "codex_failed"
                d["last_failed_at"] = now_dt.isoformat(timespec="seconds")
                if attempts >= max_attempts:
                    dead_row = dict(d)
                    dead_row["status"] = "dead_letter"
                    dead_row["dead_lettered_at"] = now_dt.isoformat(timespec="seconds")
                    dead_rows.append(json.dumps(dead_row, ensure_ascii=False))
                    continue
                delay = retry_base_seconds * (2 ** max(0, attempts - 1))
                if delay > 86400:
                    delay = 86400
                retry_at = datetime.fromtimestamp(now + delay, timezone.utc).astimezone()
                d["status"] = "pending"
                d["retry_after"] = retry_at.isoformat(timespec="seconds")
                d["retry_after_epoch"] = now + delay
                remaining.append(json.dumps(d, ensure_ascii=False))
                continue
            remaining.append(json.dumps(d, ensure_ascii=False))
        f.seek(0)
        f.truncate()
        if remaining:
            f.write("\n".join(remaining) + "\n")

    if dead_rows:
        dead.parent.mkdir(parents=True, exist_ok=True)
        with dead.open("a", encoding="utf-8") as f:
            for row in dead_rows:
                f.write(row + "\n")

    return deleted, len(dead_rows)
