#!/usr/bin/env bash
# Install Codex/standalone hook runtime under ~/.config/episodic.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_ROOT="$(cd "$SCRIPT_DIR/../templates/codex-hook-runtime" && pwd)"
CONFIG_ROOT="${EPISODIC_CONFIG_ROOT:-$HOME/.config/episodic}"
RUNTIME_ROOT="$CONFIG_ROOT/codex-hook-runtime"
BIN_DIR="$RUNTIME_ROOT/bin"
LIB_DIR="$RUNTIME_ROOT/lib"
WIKI_DIR="$RUNTIME_ROOT/wiki"

install_file() {
    local src="$1" dst="$2" mode="$3"
    install -m "$mode" "$src" "$dst"
}

mkdir -p "$BIN_DIR" "$LIB_DIR" "$WIKI_DIR"
chmod 700 "$CONFIG_ROOT" "$RUNTIME_ROOT" "$BIN_DIR" "$LIB_DIR" "$WIKI_DIR" 2>/dev/null || true

install_file "$TEMPLATE_ROOT/bin/session-start.sh" "$BIN_DIR/session-start.sh" 755
install_file "$TEMPLATE_ROOT/bin/mount-memory-share.sh" "$BIN_DIR/mount-memory-share.sh" 755
install_file "$TEMPLATE_ROOT/bin/sync-pending.sh" "$BIN_DIR/sync-pending.sh" 755

for src in "$TEMPLATE_ROOT"/lib/*; do
    [[ -f "$src" ]] || continue
    case "$src" in
        *.sh) install_file "$src" "$LIB_DIR/$(basename "$src")" 755 ;;
        *) install_file "$src" "$LIB_DIR/$(basename "$src")" 644 ;;
    esac
done

for src in "$TEMPLATE_ROOT"/wiki/enqueue.py \
           "$TEMPLATE_ROOT"/wiki/wiki-runner.sh \
           "$TEMPLATE_ROOT"/wiki/codex-instruction.md \
           "$TEMPLATE_ROOT"/wiki/codex-instruction-web.md \
           "$TEMPLATE_ROOT"/wiki/codex-instruction-minutes.md; do
    [[ -f "$src" ]] || continue
    case "$src" in
        *.sh|*.py) install_file "$src" "$WIKI_DIR/$(basename "$src")" 755 ;;
        *) install_file "$src" "$WIKI_DIR/$(basename "$src")" 644 ;;
    esac
done

printf 'installed episodic codex hook runtime: %s\n' "$RUNTIME_ROOT"
