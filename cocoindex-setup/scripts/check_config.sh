#!/usr/bin/env bash
# cocoindex-setup: ~/.config/cocoindex/{secrets.env,config.toml} を雛形から auto-provision する。
#
# 役割:
#   - 既存ファイルは上書きしない（冪等）
#   - 不足ファイルだけテンプレートからコピー
#   - パーミッションを 700/600 に設定
#
# Usage:
#   check_config.sh             # auto-provision 実行
#   check_config.sh --check     # 変更せず、必要な状態が揃っているかだけ確認（不足は exit 1）
#
# 設計上の安全策:
#   - secrets.env を source しない（任意のシェルコード実行を防ぐ）
#   - パーミッション 600 で機微情報を保護

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATES_DIR="${PLUGIN_ROOT}/templates"
CONFIG_DIR="${HOME}/.config/cocoindex"
SECRETS_FILE="${CONFIG_DIR}/secrets.env"
CONFIG_FILE="${CONFIG_DIR}/config.toml"

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

log() { printf '[cocoindex-setup] %s\n' "$*" >&2; }
err() { printf '[cocoindex-setup] ERROR: %s\n' "$*" >&2; }

provision() {
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR" 2>/dev/null || true

    if [[ ! -f "$SECRETS_FILE" ]]; then
        if [[ $CHECK_ONLY -eq 1 ]]; then
            log "missing: $SECRETS_FILE"
            return 1
        fi
        if [[ ! -f "${TEMPLATES_DIR}/secrets.example.env" ]]; then
            err "template not found: ${TEMPLATES_DIR}/secrets.example.env"
            return 2
        fi
        cp "${TEMPLATES_DIR}/secrets.example.env" "$SECRETS_FILE"
        chmod 600 "$SECRETS_FILE"
        log "created $SECRETS_FILE (set VOYAGE_API_KEY)"
    fi

    if [[ ! -f "$CONFIG_FILE" ]]; then
        if [[ $CHECK_ONLY -eq 1 ]]; then
            log "missing: $CONFIG_FILE"
            return 1
        fi
        if [[ ! -f "${TEMPLATES_DIR}/config.example.toml" ]]; then
            err "template not found: ${TEMPLATES_DIR}/config.example.toml"
            return 2
        fi
        cp "${TEMPLATES_DIR}/config.example.toml" "$CONFIG_FILE"
        chmod 600 "$CONFIG_FILE"
        log "created $CONFIG_FILE"
    fi

    log "OK: $CONFIG_DIR is provisioned"
}

provision || exit 1
