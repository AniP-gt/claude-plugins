#!/usr/bin/env bash
# memory プラグイン共通: cocoindex update を非同期キックする。
#
# このファイルは source して使う。呼び出し元で以下を事前に設定しておくこと:
#   PLUGIN_ROOT      memory プラグインのルート（${CLAUDE_PLUGIN_ROOT} 相当）
#   MEMORIES_DIR     memories ルート（既定 /Volumes/memory）
#   LOG_DIR_LOCAL    ローカルログ出力ディレクトリ（例 /tmp/memories）
#
# log() 関数が定義されていればそれを使い、無ければ printf でフォールバックする。
#
# Usage:
#   source "${PLUGIN_ROOT}/scripts/lib/cocoindex_trigger.sh"
#   trigger_cocoindex_update                # MEMORIES_DIR を使う
#   trigger_cocoindex_update /custom/path   # 引数で上書き

trigger_cocoindex_update() {
    # 新規/更新された raw / wiki ファイルを cocoindex に反映（best effort / 非同期）。
    # memory プラグイン専用エントリポイント（main_memory.py）を memory 自身の venv で実行する。
    # cocoindex 1.0 CLI 形式（cocoindex update -f main_memory.py:<AppName>）で起動。
    #
    # ドメイン固有設定（embedding model/dimension, chunk size, exclude）は
    # ~/.config/memory/cocoindex.toml の [embedding]/[chunk]/[index] セクションで管理する。
    local memories_dir="${1:-${MEMORIES_DIR:-/Volumes/memory}}"
    local memory_scripts="${PLUGIN_ROOT}/scripts"
    local recording_scripts="${memory_scripts}/recording"
    local log_dir="${LOG_DIR_LOCAL:-/tmp/memories}"
    mkdir -p "$log_dir" 2>/dev/null || true
    local cocoindex_log="$log_dir/cocoindex-memories-update.log"

    _ct_log() {
        if declare -F log >/dev/null 2>&1; then
            log "$1"
        else
            printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$1" >> "$cocoindex_log"
        fi
    }

    if [[ ! -f "$recording_scripts/main_memory.py" ]]; then
        _ct_log "cocoindex update skipped: main_memory.py not found ($recording_scripts/main_memory.py)"
        return
    fi
    if [[ ! -f "$memory_scripts/pyproject.toml" ]]; then
        _ct_log "cocoindex update skipped: memory pyproject not found ($memory_scripts/pyproject.toml)"
        return
    fi
    if ! command -v uv >/dev/null 2>&1; then
        _ct_log "cocoindex update skipped: uv not found in PATH"
        return
    fi

    # MEMORIES_DIR=`/Volumes/memory` の場合 INDEX_NAME=memory、AppName と table 名は
    # main_memory.py が hostname プレフィックス付きで自動計算する（MemoryIndex_<host>_<name>）。
    local index_name
    index_name="$(basename "$memories_dir")"
    local host_prefix
    host_prefix="$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')"
    local app_name="MemoryIndex_${host_prefix}_${index_name}"

    _ct_log "cocoindex update scheduled: $memories_dir (app=$app_name, settings=memory/cocoindex.toml [memory])"
    # main_memory.py は memory プラグイン専用 venv（uv 管理）で実行する。
    (
        cd "$memory_scripts" \
        && SOURCE_PATH="$memories_dir" \
            INDEX_NAME="$index_name" \
            PATTERNS="**/*.md" \
            nohup uv run cocoindex update -f "${recording_scripts}/main_memory.py:${app_name}" \
            >> "$cocoindex_log" 2>&1 &
    ) >/dev/null 2>&1 || true
}
