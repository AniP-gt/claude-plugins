"""staging（fallback_dir）に積まれた __staged ファイルを列挙する。

bash sync-pending.sh の STAGED_TSV 構築ロジックを Python 化。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StagedEntry:
    path: Path
    kind: str  # session / web / minutes / diary / session-source


def scan_staged_files(fallback_dir: Path) -> list[StagedEntry]:
    """fallback_dir 配下の __staged 系ファイルを列挙する。

    走査経路:
      <fallback>/YYYY-MM-DD/*__staged.md           → kind: session
      <fallback>/web/YYYY-MM-DD/*__staged.md       → kind: web
      <fallback>/minutes/YYYY-MM-DD/*__staged.md   → kind: minutes
      <fallback>/diary/YYYY-MM-DD/*__staged.md     → kind: diary
      <fallback>/session-source/YYYY-MM-DD/*__staged.jsonl[.zst] → kind: session-source
    """
    out: list[StagedEntry] = []
    if not fallback_dir.is_dir():
        return out

    # session: depth=2、kind サブディレクトリは除外。
    excluded_dirs = {"web", "minutes", "diary", "session-source"}
    for date_dir in sorted(fallback_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        if date_dir.name in excluded_dirs:
            continue
        for f in sorted(date_dir.iterdir()):
            if f.is_file() and f.name.endswith("__staged.md"):
                out.append(StagedEntry(path=f, kind="session"))

    for kind in ("web", "minutes", "diary"):
        kind_root = fallback_dir / kind
        if not kind_root.is_dir():
            continue
        for date_dir in sorted(kind_root.iterdir()):
            if not date_dir.is_dir():
                continue
            for f in sorted(date_dir.iterdir()):
                if f.is_file() and f.name.endswith("__staged.md"):
                    out.append(StagedEntry(path=f, kind=kind))

    ss_root = fallback_dir / "session-source"
    if ss_root.is_dir():
        for date_dir in sorted(ss_root.iterdir()):
            if not date_dir.is_dir():
                continue
            for f in sorted(date_dir.iterdir()):
                if not f.is_file():
                    continue
                if f.name.endswith("__staged.jsonl") or f.name.endswith("__staged.jsonl.zst"):
                    out.append(StagedEntry(path=f, kind="session-source"))

    return out
