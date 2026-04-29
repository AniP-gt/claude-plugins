#!/usr/bin/env bash
# SessionEnd: 会話履歴を Codex で要約し Raw を生成する。
# stdin の JSON ペイロードを Python hook へパススルーする。
set -u
exec "${CLAUDE_PLUGIN_ROOT}/scripts/record/hook.py"
