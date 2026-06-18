#!/usr/bin/env bash
# cocoindex-setup uninstall: 共通 secrets hub のファイルを削除する。
#
# 削除対象（このプラグインが所有するファイルのみ）:
#   1. ~/.config/cocoindex/secrets.env
#   2. ~/.config/cocoindex/config.toml
#   3. ~/.config/cocoindex/（空になった場合のみ rmdir）
#
# 重要: compose.yml（pgvector-stack 所有）には触れない。
#   secrets.env は compass / episodic の fallback secrets hub なので、
#   下流プラグインを使い続ける場合は削除しないこと。
#
# Usage:
#   uninstall.sh            # 確認プロンプトの上で削除
#   uninstall.sh --yes      # 確認なしで削除（非対話シェルではこれが必須）
#   uninstall.sh --dry-run  # 何も削除せず、実行予定だけ表示
set -u

PLUGIN="cocoindex-setup"
ASSUME_YES=0
DRY_RUN=0
CONFIG_DIR="${HOME}/.config/cocoindex"
SECRETS_FILE="${CONFIG_DIR}/secrets.env"
CONFIG_FILE="${CONFIG_DIR}/config.toml"

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
        rm -f "$p" && log "removed: $p"
    fi
}

rmdir_if_empty() {
    local d="$1"
    [[ -d "$d" ]] || return 0
    if [[ -n "$(ls -A "$d" 2>/dev/null)" ]]; then
        log "kept (not empty): $d  （compose.yml など他プラグインのファイルが残存）"
        return 0
    fi
    if [[ $DRY_RUN -eq 1 ]]; then
        log "would rmdir (empty): $d"
    else
        rmdir "$d" 2>/dev/null && log "removed empty dir: $d"
    fi
}

main() {
    log "削除対象:"
    log "  - $SECRETS_FILE"
    log "  - $CONFIG_FILE"
    log "  - $CONFIG_DIR （空の場合のみ）"
    log "注意: compose.yml（pgvector-stack 所有）は削除しません。"
    log "      secrets.env は compass / episodic の fallback hub です。"
    log "      下流プラグインを使い続けるなら削除しないでください。"

    confirm "cocoindex-setup の secrets/config を削除しますか？" || { log "中止しました"; exit 0; }

    remove_path "$SECRETS_FILE"
    remove_path "$CONFIG_FILE"
    rmdir_if_empty "$CONFIG_DIR"

    log "完了"
}

main "$@"
