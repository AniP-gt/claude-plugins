#!/usr/bin/env bash
# hook.py から subprocess.Popen で直接バックグラウンド起動されるランナー。
# stdin / stdout / stderr は呼び出し元で ~/.local/state/episodic/logs/session-runner.log に redirect されている前提。
# 完了時の状況は macOS 通知センター（display notification）で通知する（成功・SKIP・失敗いずれも）。
# osascript / codex などのコマンドが無い環境ではログだけ残して該当処理をスキップする。
#
# Args:
#   $1: 命令プロンプト埋め込み済みMarkdownファイル（codex入力）
#   $2: 保存先レポートパス（マウント時は memories_dir/raw/session/...、staged 時は fallback_dir/...）
#   $3: "staged" or "normal"（staged の場合は wiki enqueue / cocoindex update を抑止）
#   $4: meta sidecar（retry queue 連携で参照する JSON）
#
# 環境変数:
#   CODEX_RECORDING_MODEL    使用モデル（既定 gpt-5.4-mini）
#   CODEX_RECORDING_EFFORT   model_reasoning_effort（既定 low、minimal/low/medium/high/xhigh）
set -u

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
# session/ の親が plugin root（source repo / codex-hook-runtime 共通レイアウト）。
# 旧版が PLUGIN_ROOT と RUNTIME_ROOT を分けていたのは scripts/ 中継のため。
# 配置統一後は両者が同じディレクトリを指すので 1 つに集約する。
PLUGIN_ROOT="$(cd "${SCRIPTS_DIR}/.." && pwd)"
RUNTIME_ROOT="$PLUGIN_ROOT"

INPUT_MD="${1:?usage: $0 <combined_md> <report_path> <staged|normal> [meta_json]}"
REPORT_PATH="${2:?usage: $0 <combined_md> <report_path> <staged|normal> [meta_json]}"
STAGE_MODE="${3:-normal}"
META_PATH="${4:-}"
MODEL="${CODEX_RECORDING_MODEL:-gpt-5.4-mini}"
# 推論強度。session 要約はテンプレ埋めに近く深い推論を要さないため既定 low。
# minimal / low / medium / high / xhigh のうちモデルが対応する値を指定する。
EFFORT="${CODEX_RECORDING_EFFORT:-low}"
# 値域検証: 想定外の文字列が codex CLI の引数パーサーに到達するのを防ぐ。
case "$EFFORT" in
    minimal|low|medium|high|xhigh) ;;
    *) EFFORT="low" ;;
esac
# MEMORIES_DIR は wiki/cocoindex 連携で参照する。staged 時はこの値を使うのではなく、
# sync-pending.sh が後追いで処理するため、ここでは正規パス計算用としてのみ使う。
MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"
LOG_DIR_LOCAL="$HOME/.local/state/episodic/logs"
LOG_FILE="$LOG_DIR_LOCAL/session-runner.log"
mkdir -p "$LOG_DIR_LOCAL"
chmod 700 "$LOG_DIR_LOCAL" 2>/dev/null || true

