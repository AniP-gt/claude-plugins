#!/usr/bin/env bash
# UserPromptSubmit hook: ユーザー入力時に pending debounce をキャンセルする。
# stdin の JSON ペイロードを Python hook へパススルーする。
set -euo pipefail

CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
exec "${CLAUDE_PLUGIN_ROOT}/scripts/session/hook.py"
