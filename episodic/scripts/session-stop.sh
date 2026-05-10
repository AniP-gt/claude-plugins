#!/usr/bin/env bash
# Stop hook: Claude Code の応答ごとに発火し、debounce 経由で Codex 要約を起動する。
# stdin の JSON ペイロードを Python hook へパススルーする。
# Claude Code 経由起動では CLAUDE_PLUGIN_ROOT が渡されるが、手動実行を許すために
# 未定義時はスクリプト自身の位置からプラグインルートを逆算する。
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SELF_DIR/.." && pwd)}"

exec "${CLAUDE_PLUGIN_ROOT}/scripts/session/hook.py"
