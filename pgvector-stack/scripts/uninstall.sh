#!/usr/bin/env bash
# pgvector-stack uninstall: PostgreSQL コンテナ "cocoindex" とデータボリュームを削除する。
#
# 削除対象（このプラグインが所有するもののみ）:
#   1. docker コンテナ "cocoindex" とボリューム pgdata（compose down -v）
#   2. ~/.config/cocoindex/compose.yml
#   3. ~/.config/cocoindex/（空になった場合のみ rmdir）
#
# 重要: ボリューム削除は compass / episodic を含む全 database を消去する。
#   secrets.env / config.toml（cocoindex-setup 所有）には触れない。
#
# Usage:
#   uninstall.sh            # 確認プロンプトの上で削除
#   uninstall.sh --yes      # 確認なしで削除（非対話シェルではこれが必須）
#   uninstall.sh --dry-run  # 何も削除せず、実行予定だけ表示
set -u

PLUGIN="pgvector-stack"
ASSUME_YES=0
DRY_RUN=0
CONFIG_DIR="${HOME}/.config/cocoindex"
COMPOSE_FILE="${CONFIG_DIR}/compose.yml"

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

rmdir_if_empty() {
    local d="$1"
    [[ -d "$d" ]] || return 0
    if [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
        log "kept (not empty): $d"
        return 0
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
        log "would rmdir (empty): $d"
    else
        rmdir "$d" 2>/dev/null && log "removed empty dir: $d"
    fi
}

remove_container_and_volume() {
    if ! command -v docker >/dev/null 2>&1; then
        log "docker not found; コンテナ/ボリュームの削除をスキップ"
        return 0
    fi
    if [[ -f "$COMPOSE_FILE" ]]; then
        if [[ $DRY_RUN -eq 1 ]]; then
            log "would run: docker compose -f $COMPOSE_FILE down -v"
        else
            docker compose -f "$COMPOSE_FILE" down -v \
                && log "removed container 'cocoindex' + volume (compose down -v)"
        fi
        return 0
    fi
    log "compose.yml が無いため、コンテナ/ボリュームを直接削除する"
    if docker ps -a --format '{{.Names}}' | grep -q '^cocoindex$'; then
        if [[ $DRY_RUN -eq 1 ]]; then
            log "would run: docker rm -f cocoindex"
        else
            docker rm -f cocoindex && log "removed container 'cocoindex'"
        fi
    fi
    # compose プロジェクト名 'cocoindex' により実ボリューム名は cocoindex_pgdata。
    local vol
    for vol in cocoindex_pgdata pgdata; do
        if docker volume ls --format '{{.Name}}' | grep -q "^${vol}$"; then
            if [[ $DRY_RUN -eq 1 ]]; then
                log "would run: docker volume rm $vol"
            else
                docker volume rm "$vol" && log "removed volume '$vol'"
            fi
        fi
    done
}

main() {
    log "削除対象:"
    log "  - docker コンテナ 'cocoindex' + データボリューム pgdata"
    log "  - $COMPOSE_FILE"
    log "  - $CONFIG_DIR （空の場合のみ）"
    log "警告: ボリューム削除で compass / episodic を含む全 database が消えます。"
    log "      secrets.env / config.toml（cocoindex-setup 所有）は削除しません。"

    confirm "pgvector-stack のコンテナとデータを削除しますか？（取り消し不可）" || { log "中止しました"; exit 0; }

    remove_container_and_volume
    remove_path "$COMPOSE_FILE"
    rmdir_if_empty "$CONFIG_DIR"

    log "完了"
}

main "$@"
