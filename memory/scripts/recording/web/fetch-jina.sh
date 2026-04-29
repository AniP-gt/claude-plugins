#!/usr/bin/env bash
# fetch-jina: 指定 URL を Jina Reader (r.jina.ai) で Markdown 化し、
# memories/raw/web/YYYY-MM-DD/ 配下に frontmatter 付きで保存する。
#
# Usage:
#   fetch-jina.sh <URL> [--title <タイトル>] [--tags tag1,tag2] [--out <保存先絶対パス>]
#
# 動作:
#   1. URL 形式（http/https）を検証
#   2. https://r.jina.ai/<URL> を curl で取得（JINA_API_KEY があれば Bearer 付与）
#   3. 取得 Markdown の本文先頭から `Title:` などのメタ行を抽出してタイトル候補にする
#      （--title 指定があれば優先）
#   4. <memories_dir>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md に書き出す
#      slug は URL の host+path から英数字・ハイフンのみ抽出して 64 文字に切り詰める
#   5. 保存後、cocoindex 自動再インデックスに任せる（追加で何もしない）
#
# 環境変数:
#   MEMORIES_DIR        memories ルート（既定: /Volumes/memory）
#   JINA_API_KEY        Jina Reader 用 API key（任意。無くても rate limit 内で動作）
#   JINA_BASE_URL       既定: https://r.jina.ai
#
# Exit:
#   0  成功
#   2  引数不正 / URL 形式不正
#   3  保存先準備失敗（マウント未確立など）
#   4  curl 失敗（HTTP エラー含む）
set -euo pipefail

usage() {
    cat <<'EOF' >&2
Usage: fetch-jina.sh <URL> [--title <タイトル>] [--tags tag1,tag2] [--out <保存先絶対パス>]
EOF
    exit 2
}

URL=""
TITLE=""
TAGS=""
OUT_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --title) TITLE="$2"; shift 2 ;;
        --tags)  TAGS="$2"; shift 2 ;;
        --out)   OUT_PATH="$2"; shift 2 ;;
        -h|--help) usage ;;
        --) shift; break ;;
        -*) echo "unknown option: $1" >&2; usage ;;
        *)
            if [[ -z "$URL" ]]; then
                URL="$1"; shift
            else
                echo "extra positional arg: $1" >&2; usage
            fi
            ;;
    esac
done

[[ -z "$URL" ]] && usage

