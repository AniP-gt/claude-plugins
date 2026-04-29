#!/usr/bin/env bash
# SessionStart: マウント復帰時に staging を正規パスへ移送する。
# 失敗してもセッション開始を妨げない（常に exit 0）。
set -u
exec "${CLAUDE_PLUGIN_ROOT}/scripts/record/sync-pending.sh"
