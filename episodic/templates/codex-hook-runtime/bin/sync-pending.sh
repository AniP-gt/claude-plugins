#!/usr/bin/env bash
# sync-pending: fallback_dir に staged 済みの Raw（session / web / minutes）を
# MEMORIES_DIR/raw/<kind>/ へ移送する。
#
# 起動条件:
#   - SessionStart hook（fire-and-forget で呼ばれる）
#   - 手動実行: scripts/sync-pending.sh または ~/.config/episodic/codex-hook-runtime/bin/sync-pending.sh
#
# staging 配置:
#   <fallback_dir>/YYYY-MM-DD/<base>__staged.md          # session（後方互換: kind 直下なし）
#   <fallback_dir>/web/YYYY-MM-DD/<base>__staged.md      # web
#   <fallback_dir>/minutes/YYYY-MM-DD/<base>__staged.md  # minutes
#
# 動作:
#   1. canary でマウント有効性を確認。NG ならスキップ
#   2. 上記 3 経路の staged ファイルを全件列挙
#   3. 各ファイルについて
#       a. 移送先 <memories_dir>/raw/<kind>/YYYY-MM-DD/<base>.md を計算（命名規則上絶対衝突しない）
#       b. 移送先がなければ atomic rename（同一 FS）or cp -p && rm（FS 跨ぎ）で移送
#       c. 移送先が存在 → ハッシュ完全一致なら staging 削除（成功）、不一致なら staging 保全＋通知
#   4. 移送成功した Raw について enqueue.py を kind 指定で呼び wiki キューに追加 + debounced launcher を起動
#      （wiki-runner.sh が処理完了後に cocoindex update を 1 回キックする統一経路）
#
# macOS 以外の環境では osascript / open / mount_smbfs などが無く、通知やマウント関連処理は
# 自動的にスキップされる（ログのみ残る）。
set -uo pipefail

BIN_DIR="$(cd "$(dirname "$0")" && pwd)"

resolve_runtime_root() {
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "${CLAUDE_PLUGIN_ROOT}/scripts/lib" ]]; then
        printf '%s\n' "${CLAUDE_PLUGIN_ROOT}/scripts"
        return
    fi
    if [[ -d "${BIN_DIR}/lib" ]]; then
        printf '%s\n' "$BIN_DIR"
        return
    fi
    # 後方互換: 旧配置 scripts/session/sync-pending.sh からの直接実行。
    if [[ -d "${BIN_DIR}/../lib" ]]; then
        (cd "${BIN_DIR}/.." && pwd)
        return
    fi
    printf '%s\n' "$BIN_DIR"
}

RUNTIME_ROOT="$(resolve_runtime_root)"
LOG_DIR_LOCAL="/tmp/episodic"
LOG_FILE="$LOG_DIR_LOCAL/session-sync.log"
mkdir -p "$LOG_DIR_LOCAL"

# ログ肥大化を防ぐため、起動直後に rotate を試みる（best effort）。
LOG_ROTATE_LIB="$RUNTIME_ROOT/lib/log_rotate.sh"
if [[ -f "$LOG_ROTATE_LIB" ]]; then
    # shellcheck source=../lib/log_rotate.sh
    source "$LOG_ROTATE_LIB"
    rotate_log_if_needed "$LOG_FILE" || true
fi

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

