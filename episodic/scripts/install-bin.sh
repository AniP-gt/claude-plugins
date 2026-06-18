#!/usr/bin/env bash
# Install episodic hook runtime under $HOME/.config/episodic.
# Codex / Claude Code 双方の Stop / SessionStart / UserPromptSubmit hook が、ここから動く。
#
# プラグインソースは plugin root 直下に bin/ / lib/ / session/ / recording/ / wiki/ / scripts/ /
# pyproject.toml / uv.lock を持つ（codex-hook-runtime と同じレイアウト）。
# 本スクリプトはそのツリーを ~/.config/episodic/codex-hook-runtime/ にミラーコピーする。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_ROOT="${EPISODIC_CONFIG_ROOT:-$HOME/.config/episodic}"
RUNTIME_ROOT="$CONFIG_ROOT/codex-hook-runtime"

install_file() {
    local src="$1" dst="$2" mode="$3"
    install -m "$mode" "$src" "$dst"
}

# install_tree <src_dir> <dst_dir> <file_mode_for_executables>
# .sh / .py を mode (755 推奨)、それ以外を 644 で配置する。
# サブディレクトリ構造を維持する。
install_tree() {
    local src_root="$1" dst_root="$2" exec_mode="$3"
    [[ -d "$src_root" ]] || { printf 'install_tree: source not found: %s\n' "$src_root" >&2; return 1; }
    local src dst rel mode
    while IFS= read -r -d '' src; do
        rel="${src#${src_root}/}"
        dst="${dst_root}/${rel}"
        mkdir -p "$(dirname "$dst")"
        chmod 700 "$(dirname "$dst")" 2>/dev/null || true
        case "$src" in
            *.sh|*.py) mode="$exec_mode" ;;
            *)         mode="644" ;;
        esac
        install_file "$src" "$dst" "$mode"
    done < <(find "$src_root" \
        \( -type d \( -name __pycache__ -o -name .venv \) -prune \) -o \
        \( -type f -not -name '.*' -not -name '*.pyc' -print0 \))
}

mkdir -p "$RUNTIME_ROOT"
chmod 700 "$CONFIG_ROOT" "$RUNTIME_ROOT" 2>/dev/null || true

# 旧レイアウトの残骸が混在しないよう、本スクリプトが所有するディレクトリを一度クリアする。
# 削除対象は固定（bin/lib/session/recording/wiki/scripts/templates）。ユーザーの個別ファイルが
# RUNTIME_ROOT 直下にあっても影響しない設計。
for sub in bin lib session recording wiki scripts templates; do
    rm -rf "$RUNTIME_ROOT/$sub"
done

# 各 runtime ディレクトリをツリーごとミラーコピー。
install_tree "$PLUGIN_ROOT/bin"       "$RUNTIME_ROOT/bin"       755
install_tree "$PLUGIN_ROOT/lib"       "$RUNTIME_ROOT/lib"       755
install_tree "$PLUGIN_ROOT/session"   "$RUNTIME_ROOT/session"   755
install_tree "$PLUGIN_ROOT/recording" "$RUNTIME_ROOT/recording" 755
install_tree "$PLUGIN_ROOT/wiki"      "$RUNTIME_ROOT/wiki"      755
install_tree "$PLUGIN_ROOT/scripts"   "$RUNTIME_ROOT/scripts"   755

# uv / Python venv 定義（recording/main_episodic.py / scripts/search 実行用）。
install_file "$PLUGIN_ROOT/pyproject.toml" "$RUNTIME_ROOT/pyproject.toml" 644
install_file "$PLUGIN_ROOT/uv.lock"        "$RUNTIME_ROOT/uv.lock"        644

# main_episodic.py の auto-provision が参照するテンプレ。
mkdir -p "$RUNTIME_ROOT/templates"
chmod 700 "$RUNTIME_ROOT/templates" 2>/dev/null || true
install_file "$PLUGIN_ROOT/templates/cocoindex.toml.example" \
             "$RUNTIME_ROOT/templates/cocoindex.toml.example" 644

# README は install 時にインライン生成（plugin source 側に runtime 専用の README は持たない）。
cat > "$RUNTIME_ROOT/README.md" <<'README'
# Codex Hook Runtime

`episodic/scripts/install-bin.sh` が plugin source ツリーをここへミラーコピーしています。
Codex / Claude Code の hook は plugin cache の場所に依存しないよう、展開後の
`bin/session_start.py` / `bin/session_stop.py` / `bin/session_user_prompt_submit.py`
を呼びます。

ディレクトリ構成は plugin source と同一です:

```
bin/         エントリラッパー（session_{start,stop,user_prompt_submit}.py など）
lib/         共通ヘルパー（config / cocoindex_trigger / log_rotate ...）
session/     Stop hook 本体（hook.py + runner.py + retry queue ...）
recording/   cocoindex flow（main_episodic.py）と web/minutes 補助
wiki/        wiki ingest pipeline（enqueue / kick_runner / wiki_runner）
scripts/     setup_db / search などの補助 CLI
templates/   main_episodic.py が参照するテンプレ（cocoindex.toml.example）
pyproject.toml / uv.lock  episodic 専用 Python 環境の定義
```

`uv run` の venv は既定で `~/.cache/episodic/venv` に作成します。
README
chmod 644 "$RUNTIME_ROOT/README.md" 2>/dev/null || true

printf 'installed episodic codex hook runtime: %s\n' "$RUNTIME_ROOT"
