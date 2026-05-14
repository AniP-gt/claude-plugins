#!/usr/bin/env bash
# episodic プラグイン共通: cocoindex update を非同期キックする。
#
# このファイルは source して使う。呼び出し元で以下を事前に設定しておくこと:
#   PLUGIN_ROOT      episodic プラグインのルート（${CLAUDE_PLUGIN_ROOT} 相当）。
#                    pyproject.toml と recording/main_episodic.py が直下に存在する場所。
#                    source repo / codex-hook-runtime いずれの配置でも同じ。
#   MEMORIES_DIR     memories ルート（既定 /Volumes/memory）
#   DIARY_DIR        kind: diary 専用ローカルルート（既定 ~/.local/share/episodic/diary）
#   LOG_DIR_LOCAL    ローカルログ出力ディレクトリ（例 ~/.local/state/episodic/logs）
#
# log() 関数が定義されていればそれを使い、無ければ printf でフォールバックする。
#
# Usage:
#   source "${PLUGIN_ROOT}/lib/cocoindex_trigger.sh"
#   trigger_cocoindex_update                       # MEMORIES_DIR / DIARY_DIR を使う
#   trigger_cocoindex_update /custom/path           # memories_dir を引数で上書き
#   trigger_cocoindex_update /custom/path /diary    # diary_dir も引数で上書き

trigger_cocoindex_update() {
    # 新規/更新された raw / wiki ファイルを cocoindex に反映（best effort / 非同期）。
    # episodic プラグイン専用エントリポイント（main_episodic.py）を episodic 自身の venv で実行する。
    # cocoindex 1.0 CLI 形式（cocoindex update -f main_episodic.py:<AppName>）で起動。
    #
    # ドメイン固有設定（embedding model/dimension, chunk size, exclude）は
    # ~/.config/episodic/cocoindex.toml の [embedding]/[chunk]/[index] セクションで管理する。
    local memories_dir="${1:-${MEMORIES_DIR:-/Volumes/memory}}"
    # kind: diary 専用ローカルルート。第2引数 > DIARY_DIR env > 既定値。
    # main_episodic.py が DIARY_SOURCE_PATH として受け取り、2 つ目のソースとして走査する。
    local diary_dir="${2:-${DIARY_DIR:-$HOME/.local/share/episodic/diary}}"
    local app_dir="${PLUGIN_ROOT}"
    local recording_dir="${app_dir}/recording"
    local log_dir="${LOG_DIR_LOCAL:-$HOME/.local/state/episodic/logs}"
    mkdir -p "$log_dir" 2>/dev/null || true
    chmod 700 "$log_dir" 2>/dev/null || true
    local cocoindex_log="$log_dir/cocoindex-update.log"

    _ct_log() {
        if declare -F log >/dev/null 2>&1; then
            log "$1"
        else
            printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$1" >> "$cocoindex_log"
        fi
    }

    if [[ ! -f "$recording_dir/main_episodic.py" ]]; then
        _ct_log "cocoindex update skipped: main_episodic.py not found ($recording_dir/main_episodic.py)"
        return
    fi
    if [[ ! -f "$app_dir/pyproject.toml" ]]; then
        _ct_log "cocoindex update skipped: episodic pyproject not found ($app_dir/pyproject.toml)"
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

    _ct_log "cocoindex update scheduled: $memories_dir (diary=$diary_dir, app=$app_name, settings=~/.config/episodic/cocoindex.toml)"
    # main_episodic.py は uv 管理の episodic 専用 Python 環境で実行する。
    # venv は config ではなく cache に置き、runtime 配置をコード・設定に限定する。
    local uv_project_environment="${UV_PROJECT_ENVIRONMENT:-$HOME/.cache/episodic/venv}"
    mkdir -p "$(dirname "$uv_project_environment")" 2>/dev/null || true
    # サブシェル内で update の終了コードを受け取り、完了通知（macOS osascript）を出す。
    (
        cd "$app_dir" || exit 1
        SOURCE_PATH="$memories_dir" \
            DIARY_SOURCE_PATH="$diary_dir" \
            INDEX_NAME="$index_name" \
            PATTERNS="**/*.md" \
            UV_PROJECT_ENVIRONMENT="$uv_project_environment" \
            nohup uv run cocoindex update -f "${recording_dir}/main_episodic.py:${app_name}" \
            >> "$cocoindex_log" 2>&1
        rc=$?
        if [[ $rc -eq 0 ]]; then
            _ct_log "cocoindex update finished: rc=0 app=$app_name"
            _ct_notify "完了" "cocoindex update 成功 (app=${app_name})" "Glass"
        else
            _ct_log "cocoindex update failed: rc=$rc app=$app_name"
            _ct_notify "失敗" "cocoindex update 失敗 (rc=${rc})。ログ: $cocoindex_log" "Basso"
        fi
    ) >/dev/null 2>&1 &
    disown 2>/dev/null || true
}

# macOS 通知ヘルパー。osascript 不在環境（Linux 等）ではログだけ残してスキップする。
# 引数: _ct_notify <subtitle> <message> [sound]
# バックグラウンド実行で OK ボタン待ちブロッキングが起きないよう、
# display alert / dialog は使わず display notification（バナー、自動消失）に統一する。
_ct_notify() {
    local subtitle="$1" msg="$2" sound="${3:-}"
    if ! command -v osascript >/dev/null 2>&1; then
        return
    fi
    if [[ -n "$sound" ]]; then
        osascript \
            -e 'on run argv' \
            -e 'display notification (item 1 of argv) with title "Episodic Cocoindex" subtitle (item 2 of argv) sound name (item 3 of argv)' \
            -e 'end run' \
            "$msg" "$subtitle" "$sound" >/dev/null 2>&1
    else
        osascript \
            -e 'on run argv' \
            -e 'display notification (item 1 of argv) with title "Episodic Cocoindex" subtitle (item 2 of argv)' \
            -e 'end run' \
            "$msg" "$subtitle" >/dev/null 2>&1
    fi
}
