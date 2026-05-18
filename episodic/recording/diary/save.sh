#!/usr/bin/env bash
# diary/save: プライベート日記（本文のみ）を memories/raw/diary/YYYY-MM-DD/ 配下に保存する。
#
# diary は session / web / minutes と同列の 4 つ目の通常 kind。共有 NAS（memories_dir）配下
# raw/diary に保存し、staging も minutes と同じマウント前提で動作する。SMB 共有が見えて
# いなければ fallback_dir へ退避し、後追いの sync-pending.sh が移送を担当する。
#
# 入力経路（いずれか1つ）:
#   - --from-file <path>     ファイルから本文を読む
#   - stdin                  標準入力から本文を読む（パイプ・heredoc）
#
# Usage:
#   diary/save.sh [--mood "<気分>"] [--tags tag1,tag2] \
#                 [--from-file <path>] [--out <絶対パス>]
#   echo "..." | diary/save.sh
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
Usage: diary/save.sh [options]
Options:
  --mood MOOD               その時の気分タグ（任意）
  --tags tag1,tag2          frontmatter tags
  --from-file PATH          本文ソース（指定なしなら stdin から読む）
  --out PATH                明示保存先（指定なしなら自動算出）
EOF
    exit 2
}

MOOD=""
TAGS=""
FROM_FILE=""
OUT_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mood)             MOOD="$2"; shift 2 ;;
        --tags)             TAGS="$2"; shift 2 ;;
        --from-file)        FROM_FILE="$2"; shift 2 ;;
        --out)              OUT_PATH="$2"; shift 2 ;;
        -h|--help) usage ;;
        --) shift; break ;;
        *) echo "unknown option: $1" >&2; usage ;;
    esac
done

MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"

# SMB 共有が見えていなければ staging（fallback_dir）配下へ退避する。
# session / minutes 経路と挙動を揃え、外出時でも日記を保存できるようにする。
# 同期は SessionStart hook 経由の sync-pending.sh が後追いで担当する。
PLUGIN_ROOT_FOR_LIB="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
read -r MOUNT_OK FALLBACK_DIR <<EOF
$(EPISODIC_PLUGIN_ROOT="${PLUGIN_ROOT_FOR_LIB}" python3 - <<'PY' 2>/dev/null
import os, sys
sys.path.insert(0, os.environ["EPISODIC_PLUGIN_ROOT"])
try:
    from lib import config as c
    print(int(c.is_mount_active()), c.resolve_fallback_dir())
except Exception:
    print(1, "")
PY
)
EOF
MOUNT_OK="${MOUNT_OK:-1}"
IS_STAGED=0
if [[ "$MOUNT_OK" != "1" && -n "$FALLBACK_DIR" ]]; then
    IS_STAGED=1
fi

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
    # slug は本文先頭の非空行から導出する（先頭 markdown 記号を剥がす）。
    SLUG="$(grep -m1 -v '^[[:space:]]*$' "$TMP_BODY" \
        | sed -E 's/^[[:space:]]*[#>*-]+[[:space:]]*//' \
        | tr '[:upper:]' '[:lower:]' \
        | tr -c 'a-z0-9-' '-' \
        | sed -E 's/^-+|-+$//g; s/-+/-/g' \
        | head -c 48)"
    [[ -z "$SLUG" ]] && SLUG="diary"
    if [[ $IS_STAGED -eq 1 ]]; then
        OUT_DIR="$FALLBACK_DIR/diary/$DATE_DIR"
        OUT_PATH="$OUT_DIR/${TIME_PREFIX}_${SLUG}__staged.md"
    else
        OUT_DIR="$MEMORIES_DIR/raw/diary/$DATE_DIR"
        OUT_PATH="$OUT_DIR/${TIME_PREFIX}_${SLUG}.md"
    fi
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

TAGS_YAML="$(to_yaml_list "$TAGS")"

if [[ -n "$MOOD" ]]; then
    MOOD_YAML="\"$(yaml_escape "$MOOD")\""
else
    MOOD_YAML="null"
fi

{
    printf -- '---\n'
    printf 'kind: diary\n'
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

# Wiki ingest-queue へ enqueue + wiki-runner を fire-and-forget 起動。
# cocoindex update は wiki-runner 完了時に 1 回呼ばれるためここでは呼ばない（重複起動回避）。
# 起動失敗を理由に Raw 保存自体を失敗扱いにしないため、すべて || true で握る。
# staged 時は wiki / cocoindex 連携をスキップ（sync-pending.sh が移送後に担当）。
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENQUEUE="$PLUGIN_ROOT/wiki/enqueue.py"
WIKI_KICKER="$PLUGIN_ROOT/wiki/kick-runner.sh"
LOG_DIR_LOCAL="$HOME/.local/state/episodic/logs"
mkdir -p "$LOG_DIR_LOCAL" 2>/dev/null || true
chmod 700 "$LOG_DIR_LOCAL" 2>/dev/null || true
if [[ $IS_STAGED -eq 1 ]]; then
    echo "warn: SMB share not mounted; saved to staging at $OUT_PATH" >&2
    echo "      sync-pending.sh will move it to $MEMORIES_DIR/raw/diary/ on next mount." >&2
elif [[ -f "$ENQUEUE" && -x "$WIKI_KICKER" ]]; then
    python3 "$ENQUEUE" "$OUT_PATH" --kind diary >/dev/null 2>&1 || true
    ( nohup "$WIKI_KICKER" >> "$LOG_DIR_LOCAL/wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
fi

echo "$OUT_PATH"
