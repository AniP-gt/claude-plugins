"""compass プラグイン専用 cocoindex 1.0 インデクサー（コードベースのセマンティック検索）

cocoindex 1.0 CLI で起動する想定:

  cocoindex update -f main.py:CompassIndex_<host>_<project>            # batch
  cocoindex update -L -f main.py:CompassIndex_<host>_<project>         # live mode

設定は環境変数で渡す:
  SOURCE_PATH         (必須) インデックス対象ディレクトリ
  INDEX_NAME          (任意) プロジェクト名。未指定時は SOURCE_PATH のベース名
  PATTERNS            (任意, csv) 対象ファイルパターン（既定: "**/*.rb"）
  EXCLUDE             (任意, csv) 追加除外パターン
  NO_DEFAULT_EXCLUDES (任意) 真値ならデフォルト除外を無効化
  CHUNK_SIZE          (任意) 既定 800
  CHUNK_OVERLAP       (任意) 既定 200
  EMBEDDING_PROVIDER  voyage|openai|ollama (既定 voyage)
  EMBEDDING_MODEL     既定 voyage-code-3
  EMBEDDING_DIMENSION 出力次元（Matryoshka 対応モデル用）
  EMBED_PREFIX_FILEPATH  真値ならチャンク先頭にファイルパスを付与して埋め込み（既定 1）

DB / API キーは以下の fallback chain で解決:
  1. プロセス環境変数（最優先）
  2. ~/.config/compass/secrets.env (compass 専用)
  3. ~/.config/compass/.env       (compass 専用、後方互換)
  4. ~/.config/cocoindex/secrets.env (共通 hub、fallback)

専用 DB URL: COMPASS_DATABASE_URL（既定 postgres://postgres:postgres@localhost:15432/compass）
"""
from __future__ import annotations

import os
import pathlib
import re
import socket
import sys
from dataclasses import dataclass
from typing import Annotated, AsyncIterator

import asyncpg
import cocoindex as coco
from cocoindex.connectors import localfs, postgres
from cocoindex.connectors.postgres import PgType
from cocoindex.connectors.postgres._target import _vector_encoder
from cocoindex.ops.litellm import LiteLLMEmbedder
from cocoindex.ops.text import RecursiveSplitter
from cocoindex.resources.chunk import Chunk
from cocoindex.resources.file import FileLike, PatternFilePathMatcher
from cocoindex.resources.id import IdGenerator
from numpy.typing import NDArray
from dotenv import load_dotenv

# Secrets fallback chain:
# 優先順位: 既存環境変数 > ~/.config/compass/{secrets.env,.env} > ~/.config/cocoindex/secrets.env (hub)
#
# cocoindex CLI が先に ~/.env を読み込んで古い VOYAGE_API_KEY 等が紛れ込むことがあるため、
# プラグイン管理下にある secrets.env で確実に上書きする。
# 優先順位は「compass 側で明示設定した値」を最優先にしたいので、cocoindex 側を先に override=True
# で読み込み、その後 compass 側を override=True で読む。compass 側でコメントアウトされたキーは
# 何も書き換えないので、cocoindex 側で読み込んだ値が残る。
_COMPASS_CFG_DIR = pathlib.Path.home() / ".config" / "compass"
_COCOINDEX_CFG_DIR = pathlib.Path.home() / ".config" / "cocoindex"

load_dotenv(dotenv_path=_COCOINDEX_CFG_DIR / "secrets.env", override=True)
load_dotenv(dotenv_path=_COMPASS_CFG_DIR / ".env", override=True)
load_dotenv(dotenv_path=_COMPASS_CFG_DIR / "secrets.env", override=True)

# compass 専用 config を auto-provision して読み込む（~/.config/compass/cocoindex.toml）
_COMPASS_CONFIG = _COMPASS_CFG_DIR / "cocoindex.toml"
_TEMPLATE = pathlib.Path(__file__).resolve().parent / "templates" / "compass_config.toml.example"

if not _COMPASS_CONFIG.exists() and _TEMPLATE.exists():
    _COMPASS_CFG_DIR.mkdir(parents=True, exist_ok=True)
    _COMPASS_CONFIG.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

# compass 用 toml -> 環境変数への展開（既存 env は上書きしない）
_COMPASS_MAPPINGS: list[tuple[tuple[str, ...], str]] = [
    (("embedding", "provider"), "EMBEDDING_PROVIDER"),
    (("embedding", "model"), "EMBEDDING_MODEL"),
    (("embedding", "dimension"), "EMBEDDING_DIMENSION"),
    (("embedding", "address"), "EMBEDDING_ADDRESS"),
    (("chunk", "size"), "CHUNK_SIZE"),
    (("chunk", "overlap"), "CHUNK_OVERLAP"),
    (("index", "exclude"), "COMPASS_EXCLUDE"),
    (("embed", "prefix_filepath"), "EMBED_PREFIX_FILEPATH"),
]

