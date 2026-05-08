#!/usr/bin/env bash
# Terminal.appウィンドウ内で実行されることを前提としたランナー（macOS）。
# codexのstdoutを画面に流しつつ tee で LOG_FILE にも追記する。
# 完了時に macOS 通知センターで通知する（成功・SKIP・失敗いずれも）。
# osascript / open / codex などのコマンドが無い環境ではログだけ残して該当処理をスキップする。
#
# Args:
#   $1: 命令プロンプト埋め込み済みMarkdownファイル（codex入力）
#   $2: 保存先レポートパス（マウント時は memories_dir/raw/session/...、staged 時は fallback_dir/...）
#   $3: "staged" or "normal"（staged の場合は wiki enqueue / cocoindex update を抑止）
set -u

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "${SCRIPTS_DIR}/../.." && pwd)}"

INPUT_MD="${1:?usage: $0 <combined_md> <report_path> <staged|normal> [meta_json]}"
REPORT_PATH="${2:?usage: $0 <combined_md> <report_path> <staged|normal> [meta_json]}"
STAGE_MODE="${3:-normal}"
META_PATH="${4:-}"
MODEL="${CODEX_RECORDING_MODEL:-gpt-5.4-mini}"
# MEMORIES_DIR は wiki/cocoindex 連携で参照する。staged 時はこの値を使うのではなく、
# sync-pending.sh が後追いで処理するため、ここでは正規パス計算用としてのみ使う。
MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"
LOG_DIR_LOCAL="/tmp/memories"
LOG_FILE="$LOG_DIR_LOCAL/recording-runner.log"
mkdir -p "$LOG_DIR_LOCAL"

# ログ肥大化を防ぐため、起動直後に rotate を試みる（best effort）。
LOG_ROTATE_LIB="$PLUGIN_ROOT/scripts/lib/log_rotate.sh"
if [[ -f "$LOG_ROTATE_LIB" ]]; then
    # shellcheck source=../lib/log_rotate.sh
    source "$LOG_ROTATE_LIB"
    rotate_log_if_needed "$LOG_FILE" || true
fi

# ANSI色コード（Terminal表示用）
readonly C_CYAN=$'\033[1;36m'
readonly C_YELLOW=$'\033[1;33m'
readonly C_GREEN=$'\033[1;32m'
readonly C_RED=$'\033[1;31m'
readonly C_RESET=$'\033[0m'

