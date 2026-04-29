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

INPUT_MD="${1:?usage: $0 <combined_md> <report_path> <staged|normal>}"
REPORT_PATH="${2:?usage: $0 <combined_md> <report_path> <staged|normal>}"
STAGE_MODE="${3:-normal}"
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

_escape_for_osascript() {
    # osascript 文字列リテラル用に " と \ をエスケープし、改行を空白に置換する。
    # 改行を残すと osascript の文字列リテラルが切れ、AppleScript 側で構文エラーになるか
    # 意図しない式として解釈される可能性がある（codex 出力が複数行を含むケース等）。
    printf '%s' "$1" | tr '\n\r' '  ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

notify() {
    # macOS 以外、または osascript が無い環境ではログのみ残してスキップする。
    if ! command -v osascript >/dev/null 2>&1; then
        log "notify skipped (osascript not found): $1 / $2"
        return
    fi
    local subtitle="$1" msg="$2" sound="${3:-}"
    local sub_esc msg_esc sound_clause=""
    sub_esc="$(_escape_for_osascript "$subtitle")"
    msg_esc="$(_escape_for_osascript "$msg")"
    if [[ -n "$sound" ]]; then
        sound_clause=" sound name \"$sound\""
    fi
    osascript -e "display notification \"$msg_esc\" with title \"Claude Code Recording\" subtitle \"$sub_esc\"$sound_clause" >/dev/null 2>&1 || true
}

notify_success() { notify "完了" "$1" "Glass"; }
notify_skip()    { notify "スキップ" "$1"; }
notify_failure() { notify "失敗" "$1" "Basso"; }

print_banner() {
    printf '%s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n' "$C_CYAN" "$C_RESET"
    printf '%s  Claude Code Recording%s\n' "$C_CYAN" "$C_RESET"
    printf '%s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n' "$C_CYAN" "$C_RESET"
    printf 'Model:  %s\n' "$MODEL"
    printf 'Input:  %s\n' "$INPUT_MD"
    printf 'Report: %s\n' "$REPORT_PATH"
    printf 'Log:    %s\n' "$LOG_FILE"
    printf '\n'
    printf '%s▶ codex exec を実行中...%s\n\n' "$C_YELLOW" "$C_RESET"
}

log "---"
log "runner start: input=$INPUT_MD report=$REPORT_PATH model=$MODEL stage=$STAGE_MODE pid=$$"

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
trap 'rm -f "$CODEX_LAST_MSG"' EXIT

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
    log "error: codex exec failed (rc=$CODEX_RC)"
    notify_failure "codex exec に失敗しました。ログ: $LOG_FILE"
    printf '\n%s✗ codex exec に失敗しました (rc=%d)%s\n' "$C_RED" "$CODEX_RC" "$C_RESET"
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
    SUMMARY="$(summarize_report "$REPORT_PATH")"
    notify_success "$SUMMARY"
    printf '\n%s✓ レポート生成完了（フォールバック経路）: %s%s\n' "$C_GREEN" "$REPORT_PATH" "$C_RESET"
    post_process "$REPORT_PATH"
    sleep 2
    exit 0
fi

log "warn: codex produced no report; last message: $LAST_MSG_CONTENT"
notify_failure "codexがレポートを生成しませんでした。ログ: $LOG_FILE"
printf '\n%s✗ codexがレポートを生成しませんでした%s\n' "$C_RED" "$C_RESET"
printf '\n%s(このウィンドウは失敗時に残ります。閉じるには Enter を押してください)%s\n' "$C_YELLOW" "$C_RESET"
read -r _ || true
exit 2
