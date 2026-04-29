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

# --- 0. Auto-provision config files (既存は上書きしない) ---
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/secrets.env" ]] && [[ -f "$TEMPLATES_DIR/secrets.example.env" ]]; then
  cp "$TEMPLATES_DIR/secrets.example.env" "$CONFIG_DIR/secrets.env"
  echo "WARN: secrets.env をテンプレートからコピーしました。VOYAGE_API_KEY を設定してください: $CONFIG_DIR/secrets.env"
fi
if [[ ! -f "$CONFIG_DIR/config.toml" ]] && [[ -f "$TEMPLATES_DIR/config.example.toml" ]]; then
  cp "$TEMPLATES_DIR/config.example.toml" "$CONFIG_DIR/config.toml"
fi

if [[ -z "${COCOINDEX_DATABASE_URL:-}" ]]; then
  source "$CONFIG_DIR/secrets.env" 2>/dev/null || true
fi
if [[ -z "${COCOINDEX_DATABASE_URL:-}" ]]; then
  source "$CONFIG_DIR/.env" 2>/dev/null || true  # 後方互換
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

# DB_URL からホスト部分のみ抽出してログ表示用に使う（パスワード露出を避ける）
DB_DISPLAY=$(printf '%s' "$DB_URL" | sed -E 's#://[^@]+@#://***@#')

# --- 1. PostgreSQL接続確認 ---
# DB URL や TABLE NAME はシェル展開で Python ソースに直挿入せず、env var として渡す。
# これによりシングルクォート/改行などの混入によるコード注入を防止する。
PG_CHECK=$(cd "$SCRIPT_DIR" && \
  COCOINDEX_DATABASE_URL="$DB_URL" uv run python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(os.environ['COCOINDEX_DATABASE_URL'], connect_timeout=3)
    conn.close()
    print('ok')
except Exception:
    print('fail')
" 2>/dev/null)

if [[ "$PG_CHECK" == "ok" ]]; then
  echo "OK: PostgreSQL is running ($DB_DISPLAY)"
else
  echo "NG: PostgreSQL is not reachable ($DB_DISPLAY)"
  echo "    起動: docker compose -f ~/.config/cocoindex/compose.yml up -d"
  HAS_ERROR=1
fi

# --- 2. 現プロジェクトのインデックス確認 ---
if [[ "$PG_CHECK" == "ok" ]]; then
  echo ""
  echo "Project: ${PROJECT_NAME}"
  echo "Table:   ${TABLE_NAME}"

  # TABLE_NAME はシェル側で `[^a-zA-Z0-9]→_` 済みだが、SQL は psycopg2 プレースホルダーで
  # 安全に渡す（インライン展開しない）。テーブル名は識別子として sql.Identifier で quote。
  RESULT=$(cd "$SCRIPT_DIR" && \
    COCOINDEX_DATABASE_URL="$DB_URL" COCOINDEX_TABLE_NAME="$TABLE_NAME" \
    uv run python -c "
import os, psycopg2
from psycopg2 import sql
conn = psycopg2.connect(os.environ['COCOINDEX_DATABASE_URL'], connect_timeout=3)
cur = conn.cursor()
table_name = os.environ['COCOINDEX_TABLE_NAME']
cur.execute('SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = %s)', (table_name,))
if cur.fetchone()[0]:
    cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table_name)))
    print(f'ok:{cur.fetchone()[0]}')
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
