#!/usr/bin/env bash
# compass セマンティック検索の薄いラッパ。
# 使い方:
#   search.sh "<query>" [--top N] [--no-rerank]
# project-dir は CLAUDE_PROJECT_DIR > $PWD の順で自動解決される。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

cd "$SCRIPT_DIR"
exec uv run python search.py "$@" --project-dir "$PROJECT_DIR"