if ! [[ "$URL" =~ ^https?://[^[:space:]]+$ ]]; then
    echo "error: invalid URL (must start with http:// or https://): $URL" >&2
    exit 2
fi

MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"
JINA_BASE_URL="${JINA_BASE_URL:-https://r.jina.ai}"
# JINA_BASE_URL は http(s) のみ許容。`file://` 等を設定して curl にローカルファイルを読ませない。
if ! [[ "$JINA_BASE_URL" =~ ^https?:// ]]; then
    echo "error: JINA_BASE_URL must start with http:// or https://: $JINA_BASE_URL" >&2
    exit 2
fi

# JINA_API_KEY を ~/.config/jina/secrets.env から読み込む（環境変数優先）
JINA_KEY_FILE="${HOME}/.config/jina/secrets.env"
if [[ -z "${JINA_API_KEY:-}" && -f "$JINA_KEY_FILE" ]]; then
    # secrets.env: KEY=VALUE 形式。KEY=JINA_API_KEY のみ抽出
    while IFS= read -r line; do
        case "$line" in
            JINA_API_KEY=*)
                JINA_API_KEY="${line#JINA_API_KEY=}"
                # クォート除去
                JINA_API_KEY="${JINA_API_KEY%\"}"
                JINA_API_KEY="${JINA_API_KEY#\"}"
                JINA_API_KEY="${JINA_API_KEY%\'}"
                JINA_API_KEY="${JINA_API_KEY#\'}"
                break
                ;;
        esac
    done < "$JINA_KEY_FILE"
fi

# 保存先計算
NOW_ISO="$(date '+%Y-%m-%dT%H:%M:%S%z' | sed 's/\([+-]..\)\(..\)$/\1:\2/')"
DATE_DIR="$(date '+%Y-%m-%d')"
TIME_PREFIX="$(date '+%H%M%S')"

if [[ -z "$OUT_PATH" ]]; then
    # slug: URL から host+path の英数字・ハイフンのみ抽出、64 文字以内
    SLUG="$(printf '%s' "$URL" \
        | sed -E 's|^https?://||' \
        | tr '[:upper:]' '[:lower:]' \
        | tr -c 'a-z0-9-' '-' \
        | sed -E 's/^-+|-+$//g; s/-+/-/g' \
        | head -c 64)"
    [[ -z "$SLUG" ]] && SLUG="page"
    OUT_DIR="$MEMORIES_DIR/raw/web/$DATE_DIR"
    OUT_PATH="$OUT_DIR/${TIME_PREFIX}_${SLUG}.md"
fi

OUT_DIR="$(dirname "$OUT_PATH")"
mkdir -p "$OUT_DIR" 2>/dev/null || {
    echo "error: cannot create output dir: $OUT_DIR" >&2
    exit 3
}

# Jina Reader へリクエスト
TMP_BODY="$(mktemp -t fetch-jina-body.XXXXXX)"
TMP_STATUS="$(mktemp -t fetch-jina-status.XXXXXX)"
trap 'rm -f "$TMP_BODY" "$TMP_STATUS"' EXIT

CURL_ARGS=(-sS -L --max-time 60 -o "$TMP_BODY" -w '%{http_code}')
if [[ -n "${JINA_API_KEY:-}" ]]; then
    CURL_ARGS+=(-H "Authorization: Bearer ${JINA_API_KEY}")
fi
# Markdown 形式を明示
CURL_ARGS+=(-H "Accept: text/plain" -H "X-Return-Format: markdown")

# Jina Reader URL: prefix とユーザー指定 URL を結合（URL 自体はエンコードしない仕様）
JINA_URL="${JINA_BASE_URL%/}/${URL}"
HTTP_CODE="$(curl "${CURL_ARGS[@]}" "$JINA_URL" || echo "000")"

if [[ "$HTTP_CODE" != "200" ]]; then
    echo "error: jina-reader returned HTTP $HTTP_CODE for $URL" >&2
    head -c 500 "$TMP_BODY" >&2 || true
    echo >&2
    exit 4
fi

# Markdown 本文先頭から Title 抽出（--title 未指定時のみ）
if [[ -z "$TITLE" ]]; then
    # Jina の出力は先頭に "Title: ..." 形式で metadata が含まれることが多い
    EXTRACTED="$(awk '/^Title:[[:space:]]*/ { sub(/^Title:[[:space:]]*/, ""); print; exit }' "$TMP_BODY")"
    if [[ -n "$EXTRACTED" ]]; then
        TITLE="$EXTRACTED"
    else
        TITLE="$URL"
    fi
fi

# tags YAML フラグメント（各要素は yaml_escape で改行・引用符をエスケープ）
if [[ -n "$TAGS" ]]; then
    TAGS_YAML="["
    IFS=',' read -ra _arr <<< "$TAGS"
    first=1
    for raw in "${_arr[@]}"; do
        t="${raw// /}"
        [[ -z "$t" ]] && continue
        if [[ $first -eq 0 ]]; then
            TAGS_YAML+=", "
        fi
        TAGS_YAML+="\"$(yaml_escape "$t")\""
        first=0
    done
    TAGS_YAML+="]"
else
    TAGS_YAML="[]"
fi

# YAML エスケープ（改行除去 + 二重引用符と \ をエスケープ）。
# 改行を残すと frontmatter を破壊できるため `tr -d` で必ず除去する。
yaml_escape() {
    printf '%s' "$1" | tr -d '\n\r' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

TITLE_ESC="$(yaml_escape "$TITLE")"
URL_ESC="$(yaml_escape "$URL")"

# frontmatter + 本文を書き出し
{
    printf -- '---\n'
    printf 'kind: web\n'
    printf 'title: "%s"\n' "$TITLE_ESC"
    printf 'source_url: "%s"\n' "$URL_ESC"
    printf 'fetched_at: %s\n' "$NOW_ISO"
    printf 'fetched_via: jina-reader\n'
    printf 'http_status: %s\n' "$HTTP_CODE"
    printf 'created_at: %s\n' "$NOW_ISO"
    printf 'updated_at: %s\n' "$NOW_ISO"
    printf 'status: active\n'
    printf 'supersedes: null\n'
    printf 'tags: %s\n' "$TAGS_YAML"
    printf -- '---\n\n'
    cat "$TMP_BODY"
} > "$OUT_PATH"

# /tmp 経由ではないが、SMB 上で other-readable を避けるため 600 を試行（best effort）
chmod 600 "$OUT_PATH" 2>/dev/null || true

echo "$OUT_PATH"
