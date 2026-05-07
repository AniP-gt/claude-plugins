#!/usr/bin/env bash
# SessionEnd: 会話履歴を Codex で要約し Raw を生成する。
# stdin の JSON ペイロードを Python hook へパススルーする。
# Claude Code 経由起動では CLAUDE_PLUGIN_ROOT が渡されるが、手動実行を許すために
# 未定義時はスクリプト自身の位置からプラグインルートを逆算する。
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SELF_DIR/.." && pwd)}"
exec "${CLAUDE_PLUGIN_ROOT}/scripts/recording/hook.py"
