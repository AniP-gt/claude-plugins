#!/usr/bin/env python3
"""Raw レポート1件分のエントリを ingest-queue.jsonl に追記する。

呼び出し側（runner.sh）が Codex によるレポート書き出し成功直後に実行。
JSONL への append-only 書き込みを使うため、複数プロセス並行でも安全
（POSIX 上、PIPE_BUF=512 以下の write は原子的）。

Usage:
    enqueue.py <raw_path> [--memories-dir PATH]

Stdout: 追記した行（デバッグ用）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("raw_path", help="生成された Raw レポートの絶対パス")
    p.add_argument(
        "--memories-dir",
        default=Path(os.environ.get("MEMORIES_DIR", "/Volumes/memory")),
        type=Path,
    )
    args = p.parse_args()

    raw_path = Path(args.raw_path).resolve()
    if not raw_path.exists():
        print(f"raw not found: {raw_path}", file=sys.stderr)
        return 2

    state_dir = Path("/tmp/memories/state")
    queue_path = state_dir / "ingest-queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "raw_path": str(raw_path),
        "enqueued_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "pending",
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"

    # append-only。短い書き込みは POSIX で原子的なので flock 不要。
    with queue_path.open("a", encoding="utf-8") as f:
        f.write(line)

    print(line, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
