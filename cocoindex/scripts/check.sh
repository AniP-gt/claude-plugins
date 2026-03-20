#!/bin/bash
# CocoIndex ヘルスチェック: PostgreSQL接続 + 現プロジェクトのインデックス確認
#
# 使い方: bash check.sh
# 終了コード: 0=正常, 1=異常あり
#
# CLAUDE_PROJECT_DIR からプロジェクト名・テーブル名を自動計算する。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATES_DIR="$PLUGIN_ROOT/templates"

CONFIG_DIR="$HOME/.config/cocoindex"

# --- 0. Auto-provision .env ---
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/.env" ]] && [[ -f "$TEMPLATES_DIR/.env.example" ]]; then
  cp "$TEMPLATES_DIR/.env.example" "$CONFIG_DIR/.env"
  echo "WARN: .env をテンプレートからコピーしました。VOYAGE_API_KEY を設定してください: $CONFIG_DIR/.env"
fi

if [[ -z "${COCOINDEX_DATABASE_URL:-}" ]]; then
  source "$CONFIG_DIR/.env" 2>/dev/null || true
fi
DB_URL="${COCOINDEX_DATABASE_URL:-postgres://postgres:postgres@localhost:15432/postgres}"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
PROJECT_NAME=$(basename "$PROJECT_DIR")
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
INDEX_NAME="${HOST_PREFIX}_${PROJECT_NAME}"
SANITIZED=$(echo "$INDEX_NAME" | sed 's/[^a-zA-Z0-9]/_/g')
TABLE_NAME="codeindex_${SANITIZED}__code_chunks"
TABLE_NAME=$(echo "$TABLE_NAME" | tr '[:upper:]' '[:lower:]')

HAS_ERROR=0

# --- 1. PostgreSQL接続確認 ---
PG_CHECK=$(cd "$SCRIPT_DIR" && uv run python -c "
import psycopg2
try:
    conn = psycopg2.connect('$DB_URL', connect_timeout=3)
    conn.close()
    print('ok')
except Exception:
    print('fail')
" 2>/dev/null)

if [[ "$PG_CHECK" == "ok" ]]; then
  echo "OK: PostgreSQL is running ($DB_URL)"
else
  echo "NG: PostgreSQL is not reachable ($DB_URL)"
  echo "    起動: docker compose -f ~/.config/cocoindex/compose.yml up -d"
  HAS_ERROR=1
fi

# --- 2. 現プロジェクトのインデックス確認 ---
if [[ "$PG_CHECK" == "ok" ]]; then
  echo ""
  echo "Project: ${PROJECT_NAME}"
  echo "Table:   ${TABLE_NAME}"

  RESULT=$(cd "$SCRIPT_DIR" && uv run python -c "
import psycopg2
conn = psycopg2.connect('$DB_URL', connect_timeout=3)
cur = conn.cursor()
cur.execute(\"SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = '${TABLE_NAME}')\")
exists = cur.fetchone()[0]
if exists:
    cur.execute('SELECT count(*) FROM \"${TABLE_NAME}\"')
    count = cur.fetchone()[0]
    print(f'ok:{count}')
else:
    print('notfound')
conn.close()
" 2>/dev/null || echo "error")

  if [[ "$RESULT" == notfound ]]; then
    echo "Index:   NOT FOUND (run setup to build)"
    HAS_ERROR=1
  elif [[ "$RESULT" == error ]]; then
    echo "Index:   ERROR (query failed)"
    HAS_ERROR=1
  else
    COUNT="${RESULT#ok:}"
    echo "Index:   OK ($COUNT chunks)"
  fi
fi

exit $HAS_ERROR
