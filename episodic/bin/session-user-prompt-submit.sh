#!/usr/bin/env bash
# UserPromptSubmit hook: ユーザー入力時に pending debounce をキャンセルする。
# stdin の JSON ペイロードを Python hook へパススルーする。
#
# 自分の位置（bin/）から ../session/hook.py を解決するため、CLAUDE_PLUGIN_ROOT の有無や
# 配置（source repo / codex-hook-runtime）に依存しない。
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SELF_DIR/.." && pwd)}"
export CLAUDE_PLUGIN_ROOT

exec "${SELF_DIR}/../session/hook.py"
