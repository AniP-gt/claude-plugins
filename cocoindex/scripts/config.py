"""CocoIndex プラグインの設定ローダ。

優先順位（強い順）:
  1. プロセス環境変数
  2. ~/.config/cocoindex/config.toml の対応キー
  3. ~/.config/cocoindex/secrets.env （API キーなど。dotenv 形式）
  4. ハードコードのデフォルト

main.py / search.py / hooks スクリプトから `apply_config_to_env()` を呼ぶことで、
以降は os.environ 経由でアクセスできる。

旧来の `~/.config/cocoindex/.env` (settings + secrets 混在) も後方互換で読み込む。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore

CONFIG_DIR = Path.home() / ".config" / "cocoindex"

# (toml パス, 環境変数キー)
_MAPPINGS: list[tuple[tuple[str, ...], str]] = [
    (("database", "url"), "COCOINDEX_DATABASE_URL"),
    (("embedding", "provider"), "EMBEDDING_PROVIDER"),
    (("embedding", "model"), "EMBEDDING_MODEL"),
    (("embedding", "dimension"), "EMBEDDING_DIMENSION"),
    (("embedding", "address"), "EMBEDDING_ADDRESS"),
    (("chunk", "size"), "CHUNK_SIZE"),
    (("chunk", "overlap"), "CHUNK_OVERLAP"),
    (("live", "update_interval_seconds"), "LIVE_UPDATE_INTERVAL"),
]


def _walk(d: dict, path: Iterable[str]) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def apply_config_to_env() -> None:
    """設定ファイルの値を環境変数として設定する（既存値は上書きしない）。

    これを起動時に1回呼ぶと、以降は環境変数 1 つだけを参照すればよい。
    """
    # 1) secrets.env を読み込む。
    # 「設定は上書き前提」のため override=True。cocoindex CLI が `--env-file` 既定 `./.env`
    # から先に拾った古い値があった場合も、~/.config/cocoindex/secrets.env の値で上書きする。
    load_dotenv(dotenv_path=CONFIG_DIR / "secrets.env", override=True)
    # 後方互換: 旧 .env（secrets + 設定が混在）。secrets.env が無い人向け。
    load_dotenv(dotenv_path=CONFIG_DIR / ".env", override=False)

    # 2) config.toml を読み、未設定の env 変数だけ流し込む
    config_path = CONFIG_DIR / "config.toml"
    if config_path.exists():
        try:
            with config_path.open("rb") as f:
                config = tomllib.load(f)
        except Exception as e:  # 解析失敗時は警告のみ（致命的にしない）
            print(f"[cocoindex/config] warn: failed to parse {config_path}: {e}", file=sys.stderr)
            config = {}
        for path, env_key in _MAPPINGS:
            if env_key in os.environ:
                continue
            value = _walk(config, path)
            if value is not None:
                os.environ[env_key] = str(value)

    # 3) cocoindex 1.0 互換: COCOINDEX_DB は COCOINDEX_DATABASE_URL から fallback
    if "COCOINDEX_DB" not in os.environ and "COCOINDEX_DATABASE_URL" in os.environ:
        os.environ["COCOINDEX_DB"] = os.environ["COCOINDEX_DATABASE_URL"]
