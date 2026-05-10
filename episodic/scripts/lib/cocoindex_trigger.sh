#!/usr/bin/env bash
# episodic プラグイン共通: cocoindex update を非同期キックする。
#
# このファイルは source して使う。呼び出し元で以下を事前に設定しておくこと:
#   PLUGIN_ROOT      episodic プラグインのルート（${CLAUDE_PLUGIN_ROOT} 相当）
#   MEMORIES_DIR     memories ルート（既定 /Volumes/memory）
#   LOG_DIR_LOCAL    ローカルログ出力ディレクトリ（例 /tmp/episodic）
#
# log() 関数が定義されていればそれを使い、無ければ printf でフォールバックする。
#
# Usage:
#   source "${PLUGIN_ROOT}/scripts/lib/cocoindex_trigger.sh"
#   trigger_cocoindex_update                # MEMORIES_DIR を使う
#   trigger_cocoindex_update /custom/path   # 引数で上書き

trigger_cocoindex_update() {
    # 新規/更新された raw / wiki ファイルを cocoindex に反映（best effort / 非同期）。
    # episodic プラグイン専用エントリポイント（main_episodic.py）を episodic 自身の venv で実行する。
    # cocoindex 1.0 CLI 形式（cocoindex update -f main_episodic.py:<AppName>）で起動。
    #
    # ドメイン固有設定（embedding model/dimension, chunk size, exclude）は
    # ~/.config/episodic/cocoindex.toml の [embedding]/[chunk]/[index] セクションで管理する。
    local memories_dir="${1:-${MEMORIES_DIR:-/Volumes/memory}}"
    local episodic_scripts="${PLUGIN_ROOT}/scripts"
    local recording_scripts="${episodic_scripts}/recording"
    local log_dir="${LOG_DIR_LOCAL:-/tmp/episodic}"
    mkdir -p "$log_dir" 2>/dev/null || true
    local cocoindex_log="$log_dir/cocoindex-update.log"

    _ct_log() {
        if declare -F log >/dev/null 2>&1; then
            log "$1"
        else
            printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$1" >> "$cocoindex_log"
        fi
    }

    if [[ ! -f "$recording_scripts/main_episodic.py" ]]; then
        _ct_log "cocoindex update skipped: main_episodic.py not found ($recording_scripts/main_episodic.py)"
        return
    fi
    if [[ ! -f "$episodic_scripts/pyproject.toml" ]]; then
        _ct_log "cocoindex update skipped: episodic pyproject not found ($episodic_scripts/pyproject.toml)"
        return
    fi
    if ! command -v uv >/dev/null 2>&1; then
        _ct_log "cocoindex update skipped: uv not found in PATH"
        return
    fi

    # INDEX_NAME は固定 "episodic"。AppName と table 名は main_episodic.py が
    # hostname プレフィックス付きで自動計算する（EpisodicIndex_<host>_episodic / episodicindex_<host>_episodic__chunks）。
    local index_name="episodic"
    local host_prefix
    host_prefix="$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')"
    local app_name="EpisodicIndex_${host_prefix}_${index_name}"

    _ct_log "cocoindex update scheduled: $memories_dir (app=$app_name, settings=~/.config/episodic/cocoindex.toml)"
    # main_episodic.py は episodic プラグイン専用 venv（uv 管理）で実行する。
    (
        cd "$episodic_scripts" \
        && SOURCE_PATH="$memories_dir" \
            INDEX_NAME="$index_name" \
            PATTERNS="**/*.md" \
            nohup uv run cocoindex update -f "${recording_scripts}/main_episodic.py:${app_name}" \
            >> "$cocoindex_log" 2>&1 &
    ) >/dev/null 2>&1 || true
}
