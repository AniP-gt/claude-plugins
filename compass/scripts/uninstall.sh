#!/usr/bin/env bash
# compass uninstall: compass プラグインがローカルに作成したものを削除する。
#
# 削除対象（compass 専用リソースのみ）:
#   1. LiveUpdater プロセス停止 + PID ファイル（~/.claude/tmp/.pid_compass_*）
#   2. PostgreSQL の "compass" database（コンテナ cocoindex 上、FORCE で切断）
#   3. ~/.config/compass/（.env / secrets.env / cocoindex.toml）
#   4. /tmp/compass-live-updater.log
#
# 触れないもの（共有リソース）:
#   - コンテナ "cocoindex" / ボリューム pgdata（pgvector-stack 所有）
#   - ~/.config/cocoindex/secrets.env（cocoindex-setup 所有、共有 hub）
#
# 設計上の安全策（setup_db.sh と同じ方針）:
#   - .env を source しない。COMPASS_DATABASE_URL の値だけ抽出する
#   - python3 出力を eval しない（null 区切りで受け取る）
#   - DROP DATABASE の対象名は許可文字（英数 + _）に限定して検証する
#
# Usage:
#   uninstall.sh            # 確認プロンプトの上で削除
#   uninstall.sh --yes      # 確認なしで削除（非対話シェルではこれが必須）
#   uninstall.sh --dry-run  # 何も削除せず、実行予定だけ表示
set -u

PLUGIN="compass"
ASSUME_YES=0
DRY_RUN=0
CONFIG_DIR="${HOME}/.config/compass"
ENV_FILE="${CONFIG_DIR}/.env"
LOG_FILE="/tmp/compass-live-updater.log"
DEFAULT_URL="postgres://postgres:postgres@localhost:15432/compass"

log() { printf '[%s:uninstall] %s\n' "$PLUGIN" "$*" >&2; }
err() { printf '[%s:uninstall] ERROR: %s\n' "$PLUGIN" "$*" >&2; }

usage() {
    cat >&2 <<EOF
Usage: uninstall.sh [--yes|-y] [--dry-run|-n] [--help|-h]
  --yes      確認プロンプトをスキップ（非対話シェルでは必須）
  --dry-run  何も削除せず、実行予定だけ表示
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes) ASSUME_YES=1 ;;
        -n|--dry-run) DRY_RUN=1 ;;
        -h|--help) usage; exit 0 ;;
        *) err "unknown option: $1"; usage; exit 2 ;;
    esac
    shift
done

confirm() {
    [[ $ASSUME_YES -eq 1 || $DRY_RUN -eq 1 ]] && return 0
    if [[ ! -t 0 ]]; then
        err "非対話シェルです。--yes を付けて実行してください（--dry-run で事前確認も可）。"
        exit 3
    fi
    printf '%s [y/N]: ' "$1" >&2
    local ans; read -r ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

remove_path() {
    local p="$1"
    if [[ ! -e "$p" && ! -L "$p" ]]; then
        log "skip (absent): $p"
        return
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
        log "would remove: $p"
    else
        rm -rf "$p" && log "removed: $p"
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
    if [[ -n "${COMPASS_DATABASE_URL:-}" ]]; then
        printf '%s' "$COMPASS_DATABASE_URL"; return
    fi
    local from_file
    from_file=$(extract_env_value "$ENV_FILE" "COMPASS_DATABASE_URL")
    if [[ -n "$from_file" ]]; then
        printf '%s' "$from_file"; return
    fi
    printf '%s' "$DEFAULT_URL"
}

parse_db_url_python() {
    python3 - "$1" <<'PY'
import sys
from urllib.parse import urlparse
u = urlparse(sys.argv[1])
def w(s):
    sys.stdout.write(str(s)); sys.stdout.write("\0")
w(u.username or "postgres")
w(u.password or "postgres")
w((u.path or "/postgres").lstrip("/"))
sys.stdout.flush()
PY
}

stop_live_updaters() {
    local f pid
    shopt -s nullglob
    for f in "${HOME}/.claude/tmp/".pid_compass_*; do
        pid="$(tr -dc '0-9' < "$f" 2>/dev/null)"
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            if [[ $DRY_RUN -eq 1 ]]; then
                log "would kill LiveUpdater pid=$pid ($f)"
            else
                kill "$pid" 2>/dev/null && log "killed LiveUpdater pid=$pid"
            fi
        fi
        remove_path "$f"
    done
    shopt -u nullglob
}

drop_database() {
    if ! command -v docker >/dev/null 2>&1; then
        log "docker not found; DROP DATABASE をスキップ"
        return 0
    fi
    if ! docker ps --format '{{.Names}}' | grep -q '^cocoindex$'; then
        log "コンテナ 'cocoindex' 未起動; DROP DATABASE をスキップ（DB はボリューム削除時に消去される）"
        return 0
    fi
    local url DB_USER DB_PASS DB_NAME
    url=$(resolve_db_url)
    { IFS= read -r -d '' DB_USER
      IFS= read -r -d '' DB_PASS
      IFS= read -r -d '' DB_NAME
    } < <(parse_db_url_python "$url")
    if ! [[ "$DB_NAME" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
        err "invalid database name (allowed: ^[a-zA-Z_][a-zA-Z0-9_]*\$): $DB_NAME"
        return 1
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
        log "would: DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE) on container cocoindex"
        return 0
    fi
    log "dropping database '$DB_NAME'..."
    printf 'DROP DATABASE IF EXISTS "%s" WITH (FORCE);\n' "$DB_NAME" \
        | PGPASSWORD="$DB_PASS" docker exec -i -e PGPASSWORD cocoindex \
            psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 \
        && log "dropped database '$DB_NAME'"
}

main() {
    log "削除対象:"
    log "  - LiveUpdater プロセス + ~/.claude/tmp/.pid_compass_*"
    log "  - PostgreSQL database 'compass'（コンテナ cocoindex 上）"
    log "  - $CONFIG_DIR"
    log "  - $LOG_FILE"
    log "注意: コンテナ cocoindex と ~/.config/cocoindex/ は他プラグイン共有のため削除しません。"

    confirm "compass のローカルリソースを削除しますか？" || { log "中止しました"; exit 0; }

    stop_live_updaters
    drop_database
    remove_path "$CONFIG_DIR"
    remove_path "$LOG_FILE"

    log "完了"
}

main "$@"
