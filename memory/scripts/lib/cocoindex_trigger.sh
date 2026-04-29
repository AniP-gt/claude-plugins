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
    # memories 専用エントリポイント（main_memory.py）を経由し、frontmatter prepend 込みで
    # embedding を生成する。プラグイン本体（汎用 main.py）は使わない。
    # cocoindex 1.0 CLI 形式（cocoindex update -f main_memory.py:<AppName>）で起動。
    #
    # ドメイン固有設定（embedding model/dimension, chunk size, exclude）は
    # ~/.config/cocoindex/config.toml の [memory] セクションで管理する。
    local memories_dir="${1:-${MEMORIES_DIR:-/Volumes/memory}}"
    local recording_scripts="${PLUGIN_ROOT}/scripts/recording"
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

    # cocoindex プラグインキャッシュは plugin update ごとにバージョンが変わるため動的解決する。
    local plugin_scripts
    plugin_scripts="$(python3 -c "
import sys
sys.path.insert(0, '${PLUGIN_ROOT}/scripts')
from lib.cocoindex_path import resolve_cocoindex_scripts
p = resolve_cocoindex_scripts()
print(p if p else '', end='')
" 2>/dev/null)"

    if [[ ! -f "$recording_scripts/main_memory.py" ]]; then
        _ct_log "cocoindex update skipped: main_memory.py not found ($recording_scripts/main_memory.py)"
        return
    fi
    if [[ -z "$plugin_scripts" || ! -d "$plugin_scripts/.venv" ]]; then
        _ct_log "cocoindex update skipped: cocoindex plugin venv not found (resolved=$plugin_scripts)"
        return
    fi
    if ! command -v uv >/dev/null 2>&1; then
        _ct_log "cocoindex update skipped: uv not found in PATH"
        return
    fi

    # MEMORIES_DIR=`/Volumes/memory` の場合 INDEX_NAME=memory、AppName と table 名は
    # main_memory.py が hostname プレフィックス付きで自動計算する。
    local index_name
    index_name="$(basename "$memories_dir")"
    local host_prefix
    host_prefix="$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')"
    local app_name="CodeIndex_${host_prefix}_${index_name}"

    _ct_log "cocoindex update scheduled: $memories_dir (app=$app_name, settings=config.toml [memory])"
    # main_memory.py は cocoindex プラグインの venv（uv 管理）を借りて実行する。
    (
        cd "$plugin_scripts" \
        && SOURCE_PATH="$memories_dir" \
            INDEX_NAME="$index_name" \
            PATTERNS="**/*.md" \
            nohup uv run cocoindex update -f "${recording_scripts}/main_memory.py:${app_name}" \
            >> "$cocoindex_log" 2>&1 &
    ) >/dev/null 2>&1 || true
}
