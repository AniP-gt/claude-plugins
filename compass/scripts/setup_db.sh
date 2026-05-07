#!/usr/bin/env bash
# compass プラグイン専用 PostgreSQL データベースのセットアップ。
#
# 役割:
#   1. ~/.config/compass/.env と secrets.env を雛形から auto-provision（既存は上書きしない）
#   2. PostgreSQL に "compass" データベースを冪等作成
#   3. compass DB に pgvector 拡張を冪等作成（CREATE EXTENSION IF NOT EXISTS vector）
#
# 前提:
#   - pgvector-stack プラグイン由来の PostgreSQL コンテナ "cocoindex" が起動済み
#   - 接続情報は COMPASS_DATABASE_URL（未設定なら ~/.config/compass/.env、さらに既定値）から解決
#
# 設計上の安全策:
#   - .env を `source` しない（任意のシェルコード実行を防ぐ）。COMPASS_DATABASE_URL の値だけを抽出する
#   - python3 の出力を eval しない（パスワードに含まれるシェルメタ文字によるコード実行を防ぐ）
#   - SQL に DB_NAME を文字列展開しない。psql の -v バインド変数 + 識別子検証で渡す
#   - URL 全体をログに出さない（パスワード混入を避ける）
#
# Usage:
#   setup_db.sh                # 全工程を冪等実行
#   setup_db.sh --check        # 変更せず、必要な状態が揃っているかだけ確認
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES_DIR="${SCRIPT_DIR}/templates"
CONFIG_DIR="${HOME}/.config/compass"
ENV_FILE="${CONFIG_DIR}/.env"
SECRETS_FILE="${CONFIG_DIR}/secrets.env"

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

log() { printf '[compass:setup_db] %s\n' "$*" >&2; }
err() { printf '[compass:setup_db] ERROR: %s\n' "$*" >&2; }

# 1. 雛形を ~/.config/compass/ に展開（既存は触らない）
provision_config() {
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ $CHECK_ONLY -eq 1 ]]; then
            log "missing: $ENV_FILE"
            return 1
        fi
        cp "${TEMPLATES_DIR}/compass.env.example" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log "created $ENV_FILE"
    fi
    if [[ ! -f "$SECRETS_FILE" ]]; then
        if [[ $CHECK_ONLY -eq 1 ]]; then
            log "missing: $SECRETS_FILE"
            return 1
        fi
        cp "${TEMPLATES_DIR}/compass_secrets.env.example" "$SECRETS_FILE"
        chmod 600 "$SECRETS_FILE"
        log "created $SECRETS_FILE"
    fi
}

# 依存プラグイン検知（pgvector-stack / cocoindex-setup）
check_dependencies() {
    if ! docker ps --format '{{.Names}}' | grep -q '^cocoindex$'; then
        err "PostgreSQL コンテナ 'cocoindex' が起動していません"
        err "  pgvector-stack プラグインをインストール後、起動してください:"
        err "    /plugin install pgvector-stack@hidetsugu-miya"
        err "    docker compose -f ~/.config/cocoindex/compose.yml up -d"
        return 3
    fi

    # cocoindex-setup の secrets hub を検知（fallback chain の上流）
    if [[ ! -f "${HOME}/.config/cocoindex/secrets.env" ]]; then
        log "WARN: ~/.config/cocoindex/secrets.env が未配置です"
        log "  cocoindex-setup プラグイン推奨インストール:"
        log "    /plugin install cocoindex-setup@hidetsugu-miya"
        log "    bash \$\\{CLAUDE_PLUGIN_ROOT\\}/scripts/check_config.sh"
    fi
}

