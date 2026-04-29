#!/usr/bin/env python3
"""Raw レポート（kind: session/web/minutes）1件分のエントリを ingest-queue.jsonl に追記する。

呼び出し側（runner.sh / fetch-jina.sh / save.sh）が保存成功直後に実行。
JSONL への append-only 書き込みを使うため、複数プロセス並行でも安全
（POSIX 上、PIPE_BUF=512 以下の write は原子的）。

kind は引数 --kind 優先、未指定時は raw_path から自動推定する
（`raw/session/` `raw/web/` `raw/minutes/` のいずれを含むか）。

Usage:
    enqueue.py <raw_path> [--kind session|web|minutes] [--memories-dir PATH]

Stdout: 追記した行（デバッグ用）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


VALID_KINDS = ("session", "web", "minutes")


def detect_kind(raw_path: Path) -> str:
    """パスから kind を推定する。判別不能時は 'session' にフォールバック。

    パス例 `<memories_dir>/raw/session/YYYY-MM-DD/file.md` から `session` を返す。
    kind 値とディレクトリ名は完全一致（session / web / minutes）。
    """
    parts = raw_path.parts
    for i, p in enumerate(parts):
        if p == "raw" and i + 1 < len(parts):
            nxt = parts[i + 1]
            if nxt in VALID_KINDS:
                return nxt
    return "session"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("raw_path", help="生成された Raw レポートの絶対パス")
    p.add_argument(
        "--kind",
        choices=VALID_KINDS,
        default=None,
        help="kind を明示指定（未指定時は raw_path から自動推定）",
    )
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

    kind = args.kind or detect_kind(raw_path)

    # state は ~/.local/share/recording/state に永続化（OS 再起動でも pending が残る）。
    # 旧 /tmp/memories/state は wiki-runner.sh 起動時にマージされる。
    state_dir = Path.home() / ".local" / "share" / "recording" / "state"
    queue_path = state_dir / "ingest-queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "raw_path": str(raw_path),
        "kind": kind,
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
