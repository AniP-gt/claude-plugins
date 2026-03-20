"""ベクトル検索でコードのエントリーポイントを発見する

使い方:
  uv run python search.py "<query>" [--top N]

テーブル名は --project-dir のベースネームから自動計算される。
共通設定は ~/.config/cocoindex/.env で管理:
  COCOINDEX_DATABASE_URL, VOYAGE_API_KEY
"""
import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

CONFIG_DIR = Path.home() / ".config" / "cocoindex"
load_dotenv(dotenv_path=CONFIG_DIR / ".env")


def get_table_name(project_dir: str) -> str:
    """プロジェクトディレクトリからテーブル名を計算（hostname prefix付き）"""
    import socket
    host_prefix = re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()
    name = Path(project_dir).name
    index_name = f"{host_prefix}_{name}"
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name)
    return f"codeindex_{sanitized}__code_chunks".lower()


def get_query_embedding(query: str) -> list[float]:
    """環境変数に応じたプロバイダーでクエリのembeddingを生成"""
    provider = os.environ.get("EMBEDDING_PROVIDER", "voyage").lower()
    model = os.environ.get("EMBEDDING_MODEL", "voyage-code-3")

    if provider == "openai":
        import openai
        client = openai.Client()
        result = client.embeddings.create(input=[query], model=model)
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
        result = client.embed([query], model=model, input_type="query")
        return result.embeddings[0]


def main():
    parser = argparse.ArgumentParser(description="ベクトル検索でコードを探索")
    parser.add_argument("query", help="自然言語クエリ")
    parser.add_argument("--project-dir", required=True, help="プロジェクトディレクトリ（絶対パス）")
    parser.add_argument("--top", type=int, default=5, help="表示件数（デフォルト: 5）")
    args = parser.parse_args()

    table_name = get_table_name(args.project_dir)
    db_url = os.environ.get("COCOINDEX_DATABASE_URL", "postgres://postgres:postgres@localhost:15432/postgres")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    embedding = get_query_embedding(args.query)
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

    cur.execute(sql.SQL("""
        SELECT DISTINCT ON (filename) filename,
               1 - (embedding::halfvec <=> %s::halfvec) AS similarity,
               chunk_text
        FROM {}
        ORDER BY filename, embedding::halfvec <=> %s::halfvec
    """).format(sql.Identifier(table_name)), (vec_str, vec_str))
    rows = cur.fetchall()
    rows.sort(key=lambda r: r[1], reverse=True)

    for fname, sim, text in rows[:args.top]:
        preview = text[:400].replace("\n", " ")
        print(f"[{sim:.3f}] {fname}")
        print(f"  {preview}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
