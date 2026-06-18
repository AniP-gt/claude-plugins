"""staging と canonical の衝突を自動解決する CLI ヘルパー。

sync-pending.sh の COLLISION 分岐で呼ばれ、frontmatter ベースで新旧を判定し、
古い側を `<dst_dir>/<basename>__r{N}.<ext>` にリビジョン化して staging を空にする。

判定優先度（kind=session/web/minutes/diary）:
  1. ended_at（ISO8601）
  2. updated_at（ISO8601）
  3. message_count（整数）
  4. mtime（fallback）

binary（kind=session-source, *.jsonl[.zst]）は frontmatter が無いため、
`--paired-winner` で兄弟 .md の解決結果を引き継ぐ。指定が無い場合は mtime fallback。

I/O プロトコル:
  入力: --src / --dst / --kind の引数
  出力: stdout に 1 行 JSON `{"action": ..., "winner": ..., "revision": ...}`
  exit code: 0=解決済み, 2=解決不能（人間判断要）, 3=引数エラー
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .frontmatter import parse as _fm_parse, patch as _fm_patch
except ImportError:  # pragma: no cover - direct CLI 経由のため
    from frontmatter import parse as _fm_parse, patch as _fm_patch  # type: ignore[no-redef]


MD_KINDS = {"session", "web", "minutes", "diary"}
BINARY_KINDS = {"session-source"}

# frontmatter から拾うキー（順序は判定優先度と一致）。
RANK_KEYS = ("ended_at", "updated_at", "message_count")


def _parse_frontmatter(path: Path) -> dict[str, str]:
    """frontmatter を dict で返す。lib.frontmatter.parse に委譲。"""
    return _fm_parse(path)


def _to_epoch(value: str | None) -> float | None:
    if not value:
        return None
    # 数値（epoch 秒）直接受け付け。
    try:
        return float(value)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _rank(path: Path, kind: str) -> tuple[float | None, float | None, int | None, float]:
    """(ended_epoch, updated_epoch, message_count, mtime) を返す。値が無いキーは None。"""
    mtime = path.stat().st_mtime if path.exists() else 0.0
    if kind in BINARY_KINDS:
        return (None, None, None, mtime)
    fm = _parse_frontmatter(path)
    ended = _to_epoch(fm.get("ended_at"))
    updated = _to_epoch(fm.get("updated_at"))
    try:
        msg_count = int(fm.get("message_count", "")) if fm.get("message_count") else None
    except ValueError:
        msg_count = None
    return (ended, updated, msg_count, mtime)


def _compare(src_rank, dst_rank) -> str | None:
    """src と dst の rank tuple から勝者を判定。

    Returns:
        "src" / "dst" / None（タイブレーク不能）
    """
    # ended_at / updated_at / message_count の順で比較。両方 None ならスキップ。
    for i in range(3):
        a, b = src_rank[i], dst_rank[i]
        if a is None and b is None:
            continue
        if a is None:
            return "dst"
        if b is None:
            return "src"
        if a > b:
            return "src"
        if a < b:
            return "dst"
    # mtime fallback。
    a, b = src_rank[3], dst_rank[3]
    if a > b:
        return "src"
    if a < b:
        return "dst"
    return None


def _strip_staged_suffix(name: str) -> str:
    for suf in ("__staged.md", "__staged.jsonl.zst", "__staged.jsonl"):
        if name.endswith(suf):
            return name[: -len(suf)] + suf[len("__staged"):]
    return name


def _split_basename_ext(name: str) -> tuple[str, str]:
    """basename を (stem, ext) に分割。.jsonl.zst のような複合拡張子も扱う。"""
    if name.endswith(".jsonl.zst"):
        return name[: -len(".jsonl.zst")], ".jsonl.zst"
    if name.endswith(".jsonl"):
        return name[: -len(".jsonl")], ".jsonl"
    if name.endswith(".md"):
        return name[: -len(".md")], ".md"
    # その他は単純分割。
    idx = name.rfind(".")
    if idx <= 0:
        return name, ""
    return name[:idx], name[idx:]


def _next_revision_path(dst: Path) -> Path:
    """`<dst_stem>__r{N}<ext>` の次空き連番を返す。"""
    stem, ext = _split_basename_ext(dst.name)
    parent = dst.parent
    n = 1
    while True:
        candidate = parent / f"{stem}__r{n}{ext}"
        if not candidate.exists():
            return candidate
        n += 1


def _write_md_with_frontmatter_patch(path: Path, patches: dict[str, str]) -> None:
    """既存 .md の frontmatter を patch する。lib.frontmatter.patch に委譲。"""
    _fm_patch(path, patches)


def retire_to_revision(canonical: Path, kind: str, *, new_canonical: Path | None = None) -> Path:
    """既存 canonical を `<basename>__r{N}.<ext>` に退避し、revision path を返す。

    - canonical 不在なら NoOp（canonical を返す呼び出し側責務）
    - .md なら frontmatter に status=superseded / superseded_at / superseded_by を書く
    - new_canonical を渡せば superseded_by に記す（同パスに新版を書く前提）

    呼び出し側は退避された revision path を新版の `supersedes` 値として使う。
    """
    if not canonical.exists():
        raise FileNotFoundError(f"canonical not found: {canonical}")
    revision_path = _next_revision_path(canonical)
    shutil.move(str(canonical), str(revision_path))
    if kind in MD_KINDS:
        patches: dict[str, str] = {
            "status": "superseded",
            "superseded_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        }
        if new_canonical is not None:
            patches["superseded_by"] = str(new_canonical)
        _write_md_with_frontmatter_patch(revision_path, patches)
    return revision_path


def resolve(src: Path, dst: Path, kind: str, paired_winner: str | None) -> dict[str, Any]:
    """衝突を解決し、結果を dict で返す。失敗時は exception を raise。"""
    if not src.is_file():
        raise FileNotFoundError(f"src not found: {src}")
    if not dst.exists():
        raise FileNotFoundError(f"dst not found: {dst}")
    if src.resolve() == dst.resolve():
        raise ValueError(f"src and dst are the same path: {src}")

    if paired_winner in ("src", "dst"):
        winner = paired_winner
    else:
        src_rank = _rank(src, kind)
        dst_rank = _rank(dst, kind)
        winner = _compare(src_rank, dst_rank)
        if winner is None:
            raise RuntimeError(f"cannot determine winner: src={src} dst={dst} (no tiebreaker)")

    revision_path = _next_revision_path(dst)

    loser_path: Path
    if winner == "src":
        # dst を revision に退避 → src を dst に移送。
        shutil.move(str(dst), str(revision_path))
        loser_path = revision_path
        if kind in MD_KINDS:
            _write_md_with_frontmatter_patch(
                revision_path,
                {
                    "status": "superseded",
                    "superseded_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "superseded_by": str(dst),
                },
            )
        # src → dst（rename / 跨 FS 両対応）。
        try:
            shutil.move(str(src), str(dst))
        except OSError as e:
            # 移送失敗時は revision を巻き戻す（best effort）。
            try:
                shutil.move(str(revision_path), str(dst))
            except OSError:
                pass
            raise RuntimeError(f"failed to move src→dst after revision: {e}") from e
        # 新 canonical (= src からの版) の supersedes フィールドを補正。
        if kind in MD_KINDS:
            _write_md_with_frontmatter_patch(
                dst,
                {
                    "supersedes": str(revision_path),
                },
            )
    else:
        # src を revision に退避（dst は触らない）。
        shutil.move(str(src), str(revision_path))
        loser_path = revision_path
        if kind in MD_KINDS:
            _write_md_with_frontmatter_patch(
                revision_path,
                {
                    "status": "superseded",
                    "superseded_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                    "superseded_by": str(dst),
                },
            )

    return {
        "action": "resolved",
        "kind": kind,
        "winner": winner,
        "canonical": str(dst),
        "revision": str(loser_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve staging↔canonical collision.")
    parser.add_argument("--src", required=True, help="staging 側パス（__staged.*）")
    parser.add_argument("--dst", required=True, help="canonical 側パス")
    parser.add_argument("--kind", required=True, choices=sorted(MD_KINDS | BINARY_KINDS))
    parser.add_argument(
        "--paired-winner",
        choices=("src", "dst"),
        default=None,
        help="兄弟 .md の解決結果（session-source 用）",
    )
    args = parser.parse_args(argv)

    try:
        result = resolve(Path(args.src), Path(args.dst), args.kind, args.paired_winner)
    except FileNotFoundError as e:
        print(json.dumps({"action": "error", "error": str(e)}), file=sys.stdout)
        return 3
    except (RuntimeError, ValueError, OSError) as e:
        print(json.dumps({"action": "error", "error": str(e)}), file=sys.stdout)
        return 2

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
