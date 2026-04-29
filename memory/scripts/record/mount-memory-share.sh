#!/bin/bash
# SMB 共有を memories マウントポイントへマウントする macOS 用ヘルパー。
# キーチェーンに保存された資格情報を使い、未マウント時のみ実行する。
#
# 本スクリプトは memory プラグイン作者（hidetsugu-miya）の自宅サーバ向けサンプルである。
# 他環境では以下のいずれかで利用すること:
#   1. 環境変数で上書き（推奨）:
#        MEMORIES_DIR=/path/to/mountpoint
#        MEMORIES_SMB_SHARE="//user@host/share"
#        MEMORIES_SMB_PING_HOST=host         # 省略時は SHARE から自動抽出
#   2. config.toml の remount_script で自前のスクリプトに差し替える
#
# macOS 以外では mount_smbfs / /sbin/mount / /sbin/ping が無いため、自動的にスキップする
# （ログだけ残して exit 0）。Linux/Windows で SMB を使いたい場合は remount_script を
# 環境固有のラッパー（mount.cifs / net use など）へ差し替えること。

set -uo pipefail

MOUNT_POINT="${MEMORIES_DIR:-/Volumes/memory}"
# SHARE は環境ごとに必ず差し替えること。MEMORIES_SMB_SHARE 環境変数または
# config.toml で remount_script を自前のスクリプトに差し替える運用が前提。
# ここで指定しているプレースホルダは「未設定だと到達不能で fail する」ことで
# 設定漏れに気付かせる目的で置いている。
SHARE="${MEMORIES_SMB_SHARE:-//user@server.local/share}"
LOG_FILE="/tmp/memories/smb-mount.log"

# ping 用ホスト名を SHARE から抽出（//user@host/share -> host）。
# 環境変数 MEMORIES_SMB_PING_HOST が指定されていればそれを優先する。
if [[ -n "${MEMORIES_SMB_PING_HOST:-}" ]]; then
    PING_HOST="$MEMORIES_SMB_PING_HOST"
else
    _share_no_proto="${SHARE#//}"
    _share_no_user="${_share_no_proto##*@}"
    PING_HOST="${_share_no_user%%/*}"
fi

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

# macOS 以外、または必要コマンド不在時はスキップ。
if [[ "$(uname -s)" != "Darwin" ]]; then
    log "skip: non-macOS platform ($(uname -s)); mount_smbfs is mac-only"
    exit 0
fi
if [[ ! -x /sbin/mount_smbfs ]] || [[ ! -x /sbin/mount ]] || [[ ! -x /sbin/ping ]]; then
    log "skip: required macOS commands not found (/sbin/mount_smbfs, /sbin/mount, /sbin/ping)"
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

# マウントポイント作成
mkdir -p "$MOUNT_POINT" 2>/dev/null || true

# mount_smbfs 実行（資格情報はキーチェーンから取得される）
if /sbin/mount_smbfs "$SHARE" "$MOUNT_POINT" >> "$LOG_FILE" 2>&1; then
    log "mounted: $SHARE -> $MOUNT_POINT"
    exit 0
else
    rc=$?
    log "mount failed: rc=$rc"
    exit 2
fi
