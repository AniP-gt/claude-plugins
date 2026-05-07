#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TMP_DIR="$PROJECT_DIR/tmp"

if [[ -d "$TMP_DIR" ]]; then
  find "$TMP_DIR" -mindepth 1 ! -name '.keep' -delete
fi

exit 0
