#!/usr/bin/env bash
# minutes/save: 議事録（タイトル + 本文）を memories/raw/minutes/YYYY-MM-DD/ 配下に保存する。
#
# 入力経路（いずれか1つ）:
#   - --from-file <path>     ファイルから本文を読む
#   - stdin                  標準入力から本文を読む（パイプ・heredoc）
#
# Usage:
#   minutes/save.sh --title "<タイトル>" [--tags tag1,tag2] [--related-session <UUID>] \
#                   [--participants name1,name2] [--from-file <path>] [--out <絶対パス>]
#   echo "..." | minutes/save.sh --title "<タイトル>"
#
# 環境変数:
#   MEMORIES_DIR    memories ルート（既定: /Volumes/memory）
#
# Exit:
#   0  成功
#   2  引数不正
#   3  保存先準備失敗
set -euo pipefail

usage() {
    cat <<'EOF' >&2
Usage: minutes/save.sh --title "<タイトル>" [options]
Options:
  --title TITLE             議事録タイトル（必須）
  --tags tag1,tag2          frontmatter tags
  --participants n1,n2      参加者
  --related-session UUID    関連 session_id
  --from-file PATH          本文ソース（指定なしなら stdin から読む）
  --out PATH                明示保存先（指定なしなら自動算出）
EOF
    exit 2
}

TITLE=""
TAGS=""
PARTICIPANTS=""
RELATED_SESSION=""
FROM_FILE=""
OUT_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --title)            TITLE="$2"; shift 2 ;;
        --tags)             TAGS="$2"; shift 2 ;;
        --participants)     PARTICIPANTS="$2"; shift 2 ;;
        --related-session)  RELATED_SESSION="$2"; shift 2 ;;
        --from-file)        FROM_FILE="$2"; shift 2 ;;
        --out)              OUT_PATH="$2"; shift 2 ;;
        -h|--help) usage ;;
        --) shift; break ;;
        *) echo "unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$TITLE" ]] && { echo "error: --title is required" >&2; usage; }

MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"

# 本文取得
TMP_BODY="$(mktemp -t minutes-body.XXXXXX)"
trap 'rm -f "$TMP_BODY"' EXIT

if [[ -n "$FROM_FILE" ]]; then
    [[ ! -f "$FROM_FILE" ]] && { echo "error: file not found: $FROM_FILE" >&2; exit 2; }
    cat "$FROM_FILE" > "$TMP_BODY"
else
    # stdin から
    cat > "$TMP_BODY"
fi

if [[ ! -s "$TMP_BODY" ]]; then
    echo "error: body is empty (--from-file 未指定なら stdin から本文を渡してください)" >&2
    exit 2
fi

# 保存先計算
NOW_ISO="$(date '+%Y-%m-%dT%H:%M:%S%z' | sed 's/\([+-]..\)\(..\)$/\1:\2/')"
DATE_DIR="$(date '+%Y-%m-%d')"
TIME_PREFIX="$(date '+%H%M%S')"

if [[ -z "$OUT_PATH" ]]; then
    SLUG="$(printf '%s' "$TITLE" \
        | tr '[:upper:]' '[:lower:]' \
        | tr -c 'a-z0-9-' '-' \
        | sed -E 's/^-+|-+$//g; s/-+/-/g' \
        | head -c 48)"
    [[ -z "$SLUG" ]] && SLUG="minutes"
    OUT_DIR="$MEMORIES_DIR/raw/minutes/$DATE_DIR"
    OUT_PATH="$OUT_DIR/${TIME_PREFIX}_${SLUG}.md"
fi

OUT_DIR="$(dirname "$OUT_PATH")"
mkdir -p "$OUT_DIR" 2>/dev/null || {
    echo "error: cannot create output dir: $OUT_DIR" >&2
    exit 3
}

# YAML エスケープ（改行除去 + 二重引用符と \ をエスケープ）。
# 改行を残すと frontmatter を破壊できるため `tr -d` で必ず除去する。
yaml_escape() {
    printf '%s' "$1" | tr -d '\n\r' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

# inline list 化（各要素は yaml_escape で改行・引用符をエスケープ）
to_yaml_list() {
    local input="$1"
    if [[ -z "$input" ]]; then
        printf '%s' "[]"
        return
    fi
    local out="["
    IFS=',' read -ra arr <<< "$input"
    local first=1
    for raw in "${arr[@]}"; do
        local v="${raw// /}"
        [[ -z "$v" ]] && continue
        if [[ $first -eq 0 ]]; then
            out+=", "
        fi
        out+="\"$(yaml_escape "$v")\""
        first=0
    done
    out+="]"
    printf '%s' "$out"
}

TITLE_ESC="$(yaml_escape "$TITLE")"
TAGS_YAML="$(to_yaml_list "$TAGS")"
PARTICIPANTS_YAML="$(to_yaml_list "$PARTICIPANTS")"

if [[ -n "$RELATED_SESSION" ]]; then
    RELATED_YAML="\"$(yaml_escape "$RELATED_SESSION")\""
else
    RELATED_YAML="null"
fi

{
    printf -- '---\n'
    printf 'kind: minutes\n'
    printf 'title: "%s"\n' "$TITLE_ESC"
    printf 'created_at: %s\n' "$NOW_ISO"
    printf 'updated_at: %s\n' "$NOW_ISO"
    printf 'status: active\n'
    printf 'supersedes: null\n'
    printf 'related_session: %s\n' "$RELATED_YAML"
    printf 'participants: %s\n' "$PARTICIPANTS_YAML"
    printf 'tags: %s\n' "$TAGS_YAML"
    printf -- '---\n\n'
    cat "$TMP_BODY"
} > "$OUT_PATH"

chmod 600 "$OUT_PATH" 2>/dev/null || true

# Wiki ingest-queue へ enqueue + wiki-runner を fire-and-forget 起動。
# cocoindex update は wiki-runner 完了時に 1 回呼ばれるためここでは呼ばない（重複起動回避）。
# 起動失敗を理由に Raw 保存自体を失敗扱いにしないため、すべて || true で握る。
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
ENQUEUE="$PLUGIN_ROOT/scripts/wiki/enqueue.py"
WIKI_RUNNER="$PLUGIN_ROOT/scripts/wiki/wiki-runner.sh"
LOG_DIR_LOCAL="/tmp/memories"
mkdir -p "$LOG_DIR_LOCAL" 2>/dev/null || true
if [[ -f "$ENQUEUE" && -x "$WIKI_RUNNER" ]]; then
    python3 "$ENQUEUE" "$OUT_PATH" --kind minutes >/dev/null 2>&1 || true
    ( nohup "$WIKI_RUNNER" >> "$LOG_DIR_LOCAL/memory-wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
fi

echo "$OUT_PATH"
