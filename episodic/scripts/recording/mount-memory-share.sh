#!/usr/bin/env bash
# Backward-compatible wrapper. The stable entrypoint is ../mount-memory-share.sh.
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${SELF_DIR}/../mount-memory-share.sh" "$@"