_escape_for_osascript() {
    # osascript 文字列リテラル用に " と \ をエスケープし、改行を空白に置換する。
    printf '%s' "$1" | tr '\n\r' '  ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

notify() {
    # 引数: notify <subtitle> <msg> [sound] [urgency]
    #   urgency = "alert" の場合は System Events 経由で display alert を表示し、
    #             OK ボタンを押すまで残す（手動で消すまで持続）。
    #   それ以外（既定 "info"）は通常の display notification（バナー、自動消失）。
    if ! command -v osascript >/dev/null 2>&1; then
        log "notify skipped (osascript not found): $1 / $2"
        return
    fi
    local subtitle="$1" msg="$2" sound="${3:-}" urgency="${4:-info}"
    local sub_esc msg_esc sound_clause=""
    sub_esc="$(_escape_for_osascript "$subtitle")"
    msg_esc="$(_escape_for_osascript "$msg")"
    if [[ "$urgency" == "alert" ]]; then
        # System Events 経由 → 起動アプリのフォーカスを奪わずモーダル表示できる
        # (macOS バージョンにより一部フォーカス挙動が異なるが、通知センターには
        #  流れず手動で閉じるまで残るのが本旨)。
        osascript <<APPLE >/dev/null 2>&1 || true
tell application "System Events"
    display alert "$sub_esc" message "$msg_esc" as critical buttons {"OK"} default button "OK"
end tell
APPLE
        return
    fi
    if [[ -n "$sound" ]]; then
        sound_clause=" sound name \"$sound\""
    fi
    osascript -e "display notification \"$msg_esc\" with title \"Episodic Recording Sync\" subtitle \"$sub_esc\"$sound_clause" >/dev/null 2>&1 || true
}

# 設定値（config.toml + 環境変数）を Python 経由で取得。
# lib は runtime root の lib/ に配置されているため、runtime root を sys.path に渡す。
read -r MEMORIES_DIR FALLBACK_DIR MOUNT_OK <<EOF
$(PYTHONDONTWRITEBYTECODE=1 MEMREC_SCRIPTS_DIR="${RUNTIME_ROOT}" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["MEMREC_SCRIPTS_DIR"])
from lib import config as c
print(c.resolve_memories_dir(), c.resolve_fallback_dir(), int(c.is_mount_active()))
PY
)
EOF

if [[ "$MOUNT_OK" != "1" ]]; then
    log "skip: canary not present at \$MEMORIES_DIR ($MEMORIES_DIR)"
    exit 0
fi

if [[ ! -d "$FALLBACK_DIR" ]]; then
    log "skip: fallback dir does not exist: $FALLBACK_DIR"
    exit 0
fi

# staged ファイルを kind 別に列挙する（macOS のシステム bash 3.2 には mapfile が無いため while で読む）。
# 走査経路:
#   - <fallback>/YYYY-MM-DD/*__staged.md           → kind: session（後方互換、kind サブディレクトリなし）
#   - <fallback>/web/YYYY-MM-DD/*__staged.md       → kind: web
#   - <fallback>/minutes/YYYY-MM-DD/*__staged.md   → kind: minutes
# 各エントリは "<src_path>\t<kind>" の TSV で持つ。
STAGED_TSV=()

# session 経路（fallback 直下の YYYY-MM-DD/*__staged.md）。
# 配下の web/ minutes/ サブディレクトリは別経路で拾うため depth=2 で除外する。
while IFS= read -r line; do
    [[ -n "$line" ]] && STAGED_TSV+=("${line}"$'\t'"session")
done < <(find "$FALLBACK_DIR" -mindepth 2 -maxdepth 2 -type f -name '*__staged.md' 2>/dev/null | sort)

# web / minutes 経路（kind サブディレクトリ配下）。
for kind in web minutes; do
    kind_root="$FALLBACK_DIR/$kind"
    [[ ! -d "$kind_root" ]] && continue
    while IFS= read -r line; do
        [[ -n "$line" ]] && STAGED_TSV+=("${line}"$'\t'"${kind}")
    done < <(find "$kind_root" -type f -name '*__staged.md' 2>/dev/null | sort)
done

