#!/usr/bin/env bash
# episodic uninstall: episodic プラグインがローカルに作成したものを削除する。
#
# 既定で削除（プラグイン管理の設定・ランタイム・キャッシュ・ログ）:
#   1. PostgreSQL の "episodic" database（コンテナ cocoindex 上、FORCE で切断）
#   2. ~/.config/episodic/（.env / secrets.env / config.toml / cocoindex.toml /
#                           codex-hook-runtime のミラー一式）
#   3. ~/.local/state/episodic/（logs / pending / machine_id）
#   4. ~/.cache/episodic/（uv venv）
#
# --purge 指定時のみ追加削除（未同期セッションデータを含むため既定では保護）:
#   5. ~/.local/share/episodic/（raw-staging の未同期 session / retry queue /
#                                cocoindex tracking）
#
# 常に保護（削除しない）:
#   - memories_dir（/Volumes/memory 等の外部データ実体）。手動削除すること
#   - コンテナ "cocoindex" / ボリューム pgdata（pgvector-stack 所有）
#   - ~/.config/cocoindex/secrets.env（cocoindex-setup 所有、共有 hub）
#
# 設計上の安全策（setup_db.sh と同じ方針）:
#   - .env を source しない。EPISODIC_DATABASE_URL の値だけ抽出する
#   - python3 出力を eval しない（null 区切りで受け取る）
#   - DROP DATABASE の対象名は許可文字（英数 + _）に限定して検証する
#
# Usage:
#   uninstall.sh             # 既定削除（確認プロンプトあり）
#   uninstall.sh --purge     # ~/.local/share/episodic/ も削除
#   uninstall.sh --yes       # 確認なしで削除（非対話シェルでは必須）
#   uninstall.sh --dry-run   # 何も削除せず、実行予定だけ表示
set -u

PLUGIN="episodic"
ASSUME_YES=0
DRY_RUN=0
PURGE=0
CONFIG_DIR="${HOME}/.config/episodic"
ENV_FILE="${CONFIG_DIR}/.env"
STATE_DIR="${HOME}/.local/state/episodic"
SHARE_DIR="${HOME}/.local/share/episodic"
CACHE_DIR="${HOME}/.cache/episodic"
DEFAULT_DB_NAME="episodic"

log() { printf '[%s:uninstall] %s\n' "$PLUGIN" "$*" >&2; }
err() { printf '[%s:uninstall] ERROR: %s\n' "$PLUGIN" "$*" >&2; }

usage() {
    cat >&2 <<EOF
Usage: uninstall.sh [--purge] [--yes|-y] [--dry-run|-n] [--help|-h]
  --purge    ~/.local/share/episodic/（未同期 session / retry queue）も削除
  --yes      確認プロンプトをスキップ（非対話シェルでは必須）
  --dry-run  何も削除せず、実行予定だけ表示
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes) ASSUME_YES=1 ;;
        -n|--dry-run) DRY_RUN=1 ;;
        --purge) PURGE=1 ;;
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

# .env から EPISODIC_DATABASE_URL の値だけを抽出する（source しない）。
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
    if [[ -n "${EPISODIC_DATABASE_URL:-}" ]]; then
        printf '%s' "$EPISODIC_DATABASE_URL"; return
    fi
    extract_env_value "$ENV_FILE" "EPISODIC_DATABASE_URL"
}

# URL から user / password / db を null 区切りで出す。URL 空なら既定 db 名にフォールバック。
parse_db_url_python() {
    python3 - "$1" "$DEFAULT_DB_NAME" <<'PY'
import sys
from urllib.parse import urlparse
url, default_db = sys.argv[1], sys.argv[2]
u = urlparse(url) if url else None
def w(s):
    sys.stdout.write(str(s)); sys.stdout.write("\0")
w((u.username if u else None) or "postgres")
w((u.password if u else None) or "postgres")
w(((u.path.lstrip("/") if u and u.path else "") or default_db))
sys.stdout.flush()
PY
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
    log "  - PostgreSQL database 'episodic'（コンテナ cocoindex 上）"
    log "  - $CONFIG_DIR （config / secrets / codex-hook-runtime）"
    log "  - $STATE_DIR （logs / pending / machine_id）"
    log "  - $CACHE_DIR （uv venv）"
    if [[ $PURGE -eq 1 ]]; then
        log "  - $SHARE_DIR （--purge: 未同期 session / retry queue）"
    else
        log "保護（--purge 未指定）: $SHARE_DIR （未同期 session / retry queue）"
    fi
    log "保護（常時）: memories_dir（/Volumes/memory 等）は手動削除してください。"
    log "保護（共有）: コンテナ cocoindex / ~/.config/cocoindex/ は削除しません。"

    confirm "episodic のローカルリソースを削除しますか？" || { log "中止しました"; exit 0; }

    drop_database
    remove_path "$CONFIG_DIR"
    remove_path "$STATE_DIR"
    remove_path "$CACHE_DIR"
    if [[ $PURGE -eq 1 ]]; then
        remove_path "$SHARE_DIR"
    else
        log "kept: $SHARE_DIR （削除するには --purge を付けて再実行）"
    fi

    log "完了"
}

main "$@"
