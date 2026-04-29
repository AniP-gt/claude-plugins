"""cocoindex プラグインキャッシュ配下の scripts ディレクトリを動的解決する。

cocoindex プラグインのキャッシュは `~/.claude/plugins/cache/hidetsugu-miya/cocoindex/<version>/scripts`
に展開されるが、バージョンは plugin update のたびに変わる。本ヘルパーはインストール済み
バージョンを semver 順で並べ、`.venv` を持つ最新版の `scripts/` を返す。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


@lru_cache(maxsize=1)
def resolve_cocoindex_scripts() -> Path | None:
    """cocoindex プラグイン scripts ディレクトリの絶対パスを返す。

    Returns:
        最新版の `scripts/` Path。見つからない場合は None。
    """
    base = Path.home() / ".claude/plugins/cache/hidetsugu-miya/cocoindex"
    if not base.exists():
        return None
    versions = sorted(
        (p for p in base.iterdir() if p.is_dir() and _VERSION_RE.match(p.name)),
        key=lambda p: tuple(int(x) for x in p.name.split(".")),
        reverse=True,
    )
    for v in versions:
        scripts = v / "scripts"
        if (scripts / ".venv").exists():
            return scripts
    return None


@lru_cache(maxsize=1)
def resolve_cocoindex_root() -> Path | None:
    """cocoindex プラグインルートの絶対パスを返す（scripts の親）。"""
    scripts = resolve_cocoindex_scripts()
    return scripts.parent if scripts else None
