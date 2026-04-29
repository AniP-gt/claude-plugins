#!/usr/bin/env bash
# SessionStart: マウント復帰時に staging を正規パスへ移送する。
# 失敗してもセッション開始を妨げない（常に exit 0）。
# Claude Code 経由起動では CLAUDE_PLUGIN_ROOT が渡されるが、手動実行を許すために
# 未定義時はスクリプト自身の位置からプラグインルートを逆算する。
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SELF_DIR/.." && pwd)}"
exec "${CLAUDE_PLUGIN_ROOT}/scripts/record/sync-pending.sh"
