#!/usr/bin/env python3
"""Raw レポート（kind: session/web/minutes/diary）1件分のエントリを ingest-queue.jsonl に追記する。

呼び出し側（runner.sh / fetch-jina.sh / save.sh）が保存成功直後に実行。
同一 raw_path の pending エントリが既にあれば追記をスキップする（dedupe）。
追記前に flock(LOCK_EX) を取って read→check→append を直列化し、
複数プロセス並行 enqueue でも重複を生まない。

kind は引数 --kind 優先、未指定時は raw_path から自動推定する
（`raw/session/` `raw/web/` `raw/minutes/` `raw/diary/` のいずれを含むか）。

Usage:
    enqueue.py <raw_path> [--kind session|web|minutes|diary] [--memories-dir PATH]

終了コード:
    0 → 追記成功 または 重複スキップ（どちらも正常終了）
    2 → raw_path が存在しない

Stdout: 追記した行（デバッグ用）。重複スキップ時は "skip: ..." を stderr に出力。
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime
from pathlib import Path


VALID_KINDS = ("session", "web", "minutes", "diary")


def detect_kind(raw_path: Path) -> str:
    """パスから kind を推定する。判別不能時は 'session' にフォールバック。

    パス例 `<memories_dir>/raw/session/YYYY-MM-DD/file.md` から `session` を返す。
    kind 値とディレクトリ名は完全一致（session / web / minutes / diary）。
    diary は memories_dir ではなく diary_dir 配下だが、`raw/diary/` 構造を
    揃えているためルート非依存でこの推定が機能する。
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

    # state は ~/.local/share/episodic/state に永続化（OS 再起動でも pending が残る）。
    state_dir = Path.home() / ".local" / "share" / "episodic" / "state"
    queue_path = state_dir / "ingest-queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "raw_path": str(raw_path),
        "kind": kind,
        "enqueued_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "pending",
    }
    line = json.dumps(entry, ensure_ascii=False) + "\n"

    # flock で read→check→append を直列化して並行 enqueue 競合と重複を防ぐ。
    # ファイルが無くても a+ で作成されるため、queue_path 不在時も問題なし。
    with queue_path.open("a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        for existing in f:
            existing = existing.strip()
            if not existing:
                continue
            try:
                d = json.loads(existing)
            except json.JSONDecodeError:
                continue
            if d.get("raw_path") == str(raw_path) and d.get("status") == "pending":
                print(f"skip: duplicate pending entry for {raw_path}", file=sys.stderr)
                return 0
        f.seek(0, os.SEEK_END)
        f.write(line)

    print(line, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
