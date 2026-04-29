"""ベクトル検索 + voyage rerank でコードのエントリーポイントを発見する

使い方:
  uv run python search.py "<query>" --project-dir <path> [--top N] [--no-rerank]

検索フロー（既定）:
  1) vector 検索で Top-K 候補（既定 30、RERANK_CANDIDATES）を取得
  2) voyage rerank（既定 rerank-2.5、RERANK_MODEL）で再評価
  3) 上位 N 件（--top、既定 5）を表示

テーブル名は --project-dir のベースネームから自動計算される。
共通設定は ~/.config/cocoindex/{config.toml,secrets.env} で管理:
  COCOINDEX_DATABASE_URL, VOYAGE_API_KEY,
  RERANK_ENABLED, RERANK_MODEL, RERANK_CANDIDATES
"""
import argparse
import os
import re
from pathlib import Path

import psycopg2
from psycopg2 import sql

from config import apply_config_to_env

apply_config_to_env()


def get_table_name(project_dir: str) -> str:
    """プロジェクトディレクトリからテーブル名を計算（hostname prefix付き）"""
    import socket
    host_prefix = re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()
    name = Path(project_dir).name
    index_name = f"{host_prefix}_{name}"
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name)
    return f"codeindex_{sanitized}__code_chunks".lower()


def _bool_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def get_query_embedding(query: str) -> list[float]:
    """環境変数に応じたプロバイダーでクエリのembeddingを生成"""
    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage").lower()
    model = os.environ.get("EMBEDDING_MODEL", "voyage-code-3")
    dim_env = os.environ.get("EMBEDDING_DIMENSION")
    output_dim = int(dim_env) if dim_env else None

    if provider == "openai":
        import openai
        client = openai.Client()
        kwargs: dict = {}
        if output_dim:
            kwargs["dimensions"] = output_dim
        result = client.embeddings.create(input=[query], model=model, **kwargs)
        return result.data[0].embedding
    elif provider == "ollama":
        import requests
        address = os.environ.get("EMBEDDING_ADDRESS", "http://localhost:11434")
        resp = requests.post(f"{address}/api/embed", json={"model": model, "input": query})
        resp.raise_for_status()
        return resp.json()["embeddings"][0]
    else:
        import voyageai
        client = voyageai.Client()
        kwargs = {"input_type": "query"}
        if output_dim:
            kwargs["output_dimension"] = output_dim
        result = client.embed([query], model=model, **kwargs)
        return result.embeddings[0]


def vector_search(
    cur, table_name: str, vec_str: str, limit: int
) -> list[tuple[str, float, str]]:
    """vector 検索で limit 件を取得。同一ファイル複数チャンクも維持（rerank 入力用）"""
    cur.execute(sql.SQL("""
        SELECT filename,
               1 - (embedding::halfvec <=> %s::halfvec) AS similarity,
               chunk_text
        FROM {}
        ORDER BY embedding::halfvec <=> %s::halfvec
        LIMIT %s
    """).format(sql.Identifier(table_name)), (vec_str, vec_str, limit))
    return list(cur.fetchall())


def voyage_rerank(
    query: str,
    candidates: list[tuple[str, float, str]],
    model: str,
    top_k: int,
) -> list[tuple[str, float, str]]:
    """voyage rerank で再評価し top_k 件を返す。返値は (filename, relevance_score, chunk_text)"""
    import voyageai
    client = voyageai.Client()
    docs = [c[2] for c in candidates]
    res = client.rerank(query=query, documents=docs, model=model, top_k=top_k)
    return [(candidates[r.index][0], r.relevance_score, candidates[r.index][2]) for r in res.results]


def dedup_by_filename(rows: list[tuple[str, float, str]], limit: int) -> list[tuple[str, float, str]]:
    """ファイル名の重複を除いた上位 limit 件を返す（vector フォールバック用）"""
    seen: set[str] = set()
    out: list[tuple[str, float, str]] = []
    for r in rows:
        if r[0] in seen:
            continue
        seen.add(r[0])
        out.append(r)
        if len(out) >= limit:
            break
    return out


def main():
    parser = argparse.ArgumentParser(description="ベクトル検索 + voyage rerank でコードを探索")
    parser.add_argument("query", help="自然言語クエリ")
    parser.add_argument("--project-dir", required=True, help="プロジェクトディレクトリ（絶対パス）")
    parser.add_argument("--top", type=int, default=5, help="表示件数（デフォルト: 5）")
    parser.add_argument("--no-rerank", action="store_true", help="rerank を無効化し vector 検索のみ")
    args = parser.parse_args()

    rerank_enabled = _bool_env(os.environ.get("RERANK_ENABLED"), default=True) and not args.no_rerank
    rerank_model = os.environ.get("RERANK_MODEL", "rerank-2.5")
    rerank_candidates = int(os.environ.get("RERANK_CANDIDATES", "30"))

    table_name = get_table_name(args.project_dir)
    db_url = os.environ.get("COCOINDEX_DATABASE_URL", "postgres://postgres:postgres@localhost:15432/postgres")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    embedding = get_query_embedding(args.query)
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

    if rerank_enabled:
        candidates = vector_search(cur, table_name, vec_str, limit=rerank_candidates)
        results = voyage_rerank(args.query, candidates, model=rerank_model, top_k=args.top) if candidates else []
    else:
        # rerank OFF 時は同一ファイルの重複を Python 側で除いて --top に揃える。
        # 多めに取って絞ることで、上位が同一ファイル連発で潰れるのを避ける。
        rows = vector_search(cur, table_name, vec_str, limit=max(args.top * 6, args.top))
        results = dedup_by_filename(rows, limit=args.top)

    for fname, sc, text in results:
        preview = text[:400].replace("\n", " ")
        print(f"[{sc:.3f}] {fname}")
        print(f"  {preview}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