# .env から COMPASS_DATABASE_URL の値だけを抽出する（source しない）。
extract_env_value() {
    local file="$1" key="$2" line value
    [[ -f "$file" ]] || return 0
    line=$(grep -E "^[[:space:]]*${key}=" "$file" | grep -vE "^[[:space:]]*#" | tail -1)
    [[ -z "$line" ]] && return 0
    value="${line#*=}"
    if [[ "$value" =~ ^\"(.*)\"$ ]]; then
        value="${BASH_REMATCH[1]}"
    elif [[ "$value" =~ ^\'(.*)\'$ ]]; then
        value="${BASH_REMATCH[1]}"
    fi
    printf '%s' "$value"
}

resolve_db_url() {
    # 優先順位: 既存 env > ~/.config/compass/.env > 既定値
    if [[ -n "${COMPASS_DATABASE_URL:-}" ]]; then
        printf '%s' "$COMPASS_DATABASE_URL"
        return
    fi
    local from_file
    from_file=$(extract_env_value "$ENV_FILE" "COMPASS_DATABASE_URL")
    if [[ -n "$from_file" ]]; then
        printf '%s' "$from_file"
        return
    fi
    printf '%s' "postgres://postgres:postgres@localhost:15432/compass"
}

# URL から接続パラメータを 1 変数ずつ標準出力に出す。null 区切りで安全に渡す。
parse_db_url_python() {
    local url="$1"
    python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse
u = urlparse(sys.argv[1])
def w(s):
    sys.stdout.write(str(s))
    sys.stdout.write("\0")
w(u.username or "postgres")
w(u.password or "postgres")
w(u.hostname or "localhost")
w(u.port or 5432)
w((u.path or "/postgres").lstrip("/"))
sys.stdout.flush()
PY
}

# psql を docker exec 経由で叩く（コンテナ名 cocoindex 固定）。
# パスワードは PGPASSWORD env で渡し、ホスト ps からも docker argv からも見えないようにする。
psql_exec() {
    local db="$1"; shift
    PGPASSWORD="${DB_PASS}" docker exec -i -e PGPASSWORD cocoindex \
        psql -U "$DB_USER" -d "$db" -v ON_ERROR_STOP=1 "$@"
}

# 2. compass database を冪等作成（SQL に DB_NAME を文字列展開しない）
ensure_database() {
    local exists
    if ! [[ "$DB_NAME" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
        err "invalid database name (allowed: ^[a-zA-Z_][a-zA-Z0-9_]*\$): $DB_NAME"
        exit 2
    fi
    exists=$(printf 'SELECT 1 FROM pg_database WHERE datname = :%s;\n' "'db_name'" \
        | psql_exec postgres -tA -v db_name="$DB_NAME" 2>&1)
    if [[ "$exists" == "1" ]]; then
        log "database '$DB_NAME' already exists"
        return 0
    fi
    if [[ $CHECK_ONLY -eq 1 ]]; then
        log "missing: database '$DB_NAME'"
        return 1
    fi
    log "creating database '$DB_NAME'..."
    psql_exec postgres -c "CREATE DATABASE \"$DB_NAME\""
}

# 3. pgvector extension を冪等作成
ensure_extension() {
    local installed
    installed=$(printf "SELECT 1 FROM pg_extension WHERE extname = 'vector';\n" \
        | psql_exec "$DB_NAME" -tA 2>&1)
    if [[ "$installed" == "1" ]]; then
        log "extension 'vector' already installed in '$DB_NAME'"
        return 0
    fi
    if [[ $CHECK_ONLY -eq 1 ]]; then
        log "missing: extension 'vector' in '$DB_NAME'"
        return 1
    fi
    log "creating extension 'vector' in '$DB_NAME'..."
    psql_exec "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector"
}

main() {
    provision_config || { err "config provisioning failed (check mode)"; exit 1; }
    check_dependencies || exit $?

    local url
    url=$(resolve_db_url)

    local DB_USER DB_PASS DB_HOST DB_PORT DB_NAME
    {
        IFS= read -r -d '' DB_USER
        IFS= read -r -d '' DB_PASS
        IFS= read -r -d '' DB_HOST
        IFS= read -r -d '' DB_PORT
        IFS= read -r -d '' DB_NAME
    } < <(parse_db_url_python "$url")

    log "target: host=${DB_HOST} port=${DB_PORT} db=${DB_NAME} user=${DB_USER}"

    ensure_database || exit 1
    ensure_extension || exit 1

    log "OK"
}

main "$@"
