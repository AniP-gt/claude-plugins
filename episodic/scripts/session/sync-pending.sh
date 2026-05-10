#!/usr/bin/env bash
# Backward-compatible wrapper. The stable entrypoint is ../sync-pending.sh.
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${SELF_DIR}/../sync-pending.sh" "$@"
