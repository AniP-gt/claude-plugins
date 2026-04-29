#!/usr/bin/env python3
"""memory-search 専用ベクトル検索（dense + BM25 RRF → rerank-2）。

- 既存テーブル `codeindex_<host>_<name>__code_chunks`（cocoindex 出力）に対して読み取り専用
- 前提: chunk_tsv (tsvector) 列と GIN index が同テーブルに作成済み
- 出力フォーマットは cocoindex プラグインの search.py と同じ `[<score>] <filename>` 形式
  → 同階層の format.py がそのまま利用できる

依存: voyageai / psycopg2 / python-dotenv
通常は cocoindex プラグインの venv を借りて実行する（search.sh が `uv run` でラップ）。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
import voyageai
from psycopg2 import sql

CONFIG_DIR = Path.home() / ".config" / "cocoindex"
load_dotenv(dotenv_path=CONFIG_DIR / ".env")


def get_table_name(project_dir: str) -> str:
    """プロジェクトディレクトリからテーブル名を計算（hostname prefix付き）。

    cocoindex プラグインの search.py / main.py と同じロジック。
    """
    import socket
    host_prefix = re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()
    name = Path(project_dir).name
    index_name = f"{host_prefix}_{name}"
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name)
    return f"codeindex_{sanitized}__code_chunks".lower()


def embed_query(query: str) -> list[float]:
    model = os.environ.get("EMBEDDING_MODEL", "voyage-3-large")
    client = voyageai.Client()
    result = client.embed([query], model=model, input_type="query")
    return result.embeddings[0]


def reciprocal_rank_fusion(rank_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    """RRF: 各ランクリスト i 内の順位 r に対して 1/(k+r) を合算。"""
    score: dict[str, float] = {}
    for rl in rank_lists:
        for rank, key in enumerate(rl, 1):
            score[key] = score.get(key, 0.0) + 1.0 / (k + rank)
    return score


def fetch_dense(cur, table: str, query_vec: list[float], n: int) -> list[tuple]:
    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"
    cur.execute(
        sql.SQL(
            """
            SELECT id::text, filename, chunk_text,
                   1 - (embedding::halfvec <=> %s::halfvec) AS sim
            FROM {}
            ORDER BY embedding::halfvec <=> %s::halfvec
            LIMIT %s
            """
        ).format(sql.Identifier(table)),
        (vec_str, vec_str, n),
    )
    return cur.fetchall()


def fetch_bm25(cur, table: str, query: str, n: int) -> list[tuple]:
    cur.execute(
        sql.SQL(
            """
            SELECT id::text, filename, chunk_text,
                   ts_rank(chunk_tsv, plainto_tsquery('simple', %s)) AS rank
            FROM {}
            WHERE chunk_tsv @@ plainto_tsquery('simple', %s)
            ORDER BY rank DESC
            LIMIT %s
            """
        ).format(sql.Identifier(table)),
        (query, query, n),
    )
    return cur.fetchall()


def dedup_by_filename(ordered_ids: list[str], by_id: dict[str, tuple], limit: int) -> list[str]:
    """同一 filename の chunk は最上位 1 つだけ残す。"""
    seen: set[str] = set()
    out: list[str] = []
    for cid in ordered_ids:
        fname = by_id[cid][1]
        if fname in seen:
            continue
        seen.add(fname)
        out.append(cid)
        if len(out) >= limit:
            break
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="memory-search hybrid+rerank")
    p.add_argument("query")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--top", type=int, default=10)
    p.add_argument(
        "--candidates",
        type=int,
        default=50,
        help="dense/bm25 各々の取得件数（rerank の入力ファイル数上限）",
    )
    p.add_argument(
        "--rerank-model",
        default=os.environ.get("MEMORIES_RERANK_MODEL", "rerank-2"),
    )
    p.add_argument("--no-rerank", action="store_true", help="rerank を無効化")
    p.add_argument("--no-bm25", action="store_true", help="BM25 を無効化（dense のみ）")
    args = p.parse_args()

    table = get_table_name(args.project_dir)
    db_url = os.environ.get(
        "COCOINDEX_DATABASE_URL",
        "postgres://postgres:postgres@localhost:15432/postgres",
    )

    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        try:
            query_vec = embed_query(args.query)
            dense_rows = fetch_dense(cur, table, query_vec, args.candidates)
            bm25_rows = [] if args.no_bm25 else fetch_bm25(cur, table, args.query, args.candidates)
        finally:
            cur.close()
    finally:
        conn.close()

    if not dense_rows and not bm25_rows:
        print("", end="")
        return 0

    by_id: dict[str, tuple] = {r[0]: r for r in dense_rows}
    for r in bm25_rows:
        by_id.setdefault(r[0], r)

    rank_lists = [[r[0] for r in dense_rows]]
    if bm25_rows:
        rank_lists.append([r[0] for r in bm25_rows])
    rrf_score = reciprocal_rank_fusion(rank_lists)
    fused = sorted(by_id.keys(), key=lambda i: rrf_score.get(i, 0.0), reverse=True)

    deduped = dedup_by_filename(fused, by_id, args.candidates)

    if args.no_rerank or not deduped:
        for cid in deduped[: args.top]:
            row = by_id[cid]
            score = rrf_score.get(cid, 0.0)
            preview = row[2][:400].replace("\n", " ")
            print(f"[{score:.3f}] {row[1]}")
            print(f"  {preview}")
        return 0

    client = voyageai.Client()
    docs = [by_id[cid][2] for cid in deduped]
    try:
        rerank_result = client.rerank(
            args.query,
            docs,
            model=args.rerank_model,
            top_k=min(args.top, len(docs)),
        )
    except Exception as e:  # rerank API 失敗時は RRF 順にフォールバック
        sys.stderr.write(f"[warn] rerank failed: {e}; falling back to RRF order\n")
        for cid in deduped[: args.top]:
            row = by_id[cid]
            score = rrf_score.get(cid, 0.0)
            preview = row[2][:400].replace("\n", " ")
            print(f"[{score:.3f}] {row[1]}")
            print(f"  {preview}")
        return 0

    for r in rerank_result.results:
        cid = deduped[r.index]
        row = by_id[cid]
        preview = row[2][:400].replace("\n", " ")
        print(f"[{r.relevance_score:.3f}] {row[1]}")
        print(f"  {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
