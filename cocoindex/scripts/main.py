"""汎用コードベースインデクサー

使い方:
  uv run python main.py <source_path> [--patterns "**/*.rb,**/*.py"] [--exclude "**/tmp/**"]
  uv run python main.py <source_path> --live  # 常駐モード（FlowLiveUpdater）

プロジェクト名は --name で指定する。
共通設定は ~/.config/cocoindex/.env で管理:
  COCOINDEX_DATABASE_URL, VOYAGE_API_KEY
"""
import argparse
import datetime
import os
import re
import signal
from pathlib import Path

from dotenv import load_dotenv
import cocoindex

CONFIG_DIR = Path.home() / ".config" / "cocoindex"
load_dotenv(dotenv_path=CONFIG_DIR / ".env")

PROVIDER_MAP = {
    "voyage": cocoindex.LlmApiType.VOYAGE,
    "openai": cocoindex.LlmApiType.OPENAI,
    "ollama": cocoindex.LlmApiType.OLLAMA,
}

DEFAULT_EXCLUDES = [
    # === 共通 ===
    "**/.*",              # 隠しファイル・ディレクトリ (.git, .idea, .env 等)
    "**/log/**",          # ログ
    "**/tmp/**",          # 一時ファイル
    "**/coverage/**",     # カバレッジレポート

    # === Ruby/Rails ===
    "**/vendor/bundle/**",  # Bundlerの依存
    "**/.gem_rbs_collection/**",  # RBS collection

    # === Node.js ===
    "**/node_modules/**",  # npm/yarn依存
    "**/dist/**",          # ビルド成果物
    "**/build/**",         # ビルド成果物

    # === Python ===
    "**/.venv/**",         # 仮想環境
    "**/__pycache__/**",   # バイトコードキャッシュ

    # === Rust ===
    "**/target/**",        # Cargoビルド出力
]


def get_host_prefix() -> str:
    """ホスト名プレフィックスを取得（テーブル名の衝突回避用）"""
    import socket
    return re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()


def get_project_name(name: str | None, source_path: str) -> str:
    """プロジェクト名を取得（hostnameプレフィックス付き）"""
    host_prefix = get_host_prefix()
    base_name = name if name else Path(source_path).resolve().parent.name
    # 既にhostnameプレフィックスが付いている場合はそのまま返す
    if base_name.startswith(f"{host_prefix}_"):
        return base_name
    return f"{host_prefix}_{base_name}"


def derive_flow_name(name: str) -> str:
    """インデックス名からフロー名を生成"""
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", name)
    return f"CodeIndex_{sanitized}"


def create_flow(source_path: str, index_name: str, included_patterns: list[str], excluded_patterns: list[str], *, live: bool = False):
    flow_name = derive_flow_name(index_name)

    provider_name = os.environ.get("EMBEDDING_PROVIDER", "voyage").lower()
    api_type = PROVIDER_MAP.get(provider_name, cocoindex.LlmApiType.VOYAGE)
    model = os.environ.get("EMBEDDING_MODEL", "voyage-code-3")
    address = os.environ.get("EMBEDDING_ADDRESS")

    embed_opts: dict = {"api_type": api_type, "model": model, "task_type": "document"}
    if address:
        embed_opts["address"] = address

    interval = int(os.environ.get("LIVE_UPDATE_INTERVAL", "60"))

    @cocoindex.flow_def(name=flow_name)
    def code_index_flow(flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope):
        source_opts = {"path": source_path, "included_patterns": included_patterns}
        if excluded_patterns:
            source_opts["excluded_patterns"] = excluded_patterns

        data_scope["files"] = flow_builder.add_source(
            cocoindex.sources.LocalFile(**source_opts),
            refresh_interval=datetime.timedelta(seconds=interval) if live else None,
        )

        code_chunks_collector = data_scope.add_collector()

        with data_scope["files"].row() as file:
            file["language"] = file["filename"].transform(
                cocoindex.functions.DetectProgrammingLanguage()
            )
            file["chunks"] = file["content"].transform(
                cocoindex.functions.SplitRecursively(),
                chunk_size=800,
                chunk_overlap=200,
            )
            with file["chunks"].row() as chunk:
                chunk["embedding"] = chunk["text"].transform(
                    cocoindex.functions.EmbedText(**embed_opts)
                )
                code_chunks_collector.collect(
                    filename=file["filename"],
                    language=file["language"],
                    chunk_text=chunk["text"],
                    embedding=chunk["embedding"],
                    generated_id=cocoindex.GeneratedField.UUID,
                )

        code_chunks_collector.export(
            "code_chunks",
            cocoindex.targets.Postgres(
                column_options={
                    "embedding": cocoindex.targets.PostgresColumnOptions(type="halfvec"),
                },
            ),
            primary_key_fields=["generated_id"],
            vector_indexes=[
                cocoindex.VectorIndexDef(
                    field_name="embedding",
                    metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
                )
            ],
        )

    return code_index_flow, flow_name


def main():
    parser = argparse.ArgumentParser(description="コードベースのベクトルインデックスを構築")
    parser.add_argument("source_path", help="インデックス対象ディレクトリ（絶対パス）")
    parser.add_argument("--patterns", default="**/*.rb", help="対象ファイルパターン（カンマ区切り）")
    parser.add_argument("--exclude", default="", help="追加除外パターン（カンマ区切り）")
    parser.add_argument("--no-default-excludes", action="store_true", help="デフォルト除外パターンを無効化")
    parser.add_argument("--name", default=None, help="プロジェクト名（未指定時は source_path の親ディレクトリ名）")
    parser.add_argument("--live", action="store_true", help="FlowLiveUpdater で常駐モード起動")
    args = parser.parse_args()

    name = get_project_name(args.name, args.source_path)
    source_path = str(Path(args.source_path).resolve())
    included = [p.strip() for p in args.patterns.split(",")]
    excluded = list(DEFAULT_EXCLUDES) if not args.no_default_excludes else []
    if args.exclude:
        excluded.extend(p.strip() for p in args.exclude.split(",") if p.strip())

    cocoindex.init()
    flow, flow_name = create_flow(source_path, name, included, excluded, live=args.live)
    flow.setup()

    if args.live:
        print(f"Live updater started: {flow_name} (PID: {os.getpid()})")
        with cocoindex.FlowLiveUpdater(
            flow,
            cocoindex.FlowLiveUpdaterOptions(live_mode=True, print_stats=True),
        ) as updater:
            signal.signal(signal.SIGTERM, lambda s, f: updater.abort())
            signal.signal(signal.SIGINT, lambda s, f: updater.abort())
            updater.wait()
        print(f"Live updater stopped: {flow_name}")
    else:
        flow.update()
        table_name = f"{flow_name}__code_chunks".lower()
        print(f"Done: {flow_name}")
        print(f"Table: {table_name}")


if __name__ == "__main__":
    main()
