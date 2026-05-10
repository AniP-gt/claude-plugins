"""episodic 専用 cocoindex 1.0 インデクサー（frontmatter prepend 対応版）

エピソード記憶（既定 /Volumes/memory 配下）専用のフロー定義。プラグイン本体（汎用 main.py）
をベースに、検索精度向上のため以下を組み込む:

  1. frontmatter（title / tags / keywords）を embedding 入力に prepend
     （タグ語彙でのマッチ強化、特に short query で効く）
  2. chunk_text には素の本文だけを格納（embed/store 分離）
     → 検索結果のスニペット表示が綺麗になる
  3. chunk_size は prepend 分（~100字）を補償して 1300 程度に拡張可能
     （episodic 用途は 1200 + prepend が体感最良）

cocoindex 1.0 CLI で起動:
  cocoindex update -f main_episodic.py:<AppName>

設定は環境変数 + ~/.config/episodic/cocoindex.toml + secrets.env で渡す:
  SOURCE_PATH               (必須) インデックス対象 (例: /Volumes/memory)
  INDEX_NAME                プロジェクト名 (省略時は固定値 "episodic")
  PATTERNS                  csv (既定: "**/*.md")
  EXCLUDE                   csv (既定: 主要 trash/draft 除外)
  CHUNK_SIZE                既定 1200
  CHUNK_OVERLAP             既定 300
  EMBEDDING_PROVIDER        既定 voyage
  EMBEDDING_MODEL           既定 voyage-3-large
  EMBEDDING_DIMENSION       既定 1024
  EPISODIC_DATABASE_URL     DB 接続先（既定 postgres://.../episodic）
  VOYAGE_API_KEY            secrets.env で管理
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

# 1) episodic プラグイン専用の env / secrets を読み込む。
#    優先順位: 既存環境変数 > ~/.config/episodic/.env / secrets.env > ~/.config/cocoindex/secrets.env (fallback)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # scripts/ を import path に追加

from dotenv import load_dotenv  # noqa: E402

_EPISODIC_CFG_DIR = pathlib.Path.home() / ".config" / "episodic"
_COCOINDEX_CFG_DIR = pathlib.Path.home() / ".config" / "cocoindex"

# cocoindex CLI が先に ~/.env を読み込んで古い VOYAGE_API_KEY 等が紛れ込むことがあるため、
# プラグイン管理下にある secrets.env で確実に上書きする。cocoindex 側を先に override=True で
# 読み込み、続いて episodic 側を読むことで episodic 側を最優先にする。
load_dotenv(dotenv_path=_COCOINDEX_CFG_DIR / "secrets.env", override=True)
load_dotenv(dotenv_path=_EPISODIC_CFG_DIR / ".env", override=True)
load_dotenv(dotenv_path=_EPISODIC_CFG_DIR / "secrets.env", override=True)


# 2) episodic プラグイン専用設定 ~/.config/episodic/cocoindex.toml を auto-provision して読み込む
#    テンプレ参照先は本ファイルと同じ scripts/ 配下（scripts/templates/cocoindex.toml.example）。
_EPISODIC_CONFIG = _EPISODIC_CFG_DIR / "cocoindex.toml"
_TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "templates" / "cocoindex.toml.example"

if not _EPISODIC_CONFIG.exists() and _TEMPLATE.exists():
    _EPISODIC_CFG_DIR.mkdir(parents=True, exist_ok=True)
    _EPISODIC_CONFIG.write_text(_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

# episodic 用 toml -> MEMORIES_* env への展開。優先順位は MEMORIES_* env > toml > 既定値。
_EPISODIC_CONFIG_MAPPINGS: list[tuple[tuple[str, ...], str]] = [
    (("embedding", "provider"), "MEMORIES_EMBEDDING_PROVIDER"),
    (("embedding", "model"), "MEMORIES_EMBEDDING_MODEL"),
    (("embedding", "dimension"), "MEMORIES_EMBEDDING_DIMENSION"),
    (("chunk", "size"), "MEMORIES_CHUNK_SIZE"),
    (("chunk", "overlap"), "MEMORIES_CHUNK_OVERLAP"),
    (("index", "exclude"), "MEMORIES_EXCLUDE"),
]

if _EPISODIC_CONFIG.exists():
    if sys.version_info >= (3, 11):
        import tomllib  # type: ignore
    else:  # pragma: no cover
        import tomli as tomllib  # type: ignore
    try:
        with _EPISODIC_CONFIG.open("rb") as _f:
            _epicfg = tomllib.load(_f)
        for _path, _env_key in _EPISODIC_CONFIG_MAPPINGS:
            if _env_key in os.environ:
                continue
            _cur: object = _epicfg
            for _k in _path:
                if not isinstance(_cur, dict) or _k not in _cur:
                    _cur = None
                    break
                _cur = _cur[_k]
            if _cur is not None:
                os.environ[_env_key] = str(_cur)
    except Exception as _e:
        print(f"[episodic] warn: failed to parse {_EPISODIC_CONFIG}: {_e}", file=sys.stderr)


# episodic ドメイン向けの除外（trashbox / 下書き / 隠し）
DEFAULT_EXCLUDES = [
    "trashbox/**",
    "**/_*.md",
    "**/.git/**",
    "**/.*",
]


def _csv(name: str, default: str = "") -> list[str]:
    return [s.strip() for s in os.environ.get(name, default).split(",") if s.strip()]


def _bool_env(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


SOURCE_PATH = os.environ.get("SOURCE_PATH")
if not SOURCE_PATH:
    raise RuntimeError("SOURCE_PATH 環境変数が必要です（例: SOURCE_PATH=/Volumes/memory）")

# episodic ドメイン専用設定。優先順位は MEMORIES_* env > 共通 env > 既定値。
def _ep_env(primary_key: str, fallback_key: str | None, default: str) -> str:
    if primary_key in os.environ:
        return os.environ[primary_key]
    if fallback_key and fallback_key in os.environ:
        return os.environ[fallback_key]
    return default


INCLUDED = _csv("PATTERNS", default="**/*.md")
EXCLUDED = ([] if _bool_env("NO_DEFAULT_EXCLUDES") else list(DEFAULT_EXCLUDES))
# EXCLUDE はランタイム個別指定（共通）、MEMORIES_EXCLUDE は memory 用 config.toml 既定。
EXCLUDED.extend(_csv("EXCLUDE"))
EXCLUDED.extend([s.strip() for s in os.environ.get("MEMORIES_EXCLUDE", "").split(",") if s.strip()])

CHUNK_SIZE = int(_ep_env("MEMORIES_CHUNK_SIZE", "CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(_ep_env("MEMORIES_CHUNK_OVERLAP", "CHUNK_OVERLAP", "300"))
EMBEDDING_DIMENSION = int(_ep_env("MEMORIES_EMBEDDING_DIMENSION", "EMBEDDING_DIMENSION", "1024"))


def _host_prefix() -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()


def _index_name() -> str:
    # 既定値は固定 "episodic"（旧版は SOURCE_PATH の basename を使っていたが、命名統一のため固定化）。
    raw = os.environ.get("INDEX_NAME") or "episodic"
    host = _host_prefix()
    return raw if raw.startswith(f"{host}_") else f"{host}_{raw}"


INDEX = _index_name()
TABLE = f"episodicindex_{re.sub(r'[^a-zA-Z0-9]', '_', INDEX).lower()}__chunks"
APP = f"EpisodicIndex_{re.sub(r'[^a-zA-Z0-9]', '_', INDEX)}"

# episodic 専用 database への接続 URL。EPISODIC_DATABASE_URL を最優先し、未設定なら
# localhost の episodic DB を既定値とする。
DATABASE_URL = os.environ.get(
    "EPISODIC_DATABASE_URL",
    "postgres://postgres:postgres@localhost:15432/episodic",
)

# cocoindex 1.0 は自身の tracking テーブルを格納する DB を COCOINDEX_DB から取得する。
# episodic プラグインは episodic database 内に tracking も置くため、未設定なら DATABASE_URL に揃える。
os.environ.setdefault("COCOINDEX_DB", DATABASE_URL)


def _build_embedder() -> LiteLLMEmbedder:
    provider = _ep_env("MEMORIES_EMBEDDING_PROVIDER", "EMBEDDING_PROVIDER", "voyage").lower()
    model = _ep_env("MEMORIES_EMBEDDING_MODEL", "EMBEDDING_MODEL", "voyage-3-large")
    kwargs: dict = {"input_type": "document", "dimensions": EMBEDDING_DIMENSION}
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
HALFVEC_PG_TYPE = PgType(f"halfvec({EMBEDDING_DIMENSION})", encoder=_vector_encoder)

_splitter = RecursiveSplitter()


def _extract_fm_prefix(content: str) -> str:
    """先頭 `---` ブロックから title/tags/keywords だけを抽出して空白区切りで返す。"""
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    if end == -1:
        return ""
    parts: list[str] = []
    for line in content[3:end].splitlines():
        s = line.strip()
        for k in ("title:", "tags:", "keywords:"):
            if s.startswith(k):
                parts.append(s)
                break
    return " ".join(parts)


def _strip_frontmatter(content: str) -> str:
    """先頭 `---` ブロックを取り除いた本文を返す。frontmatter が無ければ素通し。"""
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    return content[end + 4 :] if end != -1 else content


@dataclass
class EpisodicChunk:
    id: int
    filename: str
    chunk_text: str  # スニペット表示用に prepend 抜きの素の本文 chunk
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
    fm_prefix: str,
    filename: pathlib.PurePath,
    id_gen: IdGenerator,
    table: postgres.TableTarget[EpisodicChunk],
) -> None:
    """1 チャンクを embed して TableTarget に declare する。

    chunk.text は素の本文（frontmatter 除去済み）。
    fm_prefix は同ファイルから抽出した title/tags/keywords の連結文字列で、
    embed 入力の先頭に付与してタグ語彙マッチを強化する。
    """
    embedder = coco.use_context(EMBEDDER)
    embed_input = f"{fm_prefix}\n\n{chunk.text}" if fm_prefix else chunk.text
    table.declare_row(
        row=EpisodicChunk(
            id=await id_gen.next_id(chunk.text),
            filename=str(filename),
            chunk_text=chunk.text,  # スニペット表示には prepend 抜きの素の本文
            embedding=await embedder.embed(embed_input),
        ),
    )


@coco.fn(memo=True)
async def _process_file(
    file: FileLike,
    table: postgres.TableTarget[EpisodicChunk],
) -> None:
    text = await file.read_text()
    fm_prefix = _extract_fm_prefix(text)
    body = _strip_frontmatter(text)
    chunks = _splitter.split(
        body,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        language="markdown",
    )
    id_gen = IdGenerator()
    # coco.map(fn, iterable, *broadcast_args) 形式: 第2引数の各要素ごとに fn を呼び、
    # それ以外の引数は全呼び出しで共有される。fm_prefix はファイル毎の定数なので broadcast。
    await coco.map(
        _process_chunk, chunks, fm_prefix, file.file_path.path, id_gen, table,
    )


@coco.fn
async def _app_main(sourcedir: pathlib.Path) -> None:
    target_table = await postgres.mount_table_target(
        PG_DB,
        table_name=TABLE,
        table_schema=await postgres.TableSchema.from_class(
            EpisodicChunk, primary_key=["id"]
        ),
        pg_schema_name="public",
    )
    # halfvec 列向けの operator class (`halfvec_cosine_ops`) を SQL で直接付与する。
    target_table.declare_sql_command_attachment(
        name="hnsw_embedding",
        setup_sql=(
            f'CREATE INDEX IF NOT EXISTS "{TABLE}__embedding_hnsw" '
            f'ON public."{TABLE}" '
            f'USING hnsw (embedding halfvec_cosine_ops);'
        ),
        teardown_sql=f'DROP INDEX IF EXISTS public."{TABLE}__embedding_hnsw";',
    )

    # ハイブリッド検索（dense + BM25 RRF → rerank-2）用に chunk_text の tsvector 生成列と
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