if _COMPASS_CONFIG.exists():
    if sys.version_info >= (3, 11):
        import tomllib  # type: ignore
    else:  # pragma: no cover
        import tomli as tomllib  # type: ignore
    try:
        with _COMPASS_CONFIG.open("rb") as _f:
            _compass_cfg = tomllib.load(_f)
        for _path, _env_key in _COMPASS_MAPPINGS:
            if _env_key in os.environ:
                continue
            _cur: object = _compass_cfg
            for _k in _path:
                if not isinstance(_cur, dict) or _k not in _cur:
                    _cur = None
                    break
                _cur = _cur[_k]
            if _cur is not None:
                os.environ[_env_key] = str(_cur)
    except Exception as _e:
        print(f"[compass] warn: failed to parse {_COMPASS_CONFIG}: {_e}", file=sys.stderr)


DEFAULT_EXCLUDES = [
    "**/.*",
    "**/log/**",
    "**/tmp/**",
    "**/coverage/**",
    "**/vendor/bundle/**",
    "**/.gem_rbs_collection/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/.venv/**",
    "**/__pycache__/**",
    "**/target/**",
]


def _bool_env(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def _csv(name: str, default: str = "") -> list[str]:
    return [s.strip() for s in os.environ.get(name, default).split(",") if s.strip()]


def _host_prefix() -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()


def _index_name() -> str:
    raw = os.environ.get("INDEX_NAME") or pathlib.Path(SOURCE_PATH).resolve().name
    host = _host_prefix()
    return raw if raw.startswith(f"{host}_") else f"{host}_{raw}"


def _table_name(index_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name).lower()
    return f"compassindex_{sanitized}__chunks"


def _app_name(index_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name)
    return f"CompassIndex_{sanitized}"


SOURCE_PATH = os.environ.get("SOURCE_PATH")
if not SOURCE_PATH:
    raise RuntimeError("SOURCE_PATH 環境変数が必要です")

INCLUDED = _csv("PATTERNS", default="**/*.rb")
EXCLUDED = ([] if _bool_env("NO_DEFAULT_EXCLUDES") else list(DEFAULT_EXCLUDES))
EXCLUDED.extend(_csv("EXCLUDE"))
EXCLUDED.extend([s.strip() for s in os.environ.get("COMPASS_EXCLUDE", "").split(",") if s.strip()])

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))

# 検索精度を上げるためにファイルパスをチャンク先頭にメタデータとして付与する。
# cAST 論文（Recall@5 +1.8〜4.3pt 改善）の主要寄与要因。
EMBED_PREFIX_FILEPATH = os.environ.get("EMBED_PREFIX_FILEPATH", "1").lower() in ("1", "true", "yes")

# 拡張子 → tree-sitter / RecursiveSplitter で認識される言語名
# 注意: cocoindex の RecursiveSplitter は拡張子を自動で言語に解決しない。
# フル名（"ruby" 等）を渡さないとプレーンテキスト扱いになる。
EXT_TO_LANG = {
    "rb": "ruby",
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "go": "go",
    "rs": "rust",
    "java": "java",
    "kt": "kotlin",
    "swift": "swift",
    "php": "php",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "hpp": "cpp",
    "cs": "csharp",
    "scala": "scala",
    "sh": "bash",
    "bash": "bash",
    "zsh": "bash",
    "md": "markdown",
    "markdown": "markdown",
    "html": "html",
    "css": "css",
    "scss": "css",
    "yml": "yaml",
    "yaml": "yaml",
    "toml": "toml",
    "json": "json",
    "xml": "xml",
    "sql": "sql",
}

# halfvec を使えば pgvector の 4000dim 上限まで HNSW index が利用できる。
_DIM_ENV = os.environ.get("EMBEDDING_DIMENSION")
EMBEDDING_DIMENSION = int(_DIM_ENV) if _DIM_ENV else 1024
HALFVEC_PG_TYPE = PgType(f"halfvec({EMBEDDING_DIMENSION})", encoder=_vector_encoder)

INDEX = _index_name()
TABLE = _table_name(INDEX)
APP = _app_name(INDEX)

# compass 専用 database への接続 URL。COMPASS_DATABASE_URL を最優先し、
# 未設定の場合は localhost の compass DB を既定値とする。
DATABASE_URL = os.environ.get(
    "COMPASS_DATABASE_URL",
    "postgres://postgres:postgres@localhost:15432/compass",
)

# cocoindex 1.0 は自身の tracking テーブルを格納する DB を COCOINDEX_DB から取得する。
# compass プラグインは compass database 内に tracking も置くため、未設定なら DATABASE_URL に揃える。
os.environ.setdefault("COCOINDEX_DB", DATABASE_URL)


def _build_embedder() -> LiteLLMEmbedder:
    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage").lower()
    model = os.environ.get("EMBEDDING_MODEL", "voyage-code-3")
    dim_env = os.environ.get("EMBEDDING_DIMENSION")
    kwargs: dict = {"input_type": "document"}
    if dim_env:
        kwargs["dimensions"] = int(dim_env)
    if provider == "voyage":
        litellm_model = f"voyage/{model}"
    elif provider == "openai":
        litellm_model = model
    elif provider == "ollama":
        litellm_model = f"ollama/{model}"
        addr = os.environ.get("EMBEDDING_ADDRESS")
        if addr:
            kwargs["api_base"] = addr
    else:
        litellm_model = f"{provider}/{model}"
    return LiteLLMEmbedder(litellm_model, **kwargs)


