#!/usr/bin/env bash
# episodic-search: memories/ 配下（raw/session + raw/web + raw/minutes + wiki）に対するハイブリッド検索
#
# Usage:
#   search.sh <query> [--top N] [--scope session|web|minutes|wiki|all] [--include-superseded]
#                     [--format json|markdown] [--no-dedupe] [--low-score-threshold N]
#
# Defaults: --top 10, --scope all, --format markdown, status=active のみ, threshold 0.3
#
# 同階層の search.py を episodic プラグイン専用 venv で実行する。
# dense + BM25 (RRF) → voyage rerank-2 のハイブリッド検索。chunk_tsv 列 + GIN index は
# main_episodic.py の declare_sql_command_attachment で自動的に作成される。
#
# 副作用なし（読み取り専用）。Claude Code・Claude API 両方から呼べるよう stdin/stdout 完結。
set -u

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "${SCRIPTS_DIR}/../.." && pwd)}"
EPISODIC_SCRIPTS_DIR="${PLUGIN_ROOT}/scripts"

MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"
FORMATTER="${SCRIPTS_DIR}/format.py"
SEARCH_PY="${SCRIPTS_DIR}/search.py"

QUERY=""
TOP=10
SCOPE="all"
INCLUDE_SUPERSEDED=0
FORMAT="markdown"
NO_DEDUPE=0
LOW_SCORE_THRESHOLD="0.3"

usage() {
    cat <<EOF >&2
Usage: $0 <query> [options]
Options:
  --top N                                 返す件数（既定: 10、ファイル単位）
  --scope session|web|minutes|wiki|all    検索対象（既定: all）
  --include-superseded                    superseded/deprecated も含める
  --format json|markdown                  出力形式（既定: markdown）
  --no-dedupe                             同一ファイル内の異なる chunk も全て返す
                                          （既定では最高スコア chunk のみ採用）
  --low-score-threshold N                 トップスコアがこの値未満なら stderr に
                                          再クエリヒントを出す（既定: 0.3、0 以下で無効化）
EOF
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --top) TOP="$2"; shift 2 ;;
        --scope) SCOPE="$2"; shift 2 ;;
        --include-superseded) INCLUDE_SUPERSEDED=1; shift ;;
        --format) FORMAT="$2"; shift 2 ;;
        --no-dedupe) NO_DEDUPE=1; shift ;;
        --low-score-threshold) LOW_SCORE_THRESHOLD="$2"; shift 2 ;;
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
[[ ! -f "$SEARCH_PY" ]] && { echo "search.py not found: $SEARCH_PY" >&2; exit 3; }
[[ ! -f "$EPISODIC_SCRIPTS_DIR/pyproject.toml" ]] && { echo "episodic pyproject not found: $EPISODIC_SCRIPTS_DIR" >&2; exit 3; }
[[ ! -d "$MEMORIES_DIR" ]] && { echo "memories dir not found: $MEMORIES_DIR" >&2; exit 3; }

# episodic プラグイン専用設定（cocoindex プラグインに依存しない）
EMBEDDING_MODEL_OVERRIDE="${MEMORIES_EMBEDDING_MODEL:-voyage-3-large}"
EMBEDDING_PROVIDER_OVERRIDE="${MEMORIES_EMBEDDING_PROVIDER:-voyage}"

# stdout（検索結果）と stderr（hint / スタックトレース）を分離して取得する。
# search.py が stderr に出す再クエリヒントを後段で透過するため。
STDERR_FILE=$(mktemp)
trap 'rm -f "$STDERR_FILE"' EXIT

# 候補は format.py 側で scope/status フィルタを適用する分も見越して 3 倍取得。
RAW_OUTPUT=$(cd "$EPISODIC_SCRIPTS_DIR" && \
    EMBEDDING_MODEL="$EMBEDDING_MODEL_OVERRIDE" \
    EMBEDDING_PROVIDER="$EMBEDDING_PROVIDER_OVERRIDE" \
    uv run python "$SEARCH_PY" "$QUERY" \
    --project-dir "$MEMORIES_DIR" \
    --top "$((TOP * 3))" \
    --low-score-threshold "$LOW_SCORE_THRESHOLD" 2>"$STDERR_FILE")
RC=$?

RAW_STDERR=$(cat "$STDERR_FILE")

if [[ $RC -ne 0 ]]; then
    # search.py 側で OperationalError をハンドルし exit 4 + hint を出すため、そのまま透過。
    # それ以外のエラーで connection refused が混じった場合のみ hint に置き換える。
    if [[ $RC -ne 4 ]] && \
       printf '%s' "$RAW_STDERR" | grep -qiE "could not connect|connection refused"; then
        cat >&2 <<EOF
[episodic-search] PostgreSQL に接続できません（既定: localhost:15432）。
  起動コマンド:
    docker compose -f ~/.config/cocoindex/compose.yml up -d
  別ホストの場合は EPISODIC_DATABASE_URL を ~/.config/episodic/.env で設定してください。
EOF
        exit 4
    fi
    [[ -n "$RAW_STDERR" ]] && echo "$RAW_STDERR" >&2
    [[ -n "$RAW_OUTPUT" ]] && echo "$RAW_OUTPUT" >&2
    exit $RC
fi

# 子プロセスの stderr（再クエリヒント等）を親 stderr に透過する。
[[ -n "$RAW_STDERR" ]] && printf '%s\n' "$RAW_STDERR" >&2

INCLUDE_FLAG=""
[[ $INCLUDE_SUPERSEDED -eq 1 ]] && INCLUDE_FLAG="--include-superseded"
NO_DEDUPE_FLAG=""
[[ $NO_DEDUPE -eq 1 ]] && NO_DEDUPE_FLAG="--no-dedupe"

printf '%s\n' "$RAW_OUTPUT" | python3 "$FORMATTER" \
    --memories-dir "$MEMORIES_DIR" \
    --scope "$SCOPE" \
    --top "$TOP" \
    --format "$FORMAT" \
    $INCLUDE_FLAG \
    $NO_DEDUPE_FLAG
