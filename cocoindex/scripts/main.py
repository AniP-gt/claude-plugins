"""汎用コードベースインデクサー (cocoindex 1.0)

cocoindex 1.0 CLI で起動する想定:

  cocoindex update <path/to/main.py>:app          # batch
  cocoindex update -L <path/to/main.py>:app       # live mode

設定は環境変数で渡す（旧 CLI 引数の置き換え）:
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

DB / API キーは ~/.config/cocoindex/.env で集中管理:
  COCOINDEX_DATABASE_URL, VOYAGE_API_KEY
"""
from __future__ import annotations

import os
import pathlib
import re
import socket
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

from config import apply_config_to_env

apply_config_to_env()

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
    return f"codeindex_{sanitized}__code_chunks"


def _app_name(index_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name)
    return f"CodeIndex_{sanitized}"


SOURCE_PATH = os.environ.get("SOURCE_PATH")
if not SOURCE_PATH:
    raise RuntimeError("SOURCE_PATH 環境変数が必要です")

INCLUDED = _csv("PATTERNS", default="**/*.rb")
EXCLUDED = ([] if _bool_env("NO_DEFAULT_EXCLUDES") else list(DEFAULT_EXCLUDES))
EXCLUDED.extend(_csv("EXCLUDE"))

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))

# halfvec を使えば pgvector の 4000dim 上限まで HNSW index が利用できる。
# 1024 dim では vector でも問題ないが halfvec で容量半分・精度同等。
_DIM_ENV = os.environ.get("EMBEDDING_DIMENSION")
EMBEDDING_DIMENSION = int(_DIM_ENV) if _DIM_ENV else 1024
HALFVEC_PG_TYPE = PgType(f"halfvec({EMBEDDING_DIMENSION})", encoder=_vector_encoder)

INDEX = _index_name()
TABLE = _table_name(INDEX)
APP = _app_name(INDEX)

DATABASE_URL = os.environ.get(
    "COCOINDEX_DATABASE_URL",
    "postgres://postgres:postgres@localhost:15432/postgres",
)


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
class CodeChunk:
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
    table: postgres.TableTarget[CodeChunk],
) -> None:
    embedder = coco.use_context(EMBEDDER)
    table.declare_row(
        row=CodeChunk(
            id=await id_gen.next_id(chunk.text),
            filename=str(filename),
            chunk_text=chunk.text,
            embedding=await embedder.embed(chunk.text),
        ),
    )


@coco.fn(memo=True)
async def _process_file(
    file: FileLike,
    table: postgres.TableTarget[CodeChunk],
) -> None:
    text = await file.read_text()
    chunks = _splitter.split(
        text,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        language="markdown",
    )
    id_gen = IdGenerator()
    await coco.map(_process_chunk, chunks, file.file_path.path, id_gen, table)


@coco.fn
async def _app_main(sourcedir: pathlib.Path) -> None:
    target_table = await postgres.mount_table_target(
        PG_DB,
        table_name=TABLE,
        table_schema=await postgres.TableSchema.from_class(
            CodeChunk, primary_key=["id"]
        ),
        pg_schema_name="public",
    )
    # halfvec 列に対応する operator class (`halfvec_cosine_ops`) を SQL で直接付与する。
    # cocoindex の declare_vector_index は vector_cosine_ops 固定で halfvec に非対応。
    # 2000dim 超は ivfflat 不可なので hnsw、それ以下も hnsw が安定（halfvec で揃える）。
    target_table.declare_sql_command_attachment(
        name="hnsw_embedding",
        setup_sql=(
            f'CREATE INDEX IF NOT EXISTS "{TABLE}__embedding_hnsw" '
            f'ON public."{TABLE}" '
            f'USING hnsw (embedding halfvec_cosine_ops);'
        ),
        teardown_sql=f'DROP INDEX IF EXISTS public."{TABLE}__embedding_hnsw";',
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
