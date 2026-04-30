#!/bin/bash
# Compass LiveUpdater をセッション開始時にバックグラウンド起動する。
# 既存インデックスがあるプロジェクトのみ起動。
# 失敗してもセッション開始を妨げない（常に exit 0）。

CONFIG_DIR="$HOME/.config/compass"
COCOINDEX_CFG_DIR="$HOME/.config/cocoindex"
SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
TEMPLATES_DIR="${SCRIPTS_DIR}/templates"

# --- 0. compass 専用 config の auto-provision（既存は上書きしない） ---
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/.env" ]] && [[ -f "$TEMPLATES_DIR/compass.env.example" ]]; then
  cp "$TEMPLATES_DIR/compass.env.example" "$CONFIG_DIR/.env"
  chmod 600 "$CONFIG_DIR/.env" 2>/dev/null || true
fi
if [[ ! -f "$CONFIG_DIR/secrets.env" ]] && [[ -f "$TEMPLATES_DIR/compass_secrets.env.example" ]]; then
  cp "$TEMPLATES_DIR/compass_secrets.env.example" "$CONFIG_DIR/secrets.env"
  chmod 600 "$CONFIG_DIR/secrets.env" 2>/dev/null || true
fi

# 環境変数を優先、未設定なら .env から COMPASS_DATABASE_URL の値だけ抽出（source しない）
extract_env_value() {
  local file="$1" key="$2" line value
  [[ -f "$file" ]] || return 0
  line=$(grep -E "^[[:space:]]*${key}=" "$file" 2>/dev/null | grep -vE "^[[:space:]]*#" | tail -1)
  [[ -z "$line" ]] && return 0
  value="${line#*=}"
  if [[ "$value" =~ ^\"(.*)\"$ ]]; then
    value="${BASH_REMATCH[1]}"
  elif [[ "$value" =~ ^\'(.*)\'$ ]]; then
    value="${BASH_REMATCH[1]}"
  fi
  printf '%s' "$value"
}

if [[ -z "${COMPASS_DATABASE_URL:-}" ]]; then
  COMPASS_DATABASE_URL="$(extract_env_value "$CONFIG_DIR/.env" "COMPASS_DATABASE_URL")"
fi
DB_URL="${COMPASS_DATABASE_URL:-postgres://postgres:postgres@localhost:15432/compass}"

PID_DIR="$HOME/.claude/tmp"
LOG_FILE="/tmp/compass-live-updater.log"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_NAME=$(basename "$PROJECT_DIR")
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
INDEX_NAME="${HOST_PREFIX}_${PROJECT_NAME}"
SANITIZED=$(echo "$INDEX_NAME" | sed 's/[^a-zA-Z0-9]/_/g')
TABLE_NAME="compassindex_${SANITIZED}__chunks"
TABLE_NAME=$(echo "$TABLE_NAME" | tr '[:upper:]' '[:lower:]')
APP_NAME="CompassIndex_${SANITIZED}"

mkdir -p "$PID_DIR"
PID_FILE="${PID_DIR}/.pid_compass_${SANITIZED}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# --- 1. PostgreSQL 接続確認 ---
PG_CHECK=$(cd "$SCRIPTS_DIR" && \
  COMPASS_DATABASE_URL="$DB_URL" uv run python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(os.environ['COMPASS_DATABASE_URL'], connect_timeout=3)
    conn.close()
    print('ok')
except Exception:
    print('fail')
" 2>/dev/null)

if [[ "$PG_CHECK" != "ok" ]]; then
  log "SKIP($PROJECT_NAME): PostgreSQL unreachable"
  echo "⚠️ Compass: PostgreSQL unreachable at localhost:15432. コードベース検索は利用できません。起動: docker compose -f ~/.config/cocoindex/compose.yml up -d"
  exit 0
fi

# --- 2. インデックステーブル存在確認 ---
EXISTS=$(cd "$SCRIPTS_DIR" && \
  COMPASS_DATABASE_URL="$DB_URL" COMPASS_TABLE_NAME="$TABLE_NAME" \
  uv run python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['COMPASS_DATABASE_URL'], connect_timeout=3)
cur = conn.cursor()
cur.execute('SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = %s)', (os.environ['COMPASS_TABLE_NAME'],))
print('t' if cur.fetchone()[0] else 'f')
conn.close()
" 2>/dev/null || echo "f")

if [[ "$EXISTS" != "t" ]]; then
  exit 0
fi

# --- 3. 二重起動防止 ---
if pgrep -f "cocoindex update.*${APP_NAME}" >/dev/null 2>&1; then
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0
  fi
  rm -f "$PID_FILE"
fi

# --- 4. LiveUpdater バックグラウンド起動（cocoindex 1.0 CLI） ---
# 親 bash 終了に追従されないよう、サブシェル + nohup + & + disown で完全に切り離す。
# stdin/stdout/stderr は明示的に detach する（Claude Code Bash の session 終了で
# 子プロセスがクリーンアップされる挙動への対策）。
PATTERNS_DEFAULT="**/*.rb,**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.go"
LIVE_PATTERNS="${PATTERNS:-$PATTERNS_DEFAULT}"
(
  cd "$SCRIPTS_DIR" \
    && SOURCE_PATH="$PROJECT_DIR" \
       PATTERNS="$LIVE_PATTERNS" \
       COMPASS_DATABASE_URL="$DB_URL" \
       nohup uv run cocoindex update -L -f "main.py:${APP_NAME}" \
       </dev/null >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  disown 2>/dev/null || true
) >/dev/null 2>&1 || true
log "Started live updater: app=${APP_NAME}"

exit 0
