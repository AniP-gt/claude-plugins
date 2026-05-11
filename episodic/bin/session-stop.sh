#!/usr/bin/env bash
# Stop hook: Claude Code の応答ごとに発火し、debounce 経由で Codex 要約を起動する。
# stdin の JSON ペイロードを Python hook へパススルーする。
#
# 自分の位置（bin/）から ../session/hook.py を解決するため、CLAUDE_PLUGIN_ROOT の有無や
# 配置（source repo / codex-hook-runtime）に依存しない。
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$SELF_DIR/.." && pwd)}"
export CLAUDE_PLUGIN_ROOT

exec "${SELF_DIR}/../session/hook.py"
