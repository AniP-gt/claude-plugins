#!/bin/bash
# SMB 共有を memories マウントポイントへマウントする macOS 用ヘルパー。
# 設定の優先順位: 環境変数 > ~/.config/recording/secrets.env > ~/.config/recording/config.toml > プレースホルダ既定
#
# - 公開可能な設定（共有 URL / ping host）は config.toml に書く。
# - シークレット情報（user 名、将来的なパスワード等）は secrets.env に書き、chmod 600 を必須とする。
# - 環境変数（MEMORIES_SMB_SHARE / MEMORIES_SMB_USER / MEMORIES_SMB_PING_HOST）が設定されていれば最優先。
# - 認証は macOS キーチェーンから自動解決される（user 名のみ secrets.env で渡す）。
#
# macOS 以外では mount_smbfs / /sbin/mount / /sbin/ping が無いため、自動的にスキップする
# （ログだけ残して exit 0）。Linux/Windows で SMB を使いたい場合は config.toml の
# remount_script を環境固有のラッパー（mount.cifs / net use など）へ差し替えること。

set -uo pipefail

CONFIG_DIR="${MEMORIES_CONFIG_DIR:-$HOME/.config/recording}"
CONFIG_TOML="$CONFIG_DIR/config.toml"
SECRETS_ENV="$CONFIG_DIR/secrets.env"
LOG_FILE="/tmp/episodic/smb-mount.log"

mkdir -p "$(dirname "$LOG_FILE")"
# ログには user 名や内部 IP が含まれ得るため、所有者のみ読み書き可に絞る。
[[ -e "$LOG_FILE" ]] || : > "$LOG_FILE"
chmod 600 "$LOG_FILE" 2>/dev/null || true

# SMB URL から user@ 部分を伏せ字化する（ログ用）。
mask_smb_url() {
    # smb://user@host/share -> smb://***@host/share
    # smb://host/share      -> 変更なし
    sed -E 's#^(smb://)[^@/]+@#\1***@#' <<<"$1"
}

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

# config.toml から指定キーの値を取得（クォート除去・行末コメント除去・前後空白除去）。
# 返り値: 値（無ければ空文字）
toml_get() {
    local key="$1"
    local file="$2"
    [[ -f "$file" ]] || return 0
    awk -v k="$key" '
        /^[[:space:]]*#/ { next }
        $0 ~ "^[[:space:]]*" k "[[:space:]]*=" {
            sub(/^[^=]*=[[:space:]]*/, "", $0)
            sub(/[[:space:]]*#.*$/, "", $0)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
            gsub(/^"|"$/, "", $0)
            print
            exit
        }
    ' "$file"
}

# secrets.env を読み込む（0600 でない場合は警告して読み込みを拒否）。
if [[ -f "$SECRETS_ENV" ]]; then
    perm=$(stat -f '%Lp' "$SECRETS_ENV" 2>/dev/null || stat -c '%a' "$SECRETS_ENV" 2>/dev/null || echo "")
    if [[ "$perm" != "600" ]]; then
        log "warn: $SECRETS_ENV permissions are $perm (expected 600). Skipping load to avoid leaking secrets."
    else
        # shellcheck disable=SC1090
        set -a
        source "$SECRETS_ENV"
        set +a
    fi
fi

MOUNT_POINT="${MEMORIES_DIR:-$(toml_get memories_dir "$CONFIG_TOML")}"
MOUNT_POINT="${MOUNT_POINT:-/Volumes/memory}"

# 共有 URL（//[user@]host/share）を解決する。
SHARE_BASE="${MEMORIES_SMB_SHARE:-$(toml_get smb_share "$CONFIG_TOML")}"
SHARE_BASE="${SHARE_BASE:-//user@server.local/share}"  # プレースホルダ。設定漏れに気付かせる目的。

# user 名は secrets.env / 環境変数からのみ受け取り、未指定なら user@ を付けない（キーチェーン解決に任せる）。
SMB_USER="${MEMORIES_SMB_USER:-}"

# SHARE_BASE 内に user@ が含まれていなければ SMB_USER を差し込む。
if [[ -n "$SMB_USER" && "$SHARE_BASE" != *"@"* ]]; then
    SHARE="//${SMB_USER}@${SHARE_BASE#//}"
else
    SHARE="$SHARE_BASE"
fi

# ping 用ホスト名を SHARE から抽出（//[user@]host/share -> host）。
# 環境変数 MEMORIES_SMB_PING_HOST が指定されていればそれを優先し、次点で config.toml の smb_ping_host を見る。
PING_HOST="${MEMORIES_SMB_PING_HOST:-$(toml_get smb_ping_host "$CONFIG_TOML")}"
if [[ -z "$PING_HOST" ]]; then
    _share_no_proto="${SHARE#//}"
    _share_no_user="${_share_no_proto##*@}"
    PING_HOST="${_share_no_user%%/*}"
fi

# macOS 以外、または必要コマンド不在時はスキップ。
if [[ "$(uname -s)" != "Darwin" ]]; then
    log "skip: non-macOS platform ($(uname -s)); mount_smbfs is mac-only"
    exit 0
fi
if [[ ! -x /sbin/mount ]] || [[ ! -x /sbin/ping ]] || [[ ! -x /usr/bin/osascript ]]; then
    log "skip: required macOS commands not found (/sbin/mount, /sbin/ping, /usr/bin/osascript)"
    exit 0
fi

# 既にマウント済みなら何もしない
if /sbin/mount | grep -q " on $MOUNT_POINT "; then
    log "already mounted: $MOUNT_POINT"
    exit 0
fi

# サーバ到達確認（5秒タイムアウト）
if ! /sbin/ping -c 1 -t 5 "$PING_HOST" >/dev/null 2>&1; then
    log "host unreachable: $PING_HOST"
    exit 1
fi

# AppleScript の "mount volume" を使う（Finder 経由マウントと同等）。
# 利点: マウントポイントを Finder が自動作成し、unmount 時にも自動削除されるため
#       /Volumes/<name> を事前 mkdir する必要がない（root 権限不要）。
# 認証はキーチェーンから自動解決され、未保存時のみ GUI プロンプトが出る。
#
# セキュリティ: SMB_URL 内に AppleScript メタ文字（"）が含まれていても、
# argv 経由（item 1 of argv）で受け取ることで AppleScript 構文に解釈されない。
# osascript -e 文字列に変数を直接埋め込むとインジェクション脆弱性になるため避ける。
SMB_URL="smb://${SHARE#//}"
SMB_URL_MASKED="$(mask_smb_url "$SMB_URL")"
if /usr/bin/osascript \
        -e 'on run argv' \
        -e 'mount volume (item 1 of argv)' \
        -e 'end run' \
        -- "$SMB_URL" >> "$LOG_FILE" 2>&1; then
    log "mounted: $SMB_URL_MASKED -> $MOUNT_POINT"
    exit 0
else
    rc=$?
    log "mount failed: rc=$rc url=$SMB_URL_MASKED"
    exit 2
fi
