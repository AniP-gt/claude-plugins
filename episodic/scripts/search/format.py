#!/usr/bin/env python3
"""cocoindex search.py の出力を整形する。

入力（stdin、cocoindex の plain text 出力）:
    [0.823] /path/to/file.md
      preview text...
    [0.745] /path/to/other.md
      preview text...

出力（stdout、--format に応じて JSON または Markdown）:
- 各ヒットのフロントマターを読んで status/title/tags/keywords を含める
- --scope と --include-superseded でフィルタ
- 上位 --top 件に絞る
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


HIT_HEADER_RE = re.compile(r"^\[(\d+\.\d+)\]\s+(.+)$")


def parse_search_output(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        m = HIT_HEADER_RE.match(line)
        if m:
            if current is not None:
                hits.append(current)
            current = {"score": float(m.group(1)), "path": m.group(2).strip(), "snippet": ""}
        elif current is not None:
            stripped = line.strip()
            if stripped:
                current["snippet"] = (current["snippet"] + " " + stripped).strip()
    if current is not None:
        hits.append(current)
    return hits


def parse_frontmatter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    fm: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not k:
            continue
        fm[k] = v
    return fm


def absolutize(hit_path: str, memories_dir: Path, diary_dir: Path | None = None) -> Path:
    """cocoindex の出力 path（ソースルート相対 or 絶対）を絶対パスに正規化する。

    cocoindex は 2 つのソース（memories_dir / diary_dir）を 1 テーブルに混在させる。
    相対パスが `raw/diary/` で始まる場合だけ diary_dir 基準、それ以外は memories_dir 基準。
    """
    p = Path(hit_path)
    if p.is_absolute():
        return p
    if diary_dir is not None and p.parts[:2] == ("raw", "diary"):
        return diary_dir / p
    return memories_dir / p


def filter_scope(
    hit: dict[str, Any], memories_dir: Path, diary_dir: Path | None, scope: str
) -> bool:
    """scope 別フィルタ。

    kind 値とディレクトリ名は完全一致（session / web / minutes / diary）。

    パス構造:
      memories_dir/raw/session/YYYY-MM-DD/...md  -> kind=session
      memories_dir/raw/web/YYYY-MM-DD/...md       -> kind=web
      memories_dir/raw/minutes/YYYY-MM-DD/...md   -> kind=minutes
      memories_dir/wiki/...                        -> wiki
      diary_dir/raw/diary/YYYY-MM-DD/...md         -> kind=diary（ローカル限定）

    scope 値:
      all      -> 全ヒット採用（diary も含む）
      session  -> raw/session/ 配下のみ
      web      -> raw/web/ 配下のみ
      minutes  -> raw/minutes/ 配下のみ
      wiki     -> wiki/ 配下のみ
      diary    -> diary_dir/raw/diary/ 配下のみ
    """
    if scope == "all":
        return True
    abs_path = absolutize(hit["path"], memories_dir, diary_dir).resolve()
    if scope == "diary":
        if diary_dir is None:
            return False
        try:
            rel = abs_path.relative_to(diary_dir.resolve())
        except ValueError:
            return False
        parts = rel.parts
        return len(parts) >= 2 and parts[0] == "raw" and parts[1] == "diary"
    try:
        rel = abs_path.relative_to(memories_dir.resolve())
    except ValueError:
        return False
    parts = rel.parts
    if not parts:
        return False
    if scope == "wiki":
        return parts[0] == "wiki"
    if scope in ("session", "web", "minutes"):
        return len(parts) >= 2 and parts[0] == "raw" and parts[1] == scope
    return False


def filter_status(fm: dict[str, Any], include_superseded: bool) -> bool:
    if include_superseded:
        return True
    status = fm.get("status", "active")
    return status not in ("deprecated", "superseded")


def render_markdown(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "_検索結果なし_\n"
    lines = []
    for i, h in enumerate(hits, 1):
        fm = h.get("frontmatter", {})
        title = fm.get("title", Path(h["path"]).stem)
        status = fm.get("status", "active")
        tags = fm.get("tags", "")
        lines.append(f"### {i}. {title}  _(score: {h['score']:.3f})_")
        lines.append(f"- **path**: `{h['path']}`")
        lines.append(f"- **status**: {status}" + (f"  **tags**: {tags}" if tags else ""))
        if h.get("snippet"):
            lines.append(f"- **snippet**: {h['snippet'][:200]}")
        lines.append("")
    return "\n".join(lines)


def render_json(hits: list[dict[str, Any]]) -> str:
    return json.dumps(hits, ensure_ascii=False, indent=2)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--memories-dir", required=True, type=Path)
    p.add_argument(
        "--diary-dir",
        default=None,
        type=Path,
        help="kind: diary 専用ローカルルート（ローカル限定。指定時のみ diary scope が有効）",
    )
    p.add_argument(
        "--scope",
        default="all",
        choices=("all", "session", "web", "minutes", "wiki", "diary"),
    )
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--include-superseded", action="store_true")
    p.add_argument("--format", default="markdown", choices=("markdown", "json"))
    p.add_argument(
        "--no-dedupe",
        action="store_true",
        help="同一ファイル内の異なる chunk を全て返す（旧挙動）。"
        "既定では最高スコアの chunk のみ採用し、上位 N ファイル分を返す。",
    )
    args = p.parse_args()

    raw = sys.stdin.read()
    hits = parse_search_output(raw)

    # cocoindex の出力は chunk 単位。同一ファイル内の異なる chunk が top N を埋めると
    # 候補多様性が失われるため、既定で filename dedupe（最高スコア chunk のみ採用）する。
    # search.sh が --top を 3 倍 oversampling しているので、dedupe 後も十分な候補が残る。
    seen_paths: set[str] = set()
    filtered: list[dict[str, Any]] = []
    for h in hits:
        if not filter_scope(h, args.memories_dir, args.diary_dir, args.scope):
            continue
        abs_path = absolutize(h["path"], args.memories_dir, args.diary_dir)
        abs_path_str = str(abs_path)
        if not args.no_dedupe and abs_path_str in seen_paths:
            continue
        fm = parse_frontmatter(abs_path)
        if not filter_status(fm, args.include_superseded):
            continue
        h["path"] = abs_path_str
        h["frontmatter"] = fm
        filtered.append(h)
        seen_paths.add(abs_path_str)
        if len(filtered) >= args.top:
            break

    if args.format == "json":
        print(render_json(filtered))
    else:
        print(render_markdown(filtered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
