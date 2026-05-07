#!/bin/bash
# Compass LiveUpdater をセッション終了時に停止する。
# 失敗してもセッション終了を妨げない（常に exit 0）。

SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
CONFIG_DIR="$HOME/.config/compass"
PID_DIR="$HOME/.claude/tmp"

# COMPASS_DATABASE_URL を .env から抽出（source しない）
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

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_NAME=$(basename "$PROJECT_DIR")
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
INDEX_NAME="${HOST_PREFIX}_${PROJECT_NAME}"
SANITIZED=$(echo "$INDEX_NAME" | sed 's/[^a-zA-Z0-9]/_/g')
APP_NAME="CompassIndex_${SANITIZED}"

PID_FILE="${PID_DIR}/.pid_compass_${SANITIZED}"

# --- PIDファイルベースの停止 ---
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

# --- pgrep フォールバック ---
PGREP_PIDS=$(pgrep -f "cocoindex update.*${APP_NAME}" 2>/dev/null || true)
if [[ -n "$PGREP_PIDS" ]]; then
  echo "$PGREP_PIDS" | xargs kill 2>/dev/null || true
fi

# --- VACUUM 実行（bloat 防止） ---
cd "$SCRIPTS_DIR" 2>/dev/null && \
  COMPASS_DATABASE_URL="$DB_URL" uv run python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(os.environ['COMPASS_DATABASE_URL'], connect_timeout=3)
    conn.autocommit = True
    conn.cursor().execute('VACUUM')
    conn.close()
except Exception:
    pass
" 2>/dev/null || true

exit 0
