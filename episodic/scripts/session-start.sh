#!/usr/bin/env bash
# SessionStart: SMB マウント試行 → 取り残された debounce セッションの finalize → staging 移送。
# 失敗してもセッション開始を妨げない（常に exit 0）。
#
# 旧設計では LaunchAgent (com.user.mount-memory) が起動時にマウントを担っていたが、
# プラグイン構成変更でパスが乖離したため、SessionStart で都度マウント試行する設計に統一する。
# mount-memory-share.sh は既マウント時は何もせず exit 0 のため、頻発呼び出しでも安全。
BIN_DIR="$(cd "$(dirname "$0")" && pwd)"

# logs ディレクトリを所有者専用で確保（後続の nohup redirect が確実に書ける状態にする）。
LOG_DIR_LOCAL="$HOME/.local/state/episodic/logs"
mkdir -p "$LOG_DIR_LOCAL"
chmod 700 "$LOG_DIR_LOCAL" 2>/dev/null || true

# マウント試行（失敗してもログだけ残して後続へ。sync-pending 側がマウント未確立を検知して skip する）
"${BIN_DIR}/mount-memory-share.sh" || true

# 旧パス（XDG_DATA_HOME 配下）に取り残された pending を新パス（XDG_STATE_HOME 配下）へ移行する。
# pending はログ・debounce 状態などの「状態データ」であり XDG 仕様上は state が正。
# 在庫の session_id ディレクトリは衝突しない前提（UUID 単位）。新側に同名があれば旧側を捨てる。
migrate_legacy_pending() {
    local legacy="$HOME/.local/share/episodic/pending"
    local current="$HOME/.local/state/episodic/pending"
    [[ -d "$legacy" ]] || return 0
    mkdir -p "$current"
    chmod 700 "$current" 2>/dev/null || true
    shopt -s nullglob
    local d name
    for d in "$legacy"/*/; do
        name=$(basename "$d")
        if [[ ! -e "$current/$name" ]]; then
            mv "$d" "$current/$name" 2>/dev/null || true
        fi
    done
    shopt -u nullglob
    rmdir "$legacy" 2>/dev/null || true
}

migrate_legacy_pending

# PC シャットダウン等で取り残された debounce 中セッションを救済する。
# pending/{session_id}/ 配下に未処理の codex.meta.json が残っていれば finalize を再 spawn する。
# ロック / debounce プロセスが生きている場合は処理中とみなしスキップ。
detect_pending_sessions() {
    local pending_root="$HOME/.local/state/episodic/pending"
    local hook_py="${BIN_DIR}/session/hook.py"
    [[ -d "$pending_root" ]] || return 0
    [[ -f "$hook_py" ]] || return 0

    local session_dir session_id lock_pid dpid meta report_path
    for session_dir in "$pending_root"/*/; do
        [[ -d "$session_dir" ]] || continue
        session_dir="${session_dir%/}"
        session_id=$(basename "$session_dir")
        # UUID 形式以外はスキップ（パストラバーサル防御）
        if [[ ! "$session_id" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
            continue
        fi

        # runner.sh が処理中ならスキップ
        if [[ -d "$session_dir/.lock" ]]; then
            lock_pid=$(cat "$session_dir/.lock/pid" 2>/dev/null || echo "")
            if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
                continue
            fi
        fi
        # debounce sleep が生きていればスキップ
        if [[ -f "$session_dir/.debounce.pid" ]]; then
            dpid=$(cat "$session_dir/.debounce.pid" 2>/dev/null || echo "")
            if [[ -n "$dpid" ]] && kill -0 "$dpid" 2>/dev/null; then
                continue
            fi
        fi

        # 最新の meta sidecar を取得
        meta=$(ls -t "$session_dir"/*.codex.meta.json 2>/dev/null | head -1)
        if [[ -z "$meta" || ! -f "$meta" ]]; then
            # 中身が無ければディレクトリ掃除
            rm -rf "$session_dir" 2>/dev/null || true
            continue
        fi

        # meta から report_path を抽出
        report_path=$(META_PATH="$meta" python3 - <<'PY' 2>/dev/null
import json, os, sys
try:
    with open(os.environ["META_PATH"], encoding="utf-8") as f:
        d = json.load(f) or {}
    print(d.get("report_path") or "")
except Exception:
    sys.exit(1)
PY
)
        if [[ -z "$report_path" ]]; then
            continue
        fi

        if [[ -f "$report_path" ]]; then
            # 既に生成済み → cleanup 漏れの掃除
            rm -rf "$session_dir" 2>/dev/null || true
        else
            # 未生成 → finalize を fire-and-forget で再起動
            ( nohup python3 "$hook_py" --finalize "$session_id" \
                >> "$HOME/.local/state/episodic/logs/session-hook.log" 2>&1 & ) >/dev/null 2>&1 || true
        fi
    done
}

detect_pending_sessions

exec "${BIN_DIR}/sync-pending.sh"
