#!/bin/bash
# CocoIndex LiveUpdater をセッション終了時に停止する。
# 失敗してもセッション終了を妨げない（常に exit 0）。

SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
CONFIG_DIR="$HOME/.config/cocoindex"
PID_DIR="$HOME/.claude/tmp"

if [[ -z "$COCOINDEX_DATABASE_URL" ]]; then
  source "$CONFIG_DIR/.env" 2>/dev/null
fi
DB_URL="${COCOINDEX_DATABASE_URL:-postgres://postgres:postgres@localhost:15432/postgres}"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_NAME=$(basename "$PROJECT_DIR")
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
INDEX_NAME="${HOST_PREFIX}_${PROJECT_NAME}"
SANITIZED=$(echo "$INDEX_NAME" | sed 's/[^a-zA-Z0-9]/_/g')

PID_FILE="${PID_DIR}/.pid_cocoindex_${SANITIZED}"

# --- PIDファイルベースの停止 ---
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

# --- pgrep フォールバック ---
PGREP_PIDS=$(pgrep -f "main.py.*--name ${SANITIZED} --live" 2>/dev/null || true)
if [[ -n "$PGREP_PIDS" ]]; then
  echo "$PGREP_PIDS" | xargs kill 2>/dev/null || true
fi

# --- VACUUM 実行（bloat 防止） ---
cd "$SCRIPTS_DIR" 2>/dev/null && uv run python -c "
import psycopg2
try:
    conn = psycopg2.connect('$DB_URL', connect_timeout=3)
    conn.autocommit = True
    conn.cursor().execute('VACUUM')
    conn.close()
except Exception:
    pass
" 2>/dev/null || true

exit 0
