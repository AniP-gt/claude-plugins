#!/usr/bin/env bash
# memory-search: memories/ 配下（Raw + Wiki）に対するベクトル検索
#
# Usage:
#   search.sh <query> [--top N] [--scope raw|wiki|all] [--include-superseded] [--format json|markdown]
#
# Defaults: --top 10, --scope all, --format markdown, status=active のみ
#
# Backend (環境変数 MEMORIES_SEARCH_BACKEND で切替):
#   hybrid (既定) — 同階層の search.py を使用。dense + BM25 (RRF) → voyage rerank-2 で
#                    top-1 精度を高めたハイブリッド検索。要 chunk_tsv 列＋GIN index。
#   dense        — cocoindex プラグイン同梱の search.py を使用（dense のみ）。
#
# 副作用なし（読み取り専用）。Claude Code・Claude API 両方から呼べるよう stdin/stdout 完結。
set -u

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "${SCRIPTS_DIR}/../.." && pwd)}"

# cocoindex プラグインルートを動的解決。COCOINDEX_PLUGIN 環境変数があれば最優先。
if [[ -n "${COCOINDEX_PLUGIN:-}" ]]; then
    PLUGIN="$COCOINDEX_PLUGIN"
else
    PLUGIN="$(python3 -c "
import sys
sys.path.insert(0, '${PLUGIN_ROOT}/scripts')
from lib.cocoindex_path import resolve_cocoindex_root
root = resolve_cocoindex_root()
print(root if root else '', end='')
")"
fi

MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"
FORMATTER="${SCRIPTS_DIR}/format.py"
HYBRID_SEARCH_PY="${SCRIPTS_DIR}/search.py"
BACKEND="${MEMORIES_SEARCH_BACKEND:-dense}"

QUERY=""
TOP=10
SCOPE="all"
INCLUDE_SUPERSEDED=0
FORMAT="markdown"

usage() {
    cat <<EOF >&2
Usage: $0 <query> [options]
Options:
  --top N                  返す件数（既定: 10）
  --scope raw|wiki|all     検索対象（既定: all）
  --include-superseded     superseded/deprecated も含める
  --format json|markdown   出力形式（既定: markdown）
EOF
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --top) TOP="$2"; shift 2 ;;
        --scope) SCOPE="$2"; shift 2 ;;
        --include-superseded) INCLUDE_SUPERSEDED=1; shift ;;
        --format) FORMAT="$2"; shift 2 ;;
        -h|--help) usage ;;
        --) shift; break ;;
        -*) echo "unknown option: $1" >&2; usage ;;
        *)
            if [[ -z "$QUERY" ]]; then
                QUERY="$1"; shift
            else
                echo "extra positional arg: $1" >&2; usage
            fi
            ;;
    esac
done

[[ -z "$QUERY" ]] && usage
[[ -z "$PLUGIN" || ! -d "$PLUGIN/scripts" ]] && { echo "cocoindex plugin not found (set COCOINDEX_PLUGIN or install cocoindex plugin): $PLUGIN" >&2; exit 3; }
[[ ! -d "$MEMORIES_DIR" ]] && { echo "memories dir not found: $MEMORIES_DIR" >&2; exit 3; }

# cocoindex search.py は --project-dir のベースネームでテーブル名を決める。
# memories/ 全体に対するインデックスを使う（raw + wiki 両対象）。
# scope フィルタは結果に対して post-process で適用する（cocoindex 側に scope 概念がないため）。
#
# memories は多言語自然文書中心のため voyage-3-large を使用。コード検索（cocoindex の
# 他用途）の voyage-code-3 と棲み分けるため、~/.config/cocoindex/.env は変更せず
# 呼び出し側で環境変数を上書きする（load_dotenv は既存 env を上書きしない）。
EMBEDDING_MODEL_OVERRIDE="${MEMORIES_EMBEDDING_MODEL:-voyage-3-large}"
EMBEDDING_PROVIDER_OVERRIDE="${MEMORIES_EMBEDDING_PROVIDER:-voyage}"

# hybrid バックエンド向けオプション（環境変数で切替可能）
HYBRID_EXTRA_ARGS=()
[[ "${MEMORIES_SEARCH_NO_BM25:-0}" == "1" ]] && HYBRID_EXTRA_ARGS+=(--no-bm25)
[[ "${MEMORIES_SEARCH_NO_RERANK:-0}" == "1" ]] && HYBRID_EXTRA_ARGS+=(--no-rerank)

case "$BACKEND" in
    hybrid)
        [[ ! -f "$HYBRID_SEARCH_PY" ]] && { echo "hybrid search.py not found: $HYBRID_SEARCH_PY" >&2; exit 3; }
        # 候補は format.py 側で scope/status フィルタを適用する分も見越して 3 倍取得。
        RAW_OUTPUT=$(cd "$PLUGIN/scripts" && \
            EMBEDDING_MODEL="$EMBEDDING_MODEL_OVERRIDE" \
            EMBEDDING_PROVIDER="$EMBEDDING_PROVIDER_OVERRIDE" \
            uv run python "$HYBRID_SEARCH_PY" "$QUERY" \
            --project-dir "$MEMORIES_DIR" \
            --top "$((TOP * 3))" ${HYBRID_EXTRA_ARGS[@]+"${HYBRID_EXTRA_ARGS[@]}"} 2>&1)
        RC=$?
        ;;
    dense)
        RAW_OUTPUT=$(cd "$PLUGIN/scripts" && \
            EMBEDDING_MODEL="$EMBEDDING_MODEL_OVERRIDE" \
            EMBEDDING_PROVIDER="$EMBEDDING_PROVIDER_OVERRIDE" \
            uv run python search.py "$QUERY" \
            --project-dir "$MEMORIES_DIR" \
            --top "$((TOP * 3))" 2>&1)
        RC=$?
        ;;
    *)
        echo "unknown MEMORIES_SEARCH_BACKEND: $BACKEND (expected hybrid|dense)" >&2
        exit 2
        ;;
esac

if [[ $RC -ne 0 ]]; then
    echo "$RAW_OUTPUT" >&2
    exit $RC
fi

INCLUDE_FLAG=""
[[ $INCLUDE_SUPERSEDED -eq 1 ]] && INCLUDE_FLAG="--include-superseded"

printf '%s\n' "$RAW_OUTPUT" | python3 "$FORMATTER" \
    --memories-dir "$MEMORIES_DIR" \
    --scope "$SCOPE" \
    --top "$TOP" \
    --format "$FORMAT" \
    $INCLUDE_FLAG
