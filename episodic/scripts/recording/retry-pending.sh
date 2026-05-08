#!/usr/bin/env bash
# retry-pending: Codex セッション要約失敗のリトライキューを消化する。
#
# 起動条件:
#   - SessionStart hook（nohup でバックグラウンド起動）
#   - 手動: ${CLAUDE_PLUGIN_ROOT}/scripts/recording/retry-pending.sh
#
# 動作:
#   1. グローバル排他ロック（state/retry-pending.lock.d）を mkdir 方式で取得
#   2. retry_queue.py list で active エントリを取得
#   3. 各エントリ pre-scan:
#        a. 期待 report_path がすでに存在 → queue から除去（success-by-other-means）
#        b. transcript_path が消失 → queue から除去（dead_letter にもしない）
#        c. attempt_count が MAX 超過 → dead_letter へ降格、通知件数を加算
#   4. 残ったエントリについて hook.py を JSON stdin で再起動（fire-and-forget）
#   5. 1 回の起動で dead_letter に降格した件数があれば 1 度だけ通知
#
# 設計上の前提:
#   - hook.py は Terminal launcher を spawn して即 return する非同期構造のため、
#     本スクリプトはエントリごとに hook.py を逐次呼び出すだけで良い
#   - runner.sh が retry queue の attempt_count をインクリメントする
#     （成功したら remove、失敗したら upsert）
#   - 同時に複数 Claude Code セッションが起動した場合は、後発の retry-pending は
#     ロック取得に失敗してそのまま exit する（重複 spawn を防ぐ）
set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "${SCRIPTS_DIR}/../.." && pwd)}"
LOG_DIR_LOCAL="/tmp/memories"
LOG_FILE="$LOG_DIR_LOCAL/recording-retry.log"
mkdir -p "$LOG_DIR_LOCAL"

LOG_ROTATE_LIB="$PLUGIN_ROOT/scripts/lib/log_rotate.sh"
if [[ -f "$LOG_ROTATE_LIB" ]]; then
    # shellcheck source=../lib/log_rotate.sh
    source "$LOG_ROTATE_LIB"
    rotate_log_if_needed "$LOG_FILE" || true
fi

STATE_DIR="${HOME}/.local/share/recording/state"
LOCK_DIR="$STATE_DIR/retry-pending.lock.d"
RETRY_QUEUE_PY="$SCRIPTS_DIR/retry_queue.py"
HOOK_PY="$SCRIPTS_DIR/hook.py"

MAX_ATTEMPTS="${MEMORIES_RETRY_MAX_ATTEMPTS:-5}"

mkdir -p "$STATE_DIR"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

