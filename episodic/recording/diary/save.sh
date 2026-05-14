#!/usr/bin/env bash
# diary/save: プライベート日記（タイトル + 本文）を diary_dir/raw/diary/YYYY-MM-DD/ 配下に保存する。
#
# diary は既存 3 kind（session / web / minutes）と異なり、共有 NAS には出さない
# ローカル限定のレイヤー。「その時の気持ち」を残す場所であり、raw / wiki / cocoindex
# インデックスのすべてを diary_dir（既定 ~/.local/share/episodic/diary）配下に完結させる。
# 共有 NAS 前提の staging ロジックは持たない。
#
# 入力経路（いずれか1つ）:
#   - --from-file <path>     ファイルから本文を読む
#   - stdin                  標準入力から本文を読む（パイプ・heredoc）
#
# Usage:
#   diary/save.sh --title "<タイトル>" [--mood "<気分>"] [--tags tag1,tag2] \
#                 [--from-file <path>] [--out <絶対パス>]
#   echo "..." | diary/save.sh --title "<タイトル>"
#
# 環境変数:
#   MEMORIES_DIARY_DIR    diary ルート（既定: ~/.local/share/episodic/diary）
#
# Exit:
#   0  成功
#   2  引数不正
#   3  保存先準備失敗
set -euo pipefail

usage() {
    cat <<'EOF' >&2
Usage: diary/save.sh --title "<タイトル>" [options]
Options:
  --title TITLE             日記タイトル（必須）
  --mood MOOD               その時の気分タグ（任意）
  --tags tag1,tag2          frontmatter tags
  --from-file PATH          本文ソース（指定なしなら stdin から読む）
  --out PATH                明示保存先（指定なしなら自動算出）
EOF
    exit 2
}

TITLE=""
MOOD=""
TAGS=""
FROM_FILE=""
OUT_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --title)            TITLE="$2"; shift 2 ;;
        --mood)             MOOD="$2"; shift 2 ;;
        --tags)             TAGS="$2"; shift 2 ;;
        --from-file)        FROM_FILE="$2"; shift 2 ;;
        --out)              OUT_PATH="$2"; shift 2 ;;
        -h|--help) usage ;;
        --) shift; break ;;
        *) echo "unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$TITLE" ]] && { echo "error: --title is required" >&2; usage; }

# diary_dir を config.py（resolve_diary_dir）から解決する。環境変数 MEMORIES_DIARY_DIR が
# あれば config.py 側でそれが優先される。解決に失敗したら既定値へフォールバック。
PLUGIN_ROOT_FOR_LIB="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
DIARY_DIR="$(EPISODIC_PLUGIN_ROOT="${PLUGIN_ROOT_FOR_LIB}" python3 - <<'PY' 2>/dev/null
import os, sys
sys.path.insert(0, os.environ["EPISODIC_PLUGIN_ROOT"])
try:
    from lib import config as c
    print(c.resolve_diary_dir())
except Exception:
    print("")
PY
)"
[[ -z "$DIARY_DIR" ]] && DIARY_DIR="$HOME/.local/share/episodic/diary"

# 本文取得
TMP_BODY="$(mktemp -t diary-body.XXXXXX)"
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
    [[ -z "$SLUG" ]] && SLUG="diary"
    OUT_DIR="$DIARY_DIR/raw/diary/$DATE_DIR"
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

if [[ -n "$MOOD" ]]; then
    MOOD_YAML="\"$(yaml_escape "$MOOD")\""
else
    MOOD_YAML="null"
fi

{
    printf -- '---\n'
    printf 'kind: diary\n'
    printf 'title: "%s"\n' "$TITLE_ESC"
    printf 'date: %s\n' "$DATE_DIR"
    printf 'mood: %s\n' "$MOOD_YAML"
    printf 'created_at: %s\n' "$NOW_ISO"
    printf 'updated_at: %s\n' "$NOW_ISO"
    printf 'status: active\n'
    printf 'supersedes: null\n'
    printf 'tags: %s\n' "$TAGS_YAML"
    printf -- '---\n\n'
    cat "$TMP_BODY"
} > "$OUT_PATH"

chmod 600 "$OUT_PATH" 2>/dev/null || true

# Wiki ingest-queue へ enqueue + wiki-runner を fire-and-forget 起動。
# cocoindex update は wiki-runner 完了時に 1 回呼ばれるためここでは呼ばない（重複起動回避）。
# 起動失敗を理由に Raw 保存自体を失敗扱いにしないため、すべて || true で握る。
# diary はローカル限定なので staging 判定は不要（常に保存・連携を実行する）。
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENQUEUE="$PLUGIN_ROOT/wiki/enqueue.py"
WIKI_KICKER="$PLUGIN_ROOT/wiki/kick-runner.sh"
LOG_DIR_LOCAL="$HOME/.local/state/episodic/logs"
mkdir -p "$LOG_DIR_LOCAL" 2>/dev/null || true
chmod 700 "$LOG_DIR_LOCAL" 2>/dev/null || true
if [[ -f "$ENQUEUE" && -x "$WIKI_KICKER" ]]; then
    python3 "$ENQUEUE" "$OUT_PATH" --kind diary >/dev/null 2>&1 || true
    ( nohup "$WIKI_KICKER" >> "$LOG_DIR_LOCAL/wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
fi

echo "$OUT_PATH"