log() {
    mkdir -p "$(dirname "$LOG_FILE")"
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

notify() {
    # 引数: notify <subtitle> <msg> [sound] [urgency]
    #   urgency = "alert" の場合は System Events 経由で display alert を表示し、
    #             OK ボタンを押すまで残す（手動で消すまで持続）。
    #   それ以外（既定 "info"）は通常の display notification（バナー、自動消失）。
    # macOS 以外、または osascript が無い環境ではログのみ残してスキップする。
    if ! command -v osascript >/dev/null 2>&1; then
        log "notify skipped (osascript not found): $1 / $2"
        return
    fi
    local subtitle="$1" msg="$2" sound="${3:-}" urgency="${4:-info}"
    local rc
    if [[ "$urgency" == "alert" ]]; then
        osascript \
            -e 'on run argv' \
            -e 'tell application "System Events"' \
            -e 'display alert (item 1 of argv) message (item 2 of argv) as critical buttons {"OK"} default button "OK"' \
            -e 'end tell' \
            -e 'end run' \
            "$subtitle" "$msg" >>"$LOG_FILE" 2>&1
        rc=$?
        log "notify alert: rc=$rc subtitle=$subtitle msg=$msg"
        return
    fi
    if [[ -n "$sound" ]]; then
        osascript \
            -e 'on run argv' \
            -e 'display notification (item 1 of argv) with title "Episodic Recording" subtitle (item 2 of argv) sound name (item 3 of argv)' \
            -e 'end run' \
            "$msg" "$subtitle" "$sound" >>"$LOG_FILE" 2>&1
    else
        osascript \
            -e 'on run argv' \
            -e 'display notification (item 1 of argv) with title "Episodic Recording" subtitle (item 2 of argv)' \
            -e 'end run' \
            "$msg" "$subtitle" >>"$LOG_FILE" 2>&1
    fi
    rc=$?
    log "notify notification: rc=$rc subtitle=$subtitle sound=${sound:-none} msg=$msg"
}

notify_success() { notify "完了" "$1" "Glass"; }
notify_skip()    { notify "スキップ" "$1"; }
notify_failure() { notify "失敗" "$1" "Basso" "alert"; }

print_banner() {
    printf '%s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n' "$C_CYAN" "$C_RESET"
    printf '%s  Episodic Recording%s\n' "$C_CYAN" "$C_RESET"
    printf '%s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n' "$C_CYAN" "$C_RESET"
    printf 'Model:  %s\n' "$MODEL"
    printf 'Input:  %s\n' "$INPUT_MD"
    printf 'Report: %s\n' "$REPORT_PATH"
    printf 'Log:    %s\n' "$LOG_FILE"
    printf '\n'
    printf '%s▶ codex exec を実行中...%s\n\n' "$C_YELLOW" "$C_RESET"
}

log "---"
log "runner start: input=$INPUT_MD report=$REPORT_PATH model=$MODEL stage=$STAGE_MODE meta=$META_PATH pid=$$"

RETRY_QUEUE_PY="$SCRIPTS_DIR/retry_queue.py"

# meta sidecar から retry queue 連携用のフィールドを抽出する。
# meta が無い／壊れている場合は META_SESSION_ID 等を空文字のまま runner を続行する
# （retry queue 操作は session_id が無ければ no-op になる）。
META_SESSION_ID=""
META_CWD=""
META_TRANSCRIPT=""
META_FIRST_TS=""
META_REPORT_PATH=""
META_IS_STAGED=""
if [[ -n "$META_PATH" && -f "$META_PATH" ]]; then
    while IFS=$'\t' read -r k v; do
        case "$k" in
            session_id)      META_SESSION_ID="$v" ;;
            cwd)             META_CWD="$v" ;;
            transcript_path) META_TRANSCRIPT="$v" ;;
            first_ts)        META_FIRST_TS="$v" ;;
            report_path)     META_REPORT_PATH="$v" ;;
            is_staged)       META_IS_STAGED="$v" ;;
        esac
    done < <(META_PATH="$META_PATH" python3 - <<'PY' 2>/dev/null
import json, os, sys
try:
    with open(os.environ["META_PATH"], encoding="utf-8") as f:
        d = json.load(f) or {}
except Exception:
    sys.exit(0)
for k in ("session_id", "cwd", "transcript_path", "first_ts", "report_path", "is_staged"):
    v = d.get(k, "")
    if isinstance(v, bool):
        v = "1" if v else "0"
    print(f"{k}\t{v}")
PY
)
fi

# 失敗理由を Codex の標準出力（LOG_FILE に tee 済）から推定する。
classify_failure_reason() {
    local rc="$1"
    if [[ ! -s "$LOG_FILE" ]]; then
        echo "unknown"
        return
    fi
    # 直近 200 行に絞って判定（LOG_FILE 全体を grep すると過去のセッション失敗まで拾うため）。
    local recent
    recent="$(tail -n 200 "$LOG_FILE" 2>/dev/null)"
    if printf '%s' "$recent" | grep -qiE "you've hit your usage limit|usage limit|rate.?limit"; then
        echo "usage_limit"
    elif printf '%s' "$recent" | grep -qiE "unauthorized|invalid api key|authentication|not logged in"; then
        echo "auth_failure"
    else
        echo "unknown"
    fi
}