_escape_for_osascript() {
    printf '%s' "$1" | tr '\n\r' '  ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

notify_failure() {
    if ! command -v osascript >/dev/null 2>&1; then
        log "notify skipped (osascript not found): $1"
        return
    fi
    local msg_esc
    msg_esc="$(_escape_for_osascript "$1")"
    osascript <<APPLE >/dev/null 2>&1 || true
tell application "System Events"
    display alert "Episodic Recording" message "$msg_esc" as critical buttons {"OK"} default button "OK"
end tell
APPLE
}

acquire_lock() {
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo $$ > "$LOCK_DIR/pid"
        return 0
    fi
    local old_pid
    old_pid=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")
    if [[ -n "$old_pid" ]] && ! kill -0 "$old_pid" 2>/dev/null; then
        log "stale lock from pid=$old_pid; removing"
        rm -rf "$LOCK_DIR"
        if mkdir "$LOCK_DIR" 2>/dev/null; then
            echo $$ > "$LOCK_DIR/pid"
            return 0
        fi
    fi
    return 1
}

if [[ ! -x "$RETRY_QUEUE_PY" && ! -f "$RETRY_QUEUE_PY" ]]; then
    log "retry_queue.py not found: $RETRY_QUEUE_PY"
    exit 0
fi
if [[ ! -f "$HOOK_PY" ]]; then
    log "hook.py not found: $HOOK_PY"
    exit 0
fi

if ! acquire_lock; then
    log "skip: another retry-pending is running (pid=$(cat "$LOCK_DIR/pid" 2>/dev/null))"
    exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT

log "retry-pending start: pid=$$ max_attempts=$MAX_ATTEMPTS"

# キュー全件（attempt_count 上限なし）を取得し、本スクリプト側で pre-scan する。
ENTRIES_JSON="$(python3 "$RETRY_QUEUE_PY" list --max-attempts 9999 2>>"$LOG_FILE" || true)"
if [[ -z "$ENTRIES_JSON" ]]; then
    log "skip: queue empty"
    exit 0
fi

DEAD_LETTER_BATCH=0
SPAWNED=0
DROPPED_REPORT_EXISTS=0
DROPPED_TRANSCRIPT_MISSING=0

while IFS= read -r line; do
    [[ -z "$line" ]] && continue

    SESSION_ID=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("session_id",""))' 2>/dev/null)
    CWD=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("cwd",""))' 2>/dev/null)
    TRANSCRIPT=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("transcript_path",""))' 2>/dev/null)
    REPORT_PATH=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("report_path",""))' 2>/dev/null)
    ATTEMPT=$(printf '%s' "$line" | python3 -c 'import json,sys;print(json.loads(sys.stdin.read()).get("attempt_count",0))' 2>/dev/null)

    if [[ -z "$SESSION_ID" ]]; then
        log "warn: malformed entry (no session_id), skipping: $line"
        continue
    fi
    # キューファイル改ざん耐性: UUID 形式以外を弾く（hook.py の sanitize_session_id と同条件）。
    if ! [[ "$SESSION_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
        log "warn: skip entry (invalid session_id): $SESSION_ID"
        continue
    fi

    # pre-scan a: report_path がすでに存在
    if [[ -n "$REPORT_PATH" && -f "$REPORT_PATH" ]]; then
        log "drop (report exists): session=$SESSION_ID path=$REPORT_PATH"
        python3 "$RETRY_QUEUE_PY" remove -- "$SESSION_ID" >>"$LOG_FILE" 2>&1 || true
        DROPPED_REPORT_EXISTS=$((DROPPED_REPORT_EXISTS + 1))
        continue
    fi

    # pre-scan b: transcript_path 消失
    if [[ -z "$TRANSCRIPT" || ! -f "$TRANSCRIPT" ]]; then
        log "drop (transcript missing): session=$SESSION_ID transcript=$TRANSCRIPT"
        python3 "$RETRY_QUEUE_PY" remove -- "$SESSION_ID" >>"$LOG_FILE" 2>&1 || true
        DROPPED_TRANSCRIPT_MISSING=$((DROPPED_TRANSCRIPT_MISSING + 1))
        continue
    fi

    # pre-scan c: attempt_count が MAX 超過 → dead_letter
    if [[ "$ATTEMPT" =~ ^[0-9]+$ ]] && [[ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]]; then
        log "promote dead_letter: session=$SESSION_ID attempt=$ATTEMPT"
        python3 "$RETRY_QUEUE_PY" promote-dead-letter -- "$SESSION_ID" >>"$LOG_FILE" 2>&1 || true
        DEAD_LETTER_BATCH=$((DEAD_LETTER_BATCH + 1))
        continue
    fi

    # hook.py へ再投入。stdin に JSON を渡し、Terminal launcher を spawn させる。
    log "spawn retry: session=$SESSION_ID attempt=$ATTEMPT cwd=$CWD"
    HOOK_PAYLOAD=$(python3 -c '
import json, sys
print(json.dumps({
    "session_id": sys.argv[1],
    "cwd": sys.argv[2],
    "transcript_path": sys.argv[3],
}))
' "$SESSION_ID" "$CWD" "$TRANSCRIPT")

    # hook.py 自体は即 return するため、明示的に & で背景起動する必要はない。
    # ただし hook.py 内部の例外で本ループが死なないよう || true する。
    printf '%s' "$HOOK_PAYLOAD" | CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" python3 "$HOOK_PY" >>"$LOG_FILE" 2>&1 || \
        log "warn: hook.py invocation failed for session=$SESSION_ID"
    SPAWNED=$((SPAWNED + 1))
done <<< "$ENTRIES_JSON"

log "retry-pending done: spawned=$SPAWNED dropped_report=$DROPPED_REPORT_EXISTS dropped_transcript=$DROPPED_TRANSCRIPT_MISSING dead_letter=$DEAD_LETTER_BATCH"

if [[ $DEAD_LETTER_BATCH -gt 0 ]]; then
    notify_failure "${DEAD_LETTER_BATCH} 件のセッション要約が ${MAX_ATTEMPTS} 回失敗し dead_letter に移送されました。詳細: $STATE_DIR/session-retry-deadletter.jsonl"
fi

exit 0
