#!/bin/bash
# SMB 共有を memories マウントポイントへマウントする macOS 用ヘルパー。
# 設定の優先順位: 環境変数 > ~/.config/episodic/secrets.env > ~/.config/episodic/config.toml > プレースホルダ既定
#
# - 公開可能な設定（共有 URL / ping host）は config.toml に書く。
# - シークレット情報（user 名、将来的なパスワード等）は secrets.env に書き、chmod 600 を必須とする。
# - 環境変数（MEMORIES_SMB_SHARE / MEMORIES_SMB_USER / MEMORIES_SMB_PING_HOST）が設定されていれば最優先。
# - 認証は macOS キーチェーンから自動解決される（user 名のみ secrets.env で渡す）。
#
# 設計:
#   - mount_smbfs を直接呼ぶ。旧実装は AppleScript の "mount volume" を使っていたが、
#     これは目的マウントポイントに既存ディレクトリ＋中身があると衝突回避で
#     "-1" サフィックス付きパス（例: /Volumes/memory-1）へ黙ってずらす仕様で、
#     残骸ディレクトリが残ると気付かないうちに別パスにマウントされる事故が起きた。
#     mount_smbfs は事前に存在する空ディレクトリへそのままオーバーレイマウントするため、
#     マウントポイントが固定化される。
#   - マウントポイント（既定 /Volumes/memory）は事前に空ディレクトリとして永続化する前提:
#       sudo install -d -o "$(id -un)" -g staff -m 0755 /Volumes/memory
#     初回 sudo 1 度きりでセットアップが完結する（episodic-setup skill の 4-A を参照）。
#   - 保険として、マウント直前に「canary 無し & 非空」のスタブ状態を検出した場合は
#     abort して退避コマンドをログに案内する（自動退避は破壊的なので人間判断に委ねる）。
#
# macOS 以外では mount_smbfs / /sbin/mount / /sbin/ping が無いため、自動的にスキップする
# （ログだけ残して exit 0）。Linux/Windows で SMB を使いたい場合は config.toml の
# remount_script を環境固有のラッパー（mount.cifs / net use など）へ差し替えること。

set -uo pipefail

CONFIG_DIR="${MEMORIES_CONFIG_DIR:-$HOME/.config/episodic}"
CONFIG_TOML="$CONFIG_DIR/config.toml"
SECRETS_ENV="$CONFIG_DIR/secrets.env"
LOG_FILE="$HOME/.local/state/episodic/logs/smb-mount.log"

mkdir -p "$(dirname "$LOG_FILE")"
chmod 700 "$(dirname "$LOG_FILE")" 2>/dev/null || true
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
if [[ ! -x /sbin/mount ]] || [[ ! -x /sbin/ping ]] || [[ ! -x /sbin/mount_smbfs ]]; then
    log "skip: required macOS commands not found (/sbin/mount, /sbin/ping, /sbin/mount_smbfs)"
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

# マウントポイントの存在確認（事前に空ディレクトリとして作成しておく前提）。
# 未作成の場合は abort し、初回セットアップコマンドをログに案内する。
if [[ ! -d "$MOUNT_POINT" ]]; then
    log "abort: mount point does not exist: $MOUNT_POINT"
    log "  initial setup (one-time, requires sudo):"
    log "    sudo install -d -o \"\$(id -un)\" -g staff -m 0755 $MOUNT_POINT"
    exit 4
fi

# スタブ検出ガード（保険）: canary が無いのに中身がある状態は、
# 過去に SMB 未マウント時に何かが書き込んだ「ローカル残骸」である。
# 放置しても mount_smbfs 自体は成功するが、マウント解除後に残骸が再露出するため早期に止める。
if [[ ! -e "$MOUNT_POINT/.mount-canary" ]] \
   && [[ -n "$(/bin/ls -A "$MOUNT_POINT" 2>/dev/null)" ]]; then
    _stub_backup="$HOME/.local/share/episodic/legacy-stub-$(date +%Y%m%d-%H%M%S)"
    log "abort: stale local stub detected at $MOUNT_POINT (no canary, non-empty)"
    log "  retire the stub and recreate an empty mount point:"
    log "    sudo mv $MOUNT_POINT $_stub_backup \\"
    log "      && sudo install -d -o \"\$(id -un)\" -g staff -m 0755 $MOUNT_POINT"
    exit 5
fi

# mount_smbfs を直接呼ぶ。-N で対話プロンプトを抑制し、キーチェーンに保存された
# 資格情報のみで認証する。初回はユーザーが Finder か手動 mount_smbfs を一度走らせて
# 「キーチェーンに保存」を選んでおく必要がある（episodic-setup skill の 4-A 参照）。
#
# セキュリティ: SHARE は //[user@]host/share 形式の信頼済み設定値（config.toml / secrets.env / env 由来）。
# 外部入力ではないため、コマンド引数として渡しても injection リスクは無い。
SMB_URL="smb://${SHARE#//}"
SMB_URL_MASKED="$(mask_smb_url "$SMB_URL")"
# mount_smbfs の stderr は認証失敗時に user@host を含む URL をそのまま吐く実装のため、
# 直接ログへリダイレクトせず変数に受けてから user@ 部分をマスクしてログへ書く。
_mount_stderr="$(/sbin/mount_smbfs -N -o nobrowse,nodev,nosuid "//${SHARE#//}" "$MOUNT_POINT" 2>&1)"
_mount_rc=$?
if [[ -n "$_mount_stderr" ]]; then
    printf '%s\n' "$_mount_stderr" \
        | /usr/bin/sed -E 's#(//)[^@/[:space:]]+@#\1***@#g' \
        >> "$LOG_FILE"
fi
if [[ $_mount_rc -eq 0 ]]; then
    log "mounted: $SMB_URL_MASKED -> $MOUNT_POINT"
    exit 0
else
    log "mount failed: rc=$_mount_rc url=$SMB_URL_MASKED (check keychain credentials and server availability)"
    exit 2
fi