if [[ ${#STAGED_TSV[@]:-0} -eq 0 ]]; then
    log "skip: no staged files in $FALLBACK_DIR"
    exit 0
fi

log "sync start: ${#STAGED_TSV[@]} staged file(s) across session/web/minutes"

MOVED=0
COLLIDED=0
DUPLICATE=0
FAILED=0
declare -a MOVED_TSV=()  # "<dst_path>\t<kind>" 形式で保持

sha256_of() {
    /usr/bin/shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
}

for entry in "${STAGED_TSV[@]}"; do
    src="${entry%$'\t'*}"
    kind="${entry##*$'\t'}"
    [[ -f "$src" ]] || continue

    date_dir="$(basename "$(dirname "$src")")"
    base="$(basename "$src")"
    # __staged.md → .md
    normal_base="${base%__staged.md}.md"
    dst_dir="$MEMORIES_DIR/raw/$kind/$date_dir"
    dst="$dst_dir/$normal_base"

    mkdir -p "$dst_dir" 2>/dev/null || true

    if [[ -e "$dst" ]]; then
        # 命名規則上ありえない衝突（session: host8+sid8+HHMMSS / web,minutes: HHMMSS+slug）
        src_hash="$(sha256_of "$src")"
        dst_hash="$(sha256_of "$dst")"
        if [[ -n "$src_hash" && "$src_hash" == "$dst_hash" ]]; then
            # 内容完全一致 → 過去同期で残った旧 staged。staging 側を消すだけ
            rm -f "$src"
            DUPLICATE=$((DUPLICATE + 1))
            log "duplicate, removed staging (kind=$kind): $src"
        else
            # 内容差分あり → staging 保全、人間判断に委ねる
            COLLIDED=$((COLLIDED + 1))
            log "COLLISION (kind=$kind): $src vs $dst (hashes differ; staging kept)"
        fi
        continue
    fi

    # 移送（同一 FS なら atomic mv、跨ぐなら cp+rm でフォールバック）
    if mv "$src" "$dst" 2>>"$LOG_FILE"; then
        MOVED=$((MOVED + 1))
        MOVED_TSV+=("${dst}"$'\t'"${kind}")
        log "moved (kind=$kind): $src -> $dst"
    else
        # cross-FS の可能性。cp -p してから rm
        if cp -p "$src" "$dst" 2>>"$LOG_FILE" && rm -f "$src"; then
            MOVED=$((MOVED + 1))
            MOVED_TSV+=("${dst}"$'\t'"${kind}")
            log "copied(cross-fs, kind=$kind): $src -> $dst"
        else
            FAILED=$((FAILED + 1))
            log "FAILED (kind=$kind): $src -> $dst"
        fi
    fi
done

# 空ディレクトリ掃除（staging 側の YYYY-MM-DD・kind サブディレクトリのみ。ルートは消さない）
find "$FALLBACK_DIR" -mindepth 1 -type d -empty -delete 2>/dev/null || true

log "sync done: moved=$MOVED duplicate=$DUPLICATE collided=$COLLIDED failed=$FAILED"

# 移送成功分を kind 指定で wiki キューへ enqueue → debounced launcher を起動
ENQUEUE="${RUNTIME_ROOT}/wiki/enqueue.py"
WIKI_KICKER="${RUNTIME_ROOT}/wiki/kick-runner.sh"

if [[ ${#MOVED_TSV[@]} -gt 0 ]]; then
    if [[ -f "$ENQUEUE" ]]; then
        for entry in "${MOVED_TSV[@]}"; do
            p="${entry%$'\t'*}"
            kind="${entry##*$'\t'}"
            python3 "$ENQUEUE" "$p" --kind "$kind" >> "$LOG_FILE" 2>&1 || \
                log "warn: enqueue failed (kind=$kind) for $p"
        done
        if [[ -x "$WIKI_KICKER" ]]; then
            ( nohup "$WIKI_KICKER" >> "$LOG_DIR_LOCAL/wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
        fi
    else
        log "warn: enqueue script not found: $ENQUEUE"
    fi

    # cocoindex update は wiki-runner.sh の処理完了後に 1 回だけ呼ばれる（重複起動回避）。
    # 上で起動した wiki-runner が cocoindex_trigger.sh 経由で update する。
fi

if [[ $COLLIDED -gt 0 || $FAILED -gt 0 ]]; then
    notify "衝突あり" \
        "${COLLIDED} 件衝突 / ${FAILED} 件失敗。手動確認が必要です。ログ: $LOG_FILE" \
        "Basso" "alert"
elif [[ $MOVED -gt 0 ]]; then
    notify "同期完了" "${MOVED} 件の staged を共有へ移送しました。"
fi

exit 0
