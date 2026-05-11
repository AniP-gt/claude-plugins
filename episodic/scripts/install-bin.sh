#!/usr/bin/env bash
# Install episodic hook runtime under $HOME/.config/episodic.
# Codex / Claude Code 双方の Stop / SessionStart / UserPromptSubmit hook が、ここから動く。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE_ROOT="$(cd "$SCRIPT_DIR/../templates/codex-hook-runtime" && pwd)"
CONFIG_ROOT="${EPISODIC_CONFIG_ROOT:-$HOME/.config/episodic}"
RUNTIME_ROOT="$CONFIG_ROOT/codex-hook-runtime"
BIN_DIR="$RUNTIME_ROOT/bin"
LIB_DIR="$RUNTIME_ROOT/lib"
WIKI_DIR="$RUNTIME_ROOT/wiki"
SESSION_DIR="$RUNTIME_ROOT/session"
SESSION_HOOK_DIR="$SESSION_DIR/hook"
RECORDING_DIR="$RUNTIME_ROOT/recording"
RECORDING_MINUTES_DIR="$RECORDING_DIR/minutes"
RECORDING_WEB_DIR="$RECORDING_DIR/web"

install_file() {
    local src="$1" dst="$2" mode="$3"
    install -m "$mode" "$src" "$dst"
}

mkdir -p \
    "$BIN_DIR" "$LIB_DIR" "$WIKI_DIR" \
    "$SESSION_DIR" "$SESSION_HOOK_DIR" \
    "$RECORDING_DIR" "$RECORDING_MINUTES_DIR" "$RECORDING_WEB_DIR"
chmod 700 \
    "$CONFIG_ROOT" "$RUNTIME_ROOT" \
    "$BIN_DIR" "$LIB_DIR" "$WIKI_DIR" \
    "$SESSION_DIR" "$SESSION_HOOK_DIR" \
    "$RECORDING_DIR" "$RECORDING_MINUTES_DIR" "$RECORDING_WEB_DIR" 2>/dev/null || true

install_file "$TEMPLATE_ROOT/README.md" "$RUNTIME_ROOT/README.md" 644

# bin/ - SessionStart / Stop / UserPromptSubmit hook の entry wrapper。
install_file "$TEMPLATE_ROOT/bin/session-start.sh"               "$BIN_DIR/session-start.sh" 755
install_file "$TEMPLATE_ROOT/bin/session-stop.sh"                "$BIN_DIR/session-stop.sh" 755
install_file "$TEMPLATE_ROOT/bin/session-user-prompt-submit.sh"  "$BIN_DIR/session-user-prompt-submit.sh" 755
install_file "$TEMPLATE_ROOT/bin/mount-memory-share.sh"          "$BIN_DIR/mount-memory-share.sh" 755
install_file "$TEMPLATE_ROOT/bin/sync-pending.sh"                "$BIN_DIR/sync-pending.sh" 755

# lib/ - 共通 Python / Bash ヘルパー。
for src in "$TEMPLATE_ROOT"/lib/*; do
    [[ -f "$src" ]] || continue
    case "$src" in
        *.sh) install_file "$src" "$LIB_DIR/$(basename "$src")" 755 ;;
        *) install_file "$src" "$LIB_DIR/$(basename "$src")" 644 ;;
    esac
done

# wiki/ - wiki 統合パイプライン（kick-runner / wiki-runner / enqueue / codex instruction）。
for src in "$TEMPLATE_ROOT"/wiki/enqueue.py \
           "$TEMPLATE_ROOT"/wiki/kick-runner.sh \
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

# session/ - Stop hook 本体（Python）と codex runner / retry queue / format adapter。
install_file "$TEMPLATE_ROOT/session/hook.py"               "$SESSION_DIR/hook.py" 755
install_file "$TEMPLATE_ROOT/session/runner.sh"             "$SESSION_DIR/runner.sh" 755
install_file "$TEMPLATE_ROOT/session/retry-pending.sh"      "$SESSION_DIR/retry-pending.sh" 755
install_file "$TEMPLATE_ROOT/session/retry_queue.py"        "$SESSION_DIR/retry_queue.py" 644
install_file "$TEMPLATE_ROOT/session/jsonl-to-markdown.py"  "$SESSION_DIR/jsonl-to-markdown.py" 755
install_file "$TEMPLATE_ROOT/session/session-extract.py"    "$SESSION_DIR/session-extract.py" 755
install_file "$TEMPLATE_ROOT/session/hook/claude.py"        "$SESSION_HOOK_DIR/claude.py" 644
install_file "$TEMPLATE_ROOT/session/hook/codex.py"         "$SESSION_HOOK_DIR/codex.py" 644

# recording/ - cocoindex flow（main_episodic）と minutes / web の補助スクリプト。
install_file "$TEMPLATE_ROOT/recording/main_episodic.py"    "$RECORDING_DIR/main_episodic.py" 755
install_file "$TEMPLATE_ROOT/recording/minutes/save.sh"     "$RECORDING_MINUTES_DIR/save.sh" 755
install_file "$TEMPLATE_ROOT/recording/web/fetch-jina.sh"   "$RECORDING_WEB_DIR/fetch-jina.sh" 755

# uv / Python venv 定義（recording/main_episodic.py 実行用）。
install_file "$TEMPLATE_ROOT/pyproject.toml" "$RUNTIME_ROOT/pyproject.toml" 644
install_file "$TEMPLATE_ROOT/uv.lock"        "$RUNTIME_ROOT/uv.lock" 644

printf 'installed episodic codex hook runtime: %s\n' "$RUNTIME_ROOT"