PG_DB = coco.ContextKey[asyncpg.Pool](f"{INDEX}__db")
EMBEDDER = coco.ContextKey[LiteLLMEmbedder](f"{INDEX}__embedder", detect_change=True)

_splitter = RecursiveSplitter()


@dataclass
class CompassChunk:
    id: int
    filename: str
    chunk_text: str
    embedding: Annotated[NDArray, EMBEDDER, HALFVEC_PG_TYPE]


@coco.lifespan
async def _lifespan(builder: coco.EnvironmentBuilder) -> AsyncIterator[None]:
    async with await asyncpg.create_pool(DATABASE_URL) as pool:
        builder.provide(PG_DB, pool)
        builder.provide(EMBEDDER, _build_embedder())
        yield


@coco.fn
async def _process_chunk(
    chunk: Chunk,
    filename: pathlib.PurePath,
    id_gen: IdGenerator,
    table: postgres.TableTarget[CompassChunk],
) -> None:
    embedder = coco.use_context(EMBEDDER)
    # メタデータ（ファイルパス）を埋め込み計算用テキストの先頭にだけ付与する。
    # 保存する chunk_text 自体は元の本文のまま（検索結果プレビューが汚れないようにする）。
    if EMBED_PREFIX_FILEPATH:
        embed_text = f"# file: {filename}\n{chunk.text}"
    else:
        embed_text = chunk.text
    table.declare_row(
        row=CompassChunk(
            id=await id_gen.next_id(chunk.text),
            filename=str(filename),
            chunk_text=chunk.text,
            embedding=await embedder.embed(embed_text),
        ),
    )


@coco.fn(memo=True)
async def _process_file(
    file: FileLike,
    table: postgres.TableTarget[CompassChunk],
) -> None:
    text = await file.read_text()
    suffix = file.file_path.path.suffix.lstrip(".").lower()
    language = EXT_TO_LANG.get(suffix)
    chunks = _splitter.split(
        text,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        language=language,
    )
    id_gen = IdGenerator()
    await coco.map(_process_chunk, chunks, file.file_path.path, id_gen, table)


@coco.fn
async def _app_main(sourcedir: pathlib.Path) -> None:
    target_table = await postgres.mount_table_target(
        PG_DB,
        table_name=TABLE,
        table_schema=await postgres.TableSchema.from_class(
            CompassChunk, primary_key=["id"]
        ),
        pg_schema_name="public",
    )
    # halfvec 列に対応する operator class (`halfvec_cosine_ops`) を SQL で直接付与する。
    # cocoindex の declare_vector_index は vector_cosine_ops 固定で halfvec に非対応。
    target_table.declare_sql_command_attachment(
        name="hnsw_embedding",
        setup_sql=(
            f'CREATE INDEX IF NOT EXISTS "{TABLE}__embedding_hnsw" '
            f'ON public."{TABLE}" '
            f'USING hnsw (embedding halfvec_cosine_ops);'
        ),
        teardown_sql=f'DROP INDEX IF EXISTS public."{TABLE}__embedding_hnsw";',
    )

    # ハイブリッド検索（dense + BM25 RRF → rerank）用に chunk_text の tsvector 生成列と
    # GIN index を declare する。chunk_tsv は STORED 生成列なので cocoindex の upsert/delete に
    # 影響されず追従する。to_tsvector('simple') は言語依存のステミングを行わないため、
    # 日本語混じり文書でも記号トークンの完全一致で BM25 が機能する。
    target_table.declare_sql_command_attachment(
        name="chunk_tsv_column",
        setup_sql=(
            f'ALTER TABLE public."{TABLE}" '
            f"ADD COLUMN IF NOT EXISTS chunk_tsv tsvector "
            f"GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED;"
        ),
        teardown_sql=f'ALTER TABLE public."{TABLE}" DROP COLUMN IF EXISTS chunk_tsv;',
    )
    target_table.declare_sql_command_attachment(
        name="gin_chunk_tsv",
        setup_sql=(
            f'CREATE INDEX IF NOT EXISTS "{TABLE}__chunk_tsv_gin" '
            f'ON public."{TABLE}" USING GIN (chunk_tsv);'
        ),
        teardown_sql=f'DROP INDEX IF EXISTS public."{TABLE}__chunk_tsv_gin";',
    )

    files = localfs.walk_dir(
        sourcedir,
        recursive=True,
        path_matcher=PatternFilePathMatcher(
            included_patterns=INCLUDED,
            excluded_patterns=EXCLUDED if EXCLUDED else None,
        ),
    )
    await coco.mount_each(_process_file, files.items(), target_table)


app = coco.App(
    coco.AppConfig(name=APP),
    _app_main,
    sourcedir=pathlib.Path(SOURCE_PATH).resolve(),
)