# UUID 形式（hook.py の sanitize_session_id と同じ）以外を弾く防御。meta sidecar 改ざん耐性。
_is_valid_uuid() {
    [[ "$1" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]
}

retry_queue_upsert() {
    local reason="$1"
    [[ -z "$META_SESSION_ID" ]] && return 0
    if ! _is_valid_uuid "$META_SESSION_ID"; then
        log "warn: skip retry queue upsert (invalid session_id): $META_SESSION_ID"
        return 0
    fi
    [[ ! -f "$RETRY_QUEUE_PY" ]] && { log "warn: retry_queue.py not found at $RETRY_QUEUE_PY"; return 0; }
    local staged_flag=()
    [[ "$META_IS_STAGED" == "1" ]] && staged_flag=(--is-staged)
    # `--` で positional 引数を保護し、session_id が `--` で始まっても option 解釈されないようにする。
    if python3 "$RETRY_QUEUE_PY" upsert \
            --cwd "$META_CWD" \
            --transcript "$META_TRANSCRIPT" \
            --first-ts "$META_FIRST_TS" \
            --report-path "$META_REPORT_PATH" \
            "${staged_flag[@]}" \
            --reason "$reason" \
            -- "$META_SESSION_ID" >>"$LOG_FILE" 2>&1; then
        log "retry queue upserted: session=$META_SESSION_ID reason=$reason"
    else
        log "warn: retry queue upsert failed: session=$META_SESSION_ID"
    fi
}

retry_queue_remove() {
    [[ -z "$META_SESSION_ID" ]] && return 0
    if ! _is_valid_uuid "$META_SESSION_ID"; then
        log "warn: skip retry queue remove (invalid session_id): $META_SESSION_ID"
        return 0
    fi
    [[ ! -f "$RETRY_QUEUE_PY" ]] && return 0
    python3 "$RETRY_QUEUE_PY" remove -- "$META_SESSION_ID" >>"$LOG_FILE" 2>&1 || \
        log "warn: retry queue remove failed: session=$META_SESSION_ID"
}

cleanup_meta_sidecar() {
    [[ -n "$META_PATH" && -f "$META_PATH" ]] && rm -f "$META_PATH"
}

trigger_memory_wiki() {
    # 生成された Raw を Wiki ingest キューに enqueue し、wiki-runner を非同期起動。
    # wiki-runner は mkdir ロックで排他制御されるため、複数 Raw 同時生成でも安全。
    local raw_path="$1"
    local enqueue="${PLUGIN_ROOT}/scripts/wiki/enqueue.py"
    local wiki_runner="${PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh"

    if [[ ! -f "$enqueue" || ! -x "$wiki_runner" ]]; then
        log "wiki scripts not found; skip enqueue (enqueue=$enqueue wiki_runner=$wiki_runner)"
        return
    fi

    if ! python3 "$enqueue" "$raw_path" >> "$LOG_FILE" 2>&1; then
        log "warn: wiki enqueue failed for $raw_path"
        return
    fi
    log "enqueued to wiki ingest: $raw_path"

    # fire-and-forget で wiki-runner を起動（Raw 生成 Terminal を待たない）
    ( nohup "$wiki_runner" >> "$LOG_DIR_LOCAL/memory-wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
}

# cocoindex update は wiki-runner.sh の処理完了後に 1 回だけ呼ぶ設計に統一済み。
# このスクリプトからは直接呼ばない（trigger_memory_wiki が起動する wiki-runner 内部で呼ばれる）。

if ! command -v codex >/dev/null 2>&1; then
    log "error: codex command not found in PATH; cannot generate session report"
    notify_failure "codex コマンドが見つかりません。Codex CLI をインストールしてください。"
    printf '%s✗ codex コマンドが見つかりません%s\n' "$C_RED" "$C_RESET"
    exit 127
fi

if [[ ! -f "$INPUT_MD" ]]; then
    log "error: input not found: $INPUT_MD"
    notify_failure "入力Markdownが見つかりません: $INPUT_MD"
    printf '%s✗ 入力ファイルが見つかりません: %s%s\n' "$C_RED" "$INPUT_MD" "$C_RESET"
    printf '\n%s(このウィンドウは失敗時に残ります。閉じるには Enter を押してください)%s\n' "$C_YELLOW" "$C_RESET"
    read -r _ || true
    exit 1
fi

mkdir -p "$(dirname "$REPORT_PATH")"

CODEX_LAST_MSG="$(mktemp -t codex-recording.XXXXXX)"
trap 'rm -f "$CODEX_LAST_MSG"; cleanup_meta_sidecar' EXIT

print_banner
log "codex exec start"

set -o pipefail
codex exec \
    --skip-git-repo-check \
    --sandbox workspace-write \
    --dangerously-bypass-approvals-and-sandbox \
    -m "$MODEL" \
    -o "$CODEX_LAST_MSG" \
    < "$INPUT_MD" 2>&1 | tee -a "$LOG_FILE"
CODEX_RC=$?
set +o pipefail

if [[ $CODEX_RC -ne 0 ]]; then
    REASON="$(classify_failure_reason "$CODEX_RC")"
    log "error: codex exec failed (rc=$CODEX_RC reason=$REASON)"
    retry_queue_upsert "$REASON"
    notify_failure "codex exec に失敗しました（$REASON）。ログ: $LOG_FILE"
    printf '\n%s✗ codex exec に失敗しました (rc=%d, %s)%s\n' "$C_RED" "$CODEX_RC" "$REASON" "$C_RESET"
    printf '%s次回 SessionStart で自動リトライされます。%s\n' "$C_YELLOW" "$C_RESET"
    printf '\n%s(このウィンドウは失敗時に残ります。閉じるには Enter を押してください)%s\n' "$C_YELLOW" "$C_RESET"
    read -r _ || true
    exit 1
fi

LAST_MSG_CONTENT="$(cat "$CODEX_LAST_MSG" 2>/dev/null || true)"

# SKIP判定（作業実体なし）
if printf '%s' "$LAST_MSG_CONTENT" | grep -q '^SKIP:'; then
    # 通知用は先頭1行のみ取り出す（codex が複数行で SKIP 理由を返した場合の osascript 安全性）
    SKIP_FIRST_LINE="$(printf '%s' "$LAST_MSG_CONTENT" | head -1)"
    log "skipped by codex: $LAST_MSG_CONTENT"
    retry_queue_remove
    notify_skip "$SKIP_FIRST_LINE"
    printf '\n%s⊘ %s%s\n' "$C_YELLOW" "$SKIP_FIRST_LINE" "$C_RESET"
    sleep 2
    exit 0
fi

summarize_report() {
    # 通知本文向けに「project名 / Title」形式の簡易サマリを作成する。
    local report="$1"
    local project title
    project=$(awk '/^project:/ { sub(/^project:[[:space:]]*/, ""); print; exit }' "$report" 2>/dev/null)
    title=$(awk '/^title:/ { sub(/^title:[[:space:]]*/, ""); print; exit }' "$report" 2>/dev/null)
    [[ -z "$project" ]] && project="?"
    if [[ -n "$title" ]]; then
        printf '%s — %s' "$project" "$title"
    else
        printf '%s' "$project"
    fi
}

post_process() {
    # report 書き込み成功後の後処理。staged 時は wiki を呼ばず、
    # SessionStart hook 経由の sync-pending.sh が後追いで処理する。
    # cocoindex update は wiki-runner.sh の処理完了後に 1 回だけ呼ばれる（重複起動回避）。
    local report_path="$1"
    if [[ "$STAGE_MODE" == "staged" ]]; then
        log "post-process skipped (staged): $report_path — sync-pending will handle"
        printf '%s⚠ 共有未マウントのため staging に保存しました。次回マウント成功時に自動同期されます。%s\n' "$C_YELLOW" "$C_RESET"
        return
    fi
    trigger_memory_wiki "$report_path"
}

# codexが直接ファイルを書いた場合（推奨経路）
if [[ -f "$REPORT_PATH" ]]; then
    log "report written by codex: $REPORT_PATH"
    retry_queue_remove
    SUMMARY="$(summarize_report "$REPORT_PATH")"
    notify_success "$SUMMARY"
    printf '\n%s✓ レポート生成完了: %s%s\n' "$C_GREEN" "$REPORT_PATH" "$C_RESET"
    post_process "$REPORT_PATH"
    sleep 2
    exit 0
fi

# codexが最終メッセージとして全文を返した場合のフォールバック
if [[ -n "$LAST_MSG_CONTENT" ]] && printf '%s' "$LAST_MSG_CONTENT" | head -1 | grep -q '^---$'; then
    printf '%s' "$LAST_MSG_CONTENT" > "$REPORT_PATH"
    log "report written from last message: $REPORT_PATH"
    retry_queue_remove
    SUMMARY="$(summarize_report "$REPORT_PATH")"
    notify_success "$SUMMARY"
    printf '\n%s✓ レポート生成完了（フォールバック経路）: %s%s\n' "$C_GREEN" "$REPORT_PATH" "$C_RESET"
    post_process "$REPORT_PATH"
    sleep 2
    exit 0
fi

log "warn: codex produced no report; last message: $LAST_MSG_CONTENT"
retry_queue_upsert "no_report"
notify_failure "codexがレポートを生成しませんでした。ログ: $LOG_FILE"
printf '\n%s✗ codexがレポートを生成しませんでした%s\n' "$C_RED" "$C_RESET"
printf '%s次回 SessionStart で自動リトライされます。%s\n' "$C_YELLOW" "$C_RESET"
printf '\n%s(このウィンドウは失敗時に残ります。閉じるには Enter を押してください)%s\n' "$C_YELLOW" "$C_RESET"
read -r _ || true
exit 2
