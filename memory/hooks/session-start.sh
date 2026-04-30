#!/usr/bin/env bash
# SessionStart: SMB 共有のマウントを試み、続いて staging を正規パスへ移送する。
# 失敗してもセッション開始を妨げない（常に exit 0）。
# Claude Code 経由起動では CLAUDE_PLUGIN_ROOT が渡されるが、手動実行を許すために
# 未定義時はスクリプト自身の位置からプラグインルートを逆算する。
#
# 旧設計では LaunchAgent (com.user.mount-memory) が起動時にマウントを担っていたが、
# プラグイン構成変更でパスが乖離したため、SessionStart で都度マウント試行する設計に統一する。
# mount-memory-share.sh は既マウント時は何もせず exit 0 のため、頻発呼び出しでも安全。
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SELF_DIR/.." && pwd)}"

# マウント試行（失敗してもログだけ残して後続へ。sync-pending 側がマウント未確立を検知して skip する）
"${CLAUDE_PLUGIN_ROOT}/scripts/recording/mount-memory-share.sh" || true

exec "${CLAUDE_PLUGIN_ROOT}/scripts/recording/sync-pending.sh"
