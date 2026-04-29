#!/bin/bash
# CocoIndex LiveUpdater をセッション開始時にバックグラウンド起動する。
# 既存インデックスがあるプロジェクトのみ起動。
# 失敗してもセッション開始を妨げない（常に exit 0）。

CONFIG_DIR="$HOME/.config/cocoindex"
SCRIPTS_DIR="${CLAUDE_PLUGIN_ROOT}/scripts"
TEMPLATES_DIR="${CLAUDE_PLUGIN_ROOT}/templates"
# --- 0. Auto-provision config files (既存ファイルは上書きしない) ---
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/secrets.env" ]] && [[ -f "$TEMPLATES_DIR/secrets.example.env" ]]; then
  cp "$TEMPLATES_DIR/secrets.example.env" "$CONFIG_DIR/secrets.env"
fi
if [[ ! -f "$CONFIG_DIR/config.toml" ]] && [[ -f "$TEMPLATES_DIR/config.example.toml" ]]; then
  cp "$TEMPLATES_DIR/config.example.toml" "$CONFIG_DIR/config.toml"
fi

# 環境変数を優先、未設定なら secrets.env / 旧 .env から読み込み（DB URL のみ hooks で使う）
if [[ -z "$COCOINDEX_DATABASE_URL" ]]; then
  source "$CONFIG_DIR/secrets.env" 2>/dev/null
fi
if [[ -z "$COCOINDEX_DATABASE_URL" ]]; then
  source "$CONFIG_DIR/.env" 2>/dev/null  # 後方互換
fi
DB_URL="${COCOINDEX_DATABASE_URL:-postgres://postgres:postgres@localhost:15432/postgres}"

PID_DIR="$HOME/.claude/tmp"
LOG_FILE="/tmp/cocoindex-live-updater.log"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_NAME=$(basename "$PROJECT_DIR")
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
INDEX_NAME="${HOST_PREFIX}_${PROJECT_NAME}"
SANITIZED=$(echo "$INDEX_NAME" | sed 's/[^a-zA-Z0-9]/_/g')
TABLE_NAME="codeindex_${SANITIZED}__code_chunks"
TABLE_NAME=$(echo "$TABLE_NAME" | tr '[:upper:]' '[:lower:]')

mkdir -p "$PID_DIR"
PID_FILE="${PID_DIR}/.pid_cocoindex_${SANITIZED}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# --- 1. PostgreSQL 接続確認 ---
# DB URL/TABLE NAME はシェル展開でインライン挿入せず env var で安全に渡す
PG_CHECK=$(cd "$SCRIPTS_DIR" && \
  COCOINDEX_DATABASE_URL="$DB_URL" uv run python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(os.environ['COCOINDEX_DATABASE_URL'], connect_timeout=3)
    conn.close()
    print('ok')
except Exception:
    print('fail')
" 2>/dev/null)

if [[ "$PG_CHECK" != "ok" ]]; then
  log "SKIP($PROJECT_NAME): PostgreSQL unreachable"
  echo "⚠️ CocoIndex: PostgreSQL unreachable at localhost:15432. コードベース検索は利用できません。起動: docker compose -f ~/.config/cocoindex/compose.yml up -d"
  exit 0
fi

# --- 2. インデックステーブル存在確認 ---
EXISTS=$(cd "$SCRIPTS_DIR" && \
  COCOINDEX_DATABASE_URL="$DB_URL" COCOINDEX_TABLE_NAME="$TABLE_NAME" \
  uv run python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['COCOINDEX_DATABASE_URL'], connect_timeout=3)
cur = conn.cursor()
cur.execute('SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = %s)', (os.environ['COCOINDEX_TABLE_NAME'],))
print('t' if cur.fetchone()[0] else 'f')
conn.close()
" 2>/dev/null || echo "f")

if [[ "$EXISTS" != "t" ]]; then
  exit 0
fi

# --- 3. 二重起動防止 ---
if pgrep -f "main.py.*--name ${SANITIZED} --live" >/dev/null 2>&1; then
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    exit 0
  fi
  rm -f "$PID_FILE"
fi

# --- 4. LiveUpdater バックグラウンド起動 ---
cd "$SCRIPTS_DIR"
nohup uv run python main.py "$PROJECT_DIR" --name "$SANITIZED" --live >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
log "Started live updater: index=$SANITIZED PID=$!"

exit 0