# pending/{session_id}/ から最新 timestamp を再選択する（trap EXIT 取り残し検出に必要）。
# Popen 起動から runner.sh が走り出すまでの僅かな遅延中に新しい Stop が来て
# 新 timestamp が書かれた可能性があるため、INPUT_MD の親ディレクトリを SESSION_DIR とみなして
# 最新 *.codex.md を選び直す。
SESSION_DIR=$(dirname "$INPUT_MD")
LATEST_TS=""
LATEST_CODEX=$(ls -t "${SESSION_DIR}"/*.codex.md 2>/dev/null | head -1)
if [[ -n "$LATEST_CODEX" ]]; then
    INPUT_MD="$LATEST_CODEX"
    # {ts}.codex.md → {ts} を抽出して同 ts の meta / launcher / md を確定。
    LATEST_TS=$(basename "$LATEST_CODEX" .codex.md)
    META_CANDIDATE="${SESSION_DIR}/${LATEST_TS}.codex.meta.json"
    if [[ -f "$META_CANDIDATE" ]]; then
        META_PATH="$META_CANDIDATE"
    else
        META_PATH=""
    fi
fi

# ログ肥大化を防ぐため、起動直後に rotate を試みる（best effort）。
LOG_ROTATE_LIB="$RUNTIME_ROOT/lib/log_rotate.sh"
if [[ -f "$LOG_ROTATE_LIB" ]]; then
    # shellcheck source=../lib/log_rotate.sh
    source "$LOG_ROTATE_LIB"
    rotate_log_if_needed "$LOG_FILE" || true
fi

log() {
    mkdir -p "$(dirname "$LOG_FILE")"
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

notify() {
    # 引数: notify <subtitle> <msg> [sound]
    #   バックグラウンド実行で OK ボタン待ちブロッキングが起きないよう、
    #   display alert / dialog は使わず display notification（バナー、自動消失）に統一する。
    # macOS 以外、または osascript が無い環境ではログのみ残してスキップする。
    if ! command -v osascript >/dev/null 2>&1; then
        log "notify skipped (osascript not found): $1 / $2"
        return
    fi
    local subtitle="$1" msg="$2" sound="${3:-}"
    local rc
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
    log "notify: rc=$rc subtitle=$subtitle sound=${sound:-none} msg=$msg"
}

notify_success() { notify "完了" "$1" "Glass"; }
notify_skip()    { notify "スキップ" "$1"; }
notify_failure() { notify "失敗" "$1" "Basso"; }

log_run_header() {
    log "model=$MODEL effort=$EFFORT input=$INPUT_MD report=$REPORT_PATH"
    log "codex exec を実行します"
}

log "---"
log "runner start: input=$INPUT_MD report=$REPORT_PATH model=$MODEL effort=$EFFORT stage=$STAGE_MODE meta=$META_PATH pid=$$ ts=${LATEST_TS:-?}"

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

# session_id の UUID 検証（パストラバーサル防御）。SESSION_DIR の basename をここで判定する。
SESSION_ID_FROM_DIR=$(basename "$SESSION_DIR")
if [[ ! "$SESSION_ID_FROM_DIR" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
    log "warn: session_id from dir is not UUID, skip cleanup: $SESSION_ID_FROM_DIR"
    SESSION_ID_FROM_DIR=""
fi

# finalize が取得した処理中ロックの所有者を、この runner に移す。
# finalize 側の Python プロセスは launcher 起動後すぐ終了するため、その PID のままだと
# runner 実行中に stale lock と誤判定され、同一セッションの Codex が多重起動する。
if [[ -n "$SESSION_ID_FROM_DIR" && -d "${SESSION_DIR}/.lock" ]]; then
    printf '%s\n' "$$" > "${SESSION_DIR}/.lock/pid" 2>/dev/null || true
    touch "${SESSION_DIR}/.lock" 2>/dev/null || true
    log "runner claimed lock: session=$SESSION_ID_FROM_DIR pid=$$"
fi

cleanup_session_dir() {
    cleanup_meta_sidecar
    [[ -z "$SESSION_DIR" || ! -d "$SESSION_DIR" ]] && return 0
    # 削除対象パスのトラバーサル防御。pending ディレクトリ配下のみ許可。
    case "$SESSION_DIR" in
        "$HOME/.local/state/episodic/pending/"*) ;;
        *) return 0 ;;
    esac

    # 取り残し検出: 処理に使った {ts} より新しい {ts}.codex.md があれば再 finalize spawn。
    # finalize 中に新 Stop が来てロック取得失敗で skip された分を救済する。
    if [[ -n "$LATEST_TS" && -n "$SESSION_ID_FROM_DIR" ]]; then
        local newer
        newer=$(find "$SESSION_DIR" -maxdepth 1 -name '*.codex.md' -newer "${SESSION_DIR}/${LATEST_TS}.codex.md" 2>/dev/null | head -1)
        if [[ -n "$newer" ]]; then
            log "respawn finalize for newer timestamp: $newer"
            local hook_py="${SCRIPTS_DIR}/hook.py"
            # 現 runner.sh の trap EXIT で .lock を解放した直後に新 finalize がロックを取得できる。
            # SESSION_DIR は新 finalize の trap EXIT 経由で掃除されるためここでは消さない。
            rm -rf "${SESSION_DIR}/.lock"
            rm -f "${SESSION_DIR}/.debounce.pid"
            ( nohup python3 "$hook_py" --finalize "$SESSION_ID_FROM_DIR" \
                >> "$LOG_FILE" 2>&1 & ) >/dev/null 2>&1 || true
            return 0
        fi
    fi

    # 通常クリーンアップ: ディレクトリごと削除。
    rm -rf "$SESSION_DIR"
}

trigger_memory_wiki() {
    # 生成された Raw を Wiki ingest キューに enqueue し、debounced launcher を非同期起動。
    # wiki-runner は mkdir ロックで排他制御されるため、複数 Raw 同時生成でも安全。
    local raw_path="$1"
    local enqueue="${RUNTIME_ROOT}/wiki/enqueue.py"
    local wiki_kicker="${RUNTIME_ROOT}/wiki/kick-runner.sh"

    if [[ ! -f "$enqueue" || ! -x "$wiki_kicker" ]]; then
        log "wiki scripts not found; skip enqueue (enqueue=$enqueue wiki_kicker=$wiki_kicker)"
        return
    fi

    if ! python3 "$enqueue" "$raw_path" >> "$LOG_FILE" 2>&1; then
        log "warn: wiki enqueue failed for $raw_path"
        return
    fi
    log "enqueued to wiki ingest: $raw_path"

    # fire-and-forget で wiki kick-runner を起動（Raw 生成側は wiki 処理を待たない）
    ( nohup "$wiki_kicker" >> "$LOG_DIR_LOCAL/wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
}

# cocoindex update は wiki-runner.sh の処理完了後に 1 回だけ呼ぶ設計に統一済み。
# このスクリプトからは直接呼ばない（trigger_memory_wiki が起動する wiki-runner 内部で呼ばれる）。

# Codex CLI のパス解決。攻撃者が PATH を細工して悪意ある codex バイナリを差し込む攻撃に
# 備えて、絶対パスかつ世界書き込み可能ディレクトリ配下でないことを検証する。
# CODEX_BINARY を環境変数で明示指定できる（CI 等で固定したいケース向け）。
if [[ -n "${CODEX_BINARY:-}" ]]; then
    CODEX_BIN="$CODEX_BINARY"
else
    CODEX_BIN="$(command -v codex 2>/dev/null || true)"
fi
if [[ -z "$CODEX_BIN" || ! -x "$CODEX_BIN" ]]; then
    log "error: codex binary not executable: '${CODEX_BIN:-<empty>}'"
    notify_failure "codex コマンドが見つかりません。Codex CLI をインストールしてください。"
    exit 127
fi
if command -v realpath >/dev/null 2>&1; then
    CODEX_BIN_REAL="$(realpath "$CODEX_BIN" 2>/dev/null || echo "$CODEX_BIN")"
else
    CODEX_BIN_REAL="$CODEX_BIN"
fi
case "$CODEX_BIN_REAL" in
    /tmp/*|/var/tmp/*|/private/tmp/*|/private/var/tmp/*)
        log "error: codex binary in world-writable dir: $CODEX_BIN_REAL"
        notify_failure "codex のパスが世界書き込み可能ディレクトリ配下にあります: $CODEX_BIN_REAL"
        exit 126
        ;;
esac

if [[ ! -f "$INPUT_MD" ]]; then
    log "error: input not found: $INPUT_MD"
    notify_failure "入力Markdownが見つかりません: $INPUT_MD"
    exit 1
fi

mkdir -p "$(dirname "$REPORT_PATH")"

CODEX_LAST_MSG="$(mktemp -t codex-session.XXXXXX)"
trap 'rm -f "$CODEX_LAST_MSG"; cleanup_session_dir' EXIT

log_run_header
log "codex exec start (hooks disabled)"

# tee で session-runner.log にも追記する（hook.py 側 redirect と二重になっても害はない）。
# pipefail を有効にすると tee の失敗が混ざるため、PIPESTATUS で codex の RC のみを取る。
set -o pipefail
EPISODIC_RECORDING_ACTIVE=1 "$CODEX_BIN" exec \
    --disable hooks \
    --skip-git-repo-check \
    --sandbox workspace-write \
    --dangerously-bypass-approvals-and-sandbox \
    -c model_reasoning_effort="$EFFORT" \
    -m "$MODEL" \
    -o "$CODEX_LAST_MSG" \
    < "$INPUT_MD" 2>&1 | tee -a "$LOG_FILE"
CODEX_RC=${PIPESTATUS[0]}
set +o pipefail

if [[ $CODEX_RC -ne 0 ]]; then
    REASON="$(classify_failure_reason "$CODEX_RC")"
    log "error: codex exec failed (rc=$CODEX_RC reason=$REASON)"
    retry_queue_upsert "$REASON"
    notify_failure "codex exec に失敗しました（$REASON）。次回 SessionStart で自動リトライ。ログ: $LOG_FILE"
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
    log "report generated: $REPORT_PATH"
    post_process "$REPORT_PATH"
    exit 0
fi

# codexが最終メッセージとして全文を返した場合のフォールバック
if [[ -n "$LAST_MSG_CONTENT" ]] && printf '%s' "$LAST_MSG_CONTENT" | head -1 | grep -q '^---$'; then
    printf '%s' "$LAST_MSG_CONTENT" > "$REPORT_PATH"
    log "report written from last message: $REPORT_PATH"
    retry_queue_remove
    SUMMARY="$(summarize_report "$REPORT_PATH")"
    notify_success "$SUMMARY"
    post_process "$REPORT_PATH"
    exit 0
fi

log "warn: codex produced no report; last message: $LAST_MSG_CONTENT"
retry_queue_upsert "no_report"
notify_failure "codex がレポートを生成しませんでした。次回 SessionStart で自動リトライ。ログ: $LOG_FILE"
exit 2
