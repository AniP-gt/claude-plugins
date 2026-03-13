#!/bin/bash
# CocoIndex LiveUpdater をセッション開始時にバックグラウンド起動する。
# 既存インデックスがあるプロジェクトのみ起動。
# 失敗してもセッション開始を妨げない（常に exit 0）。

CONFIG_DIR="$HOME/.config/cocoindex"
COMPOSE_DIR="$CONFIG_DIR"
CONTAINER_NAME="cocoindex"
SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
TEMPLATES_DIR="${CLAUDE_PLUGIN_ROOT}/templates"

# --- 0. Auto-provision config ---
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/compose.yml" ]] && [[ -f "$TEMPLATES_DIR/compose.yml" ]]; then
  cp "$TEMPLATES_DIR/compose.yml" "$CONFIG_DIR/compose.yml"
fi
if [[ ! -f "$CONFIG_DIR/.env" ]] && [[ -f "$TEMPLATES_DIR/.env.example" ]]; then
  cp "$TEMPLATES_DIR/.env.example" "$CONFIG_DIR/.env"
fi

PID_DIR="$HOME/.claude/tmp"
LOG_FILE="/tmp/cocoindex-live-updater.log"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_NAME=$(basename "$PROJECT_DIR")
SANITIZED=$(echo "$PROJECT_NAME" | sed 's/[^a-zA-Z0-9]/_/g')
TABLE_NAME="codeindex_${SANITIZED}__code_chunks"
TABLE_NAME=$(echo "$TABLE_NAME" | tr '[:upper:]' '[:lower:]')

mkdir -p "$PID_DIR"
PID_FILE="${PID_DIR}/.pid_${SANITIZED}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# --- 1. PostgreSQL コンテナ確認 ---
check_pg() {
  docker exec "$CONTAINER_NAME" pg_isready -U postgres >/dev/null 2>&1
}

if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$" || ! check_pg; then
  if [[ -f "$COMPOSE_DIR/compose.yml" ]]; then
    (cd "$COMPOSE_DIR" && docker compose up -d) >/dev/null 2>&1 || true
    for i in $(seq 1 15); do
      check_pg && break
      sleep 1
    done
  fi
  if ! check_pg; then
    log "SKIP($PROJECT_NAME): PostgreSQL unreachable"
    exit 0
  fi
fi

# --- 2. インデックステーブル存在確認 ---
EXISTS=$(docker exec "$CONTAINER_NAME" psql -U postgres -t -A -c \
  "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = '${TABLE_NAME}');" 2>/dev/null || echo "f")

if [[ "$EXISTS" != "t" ]]; then
  exit 0
fi

# --- 3. 二重起動防止 ---
# 一次チェック: プロセス名パターンで既存プロセスを検出
if pgrep -f "main.py.*--name ${SANITIZED} --live" >/dev/null 2>&1; then
  exit 0
fi

# 二次チェック: PIDファイル（フォールバック）
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0
  fi
  rm -f "$PID_FILE"
fi

# --- 4. LiveUpdater バックグラウンド起動 ---
cd "$SCRIPTS_DIR"
nohup uv run python main.py "$PROJECT_DIR" --name "$PROJECT_NAME" --live >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
log "Started live updater: project=$PROJECT_NAME PID=$!"

exit 0
