#!/usr/bin/env python3
"""episodic-search 専用ベクトル検索（dense + BM25 RRF → rerank-2）。

- 対象テーブル `episodicindex_<host>_<name>__chunks`（main_episodic.py が episodic DB に作成）
- 前提: chunk_tsv (tsvector) 列と GIN index は main_episodic.py の declare_sql_command_attachment
  により自動的に作成・維持される
- 出力フォーマットは `[<score>] <filename>` の単純形式（同階層の format.py が消費する）

依存: voyageai / psycopg2 / python-dotenv
episodic プラグイン専用 venv（episodic/scripts/.venv）で実行する（search.sh が `uv run` でラップ）。
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

_EPISODIC_CFG_DIR = Path.home() / ".config" / "episodic"
_COCOINDEX_CFG_DIR = Path.home() / ".config" / "cocoindex"

# プラグイン管理下にある secrets.env で確実に上書きする（古い ~/.env 等を排除）。
# 優先順位: episodic 側で明示設定した値 > cocoindex 側 secrets.env > プロセス起動時の env。
load_dotenv(dotenv_path=_COCOINDEX_CFG_DIR / "secrets.env", override=True)
load_dotenv(dotenv_path=_EPISODIC_CFG_DIR / ".env", override=True)
load_dotenv(dotenv_path=_EPISODIC_CFG_DIR / "secrets.env", override=True)


def get_table_name(project_dir: str) -> str:
    """プロジェクトディレクトリからテーブル名を計算（hostname prefix付き）。

    main_episodic.py の TABLE 命名規約と一致させる:
      episodicindex_<sanitized_host>_<sanitized_name>__chunks
    """
    import socket
    host_prefix = re.sub(r"[^a-zA-Z0-9]", "_", socket.gethostname()).lower()
    name = Path(project_dir).name
    index_name = f"{host_prefix}_{name}"
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", index_name)
    return f"episodicindex_{sanitized}__chunks".lower()


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


def emit_low_score_hint(top_score: float, threshold: float) -> None:
    """トップスコアが閾値未満なら stderr に再クエリヒントを出す（threshold <= 0 で無効化）。"""
    if threshold <= 0.0:
        return
    if top_score >= threshold:
        return
    sys.stderr.write(
        f"[hint] top score {top_score:.3f} は閾値 {threshold:.3f} 未満です。再クエリを推奨します。\n"
        "  - 固有名詞を一般語に置換（例: 'feature-dev effort' → 'スキル 設定値 妥当性'）\n"
        "  - 動詞化（例: 'effort 設定' → 'effort を変更する議論'）\n"
        "  - 時系列で当てるなら recent.sh --kind session を併用\n"
    )


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
    p = argparse.ArgumentParser(description="episodic-search hybrid+rerank")
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
    p.add_argument(
        "--low-score-threshold",
        type=float,
        default=0.3,
        help="この値未満のトップスコアなら stderr に再クエリヒントを出す（既定: 0.3、0 以下で無効化）",
    )
    args = p.parse_args()

    table = get_table_name(args.project_dir)
    db_url = os.environ.get(
        "EPISODIC_DATABASE_URL",
        "postgres://postgres:postgres@localhost:15432/episodic",
    )

    try:
        conn = psycopg2.connect(db_url)
    except psycopg2.OperationalError as e:
        msg = str(e).strip()
        if "could not connect" in msg.lower() or "connection refused" in msg.lower():
            sys.stderr.write(
                "[episodic-search] PostgreSQL に接続できません（既定: localhost:15432）。\n"
                "  起動コマンド:\n"
                "    docker compose -f ~/.config/cocoindex/compose.yml up -d\n"
                "  別ホストの場合は EPISODIC_DATABASE_URL を設定してください。\n"
            )
            return 4
        raise
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
        top_score = 0.0
        for i, cid in enumerate(deduped[: args.top]):
            row = by_id[cid]
            score = rrf_score.get(cid, 0.0)
            if i == 0:
                top_score = score
            preview = row[2][:400].replace("\n", " ")
            print(f"[{score:.3f}] {row[1]}")
            print(f"  {preview}")
        emit_low_score_hint(top_score, args.low_score_threshold)
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
        top_score = 0.0
        for i, cid in enumerate(deduped[: args.top]):
            row = by_id[cid]
            score = rrf_score.get(cid, 0.0)
            if i == 0:
                top_score = score
            preview = row[2][:400].replace("\n", " ")
            print(f"[{score:.3f}] {row[1]}")
            print(f"  {preview}")
        emit_low_score_hint(top_score, args.low_score_threshold)
        return 0

    for r in rerank_result.results:
        cid = deduped[r.index]
        row = by_id[cid]
        preview = row[2][:400].replace("\n", " ")
        print(f"[{r.relevance_score:.3f}] {row[1]}")
        print(f"  {preview}")
    top_score = rerank_result.results[0].relevance_score if rerank_result.results else 0.0
    emit_low_score_hint(top_score, args.low_score_threshold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
