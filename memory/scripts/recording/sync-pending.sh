#!/usr/bin/env bash
# sync-pending: fallback_dir に staged 済みの session レポートを MEMORIES_DIR/raw/sessions/ へ移送する。
# session（Claude Code セッション要約）専用。web / minutes は手動経路のため staging を使わない。
#
# 起動条件:
#   - SessionStart hook（fire-and-forget で呼ばれる）
#   - 手動実行: ${CLAUDE_PLUGIN_ROOT}/scripts/recording/sync-pending.sh
#
# 動作:
#   1. canary でマウント有効性を確認。NG ならスキップ
#   2. fallback_dir/YYYY-MM-DD/<basename>__staged.md を全件列挙
#   3. 各ファイルについて
#       a. 移送先 <memories_dir>/raw/sessions/YYYY-MM-DD/<basename>.md を計算（命名規則上絶対衝突しない）
#       b. 移送先がなければ atomic rename（同一 FS）or cp -p && rm（FS 跨ぎ）で移送
#       c. 移送先が存在 → ハッシュ完全一致なら staging 削除（成功）、不一致なら staging 保全＋通知
#   4. 移送成功した session レポートについて enqueue.py を呼び wiki キューに追加
#   5. 1 件以上正規パスへ移った場合のみ cocoindex update をキック
#
# macOS 以外の環境では osascript / open / mount_smbfs などが無く、通知やマウント関連処理は
# 自動的にスキップされる（ログのみ残る）。
set -uo pipefail

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "${SCRIPTS_DIR}/../.." && pwd)}"
LOG_DIR_LOCAL="/tmp/memories"
LOG_FILE="$LOG_DIR_LOCAL/recording-sync.log"
mkdir -p "$LOG_DIR_LOCAL"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*" >> "$LOG_FILE"
}

_escape_for_osascript() {
    # osascript 文字列リテラル用に " と \ をエスケープし、改行を空白に置換する。
    printf '%s' "$1" | tr '\n\r' '  ' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

notify() {
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
    osascript -e "display notification \"$msg_esc\" with title \"Claude Code Recording Sync\" subtitle \"$sub_esc\"$sound_clause" >/dev/null 2>&1 || true
}

# 設定値（config.toml + 環境変数）を Python 経由で取得。
# lib は <PLUGIN_ROOT>/scripts/lib に配置されているため、scripts ディレクトリを sys.path に渡す。
read -r MEMORIES_DIR FALLBACK_DIR MOUNT_OK <<EOF
$(MEMREC_SCRIPTS_DIR="${PLUGIN_ROOT}/scripts" python3 - <<'PY'
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

# staged ファイルを列挙（macOS のシステム bash 3.2 には mapfile が無いため while で読む）
STAGED_FILES=()
while IFS= read -r line; do
    [[ -n "$line" ]] && STAGED_FILES+=("$line")
done < <(find "$FALLBACK_DIR" -type f -name '*__staged.md' 2>/dev/null | sort)

if [[ ${#STAGED_FILES[@]:-0} -eq 0 ]]; then
    log "skip: no staged files in $FALLBACK_DIR"
    exit 0
fi

log "sync start: ${#STAGED_FILES[@]} staged file(s)"

MOVED=0
COLLIDED=0
DUPLICATE=0
FAILED=0
declare -a MOVED_PATHS=()

sha256_of() {
    /usr/bin/shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
}

for src in "${STAGED_FILES[@]}"; do
    [[ -f "$src" ]] || continue

    date_dir="$(basename "$(dirname "$src")")"
    base="$(basename "$src")"
    # __staged.md → .md
    normal_base="${base%__staged.md}.md"
    dst_dir="$MEMORIES_DIR/raw/sessions/$date_dir"
    dst="$dst_dir/$normal_base"

    mkdir -p "$dst_dir" 2>/dev/null || true

    if [[ -e "$dst" ]]; then
        # 命名規則上ありえない衝突（host8 + sid8 + HHMMSS が一致）
        src_hash="$(sha256_of "$src")"
        dst_hash="$(sha256_of "$dst")"
        if [[ -n "$src_hash" && "$src_hash" == "$dst_hash" ]]; then
            # 内容完全一致 → 過去同期で残った旧 staged。staging 側を消すだけ
            rm -f "$src"
            DUPLICATE=$((DUPLICATE + 1))
            log "duplicate, removed staging: $src"
        else
            # 内容差分あり → staging 保全、人間判断に委ねる
            COLLIDED=$((COLLIDED + 1))
            log "COLLISION: $src vs $dst (hashes differ; staging kept)"
        fi
        continue
    fi

    # 移送（同一 FS なら atomic mv、跨ぐなら cp+rm でフォールバック）
    if mv "$src" "$dst" 2>>"$LOG_FILE"; then
        MOVED=$((MOVED + 1))
        MOVED_PATHS+=("$dst")
        log "moved: $src -> $dst"
    else
        # cross-FS の可能性。cp -p してから rm
        if cp -p "$src" "$dst" 2>>"$LOG_FILE" && rm -f "$src"; then
            MOVED=$((MOVED + 1))
            MOVED_PATHS+=("$dst")
            log "copied(cross-fs): $src -> $dst"
        else
            FAILED=$((FAILED + 1))
            log "FAILED: $src -> $dst"
        fi
    fi
done

# 空ディレクトリ掃除（staging 側の YYYY-MM-DD のみ。ルートは消さない）
find "$FALLBACK_DIR" -mindepth 1 -type d -empty -delete 2>/dev/null || true

log "sync done: moved=$MOVED duplicate=$DUPLICATE collided=$COLLIDED failed=$FAILED"

# 移送成功分を wiki キューへ enqueue → wiki-runner を起動
ENQUEUE="${PLUGIN_ROOT}/scripts/wiki/enqueue.py"
WIKI_RUNNER="${PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh"

if [[ ${#MOVED_PATHS[@]} -gt 0 ]]; then
    if [[ -f "$ENQUEUE" ]]; then
        for p in "${MOVED_PATHS[@]}"; do
            python3 "$ENQUEUE" "$p" >> "$LOG_FILE" 2>&1 || \
                log "warn: enqueue failed for $p"
        done
        if [[ -x "$WIKI_RUNNER" ]]; then
            ( nohup "$WIKI_RUNNER" >> "$LOG_DIR_LOCAL/memory-wiki-runner.log" 2>&1 & ) >/dev/null 2>&1 || true
        fi
    else
        log "warn: enqueue script not found: $ENQUEUE"
    fi

    # cocoindex update をキック（runner.sh の trigger_cocoindex_update と同等）
    # cocoindex プラグインキャッシュは plugin update で消えるため動的解決する。
    PLUGIN_SCRIPTS="$(python3 -c "
import sys
sys.path.insert(0, '${PLUGIN_ROOT}/scripts')
from lib.cocoindex_path import resolve_cocoindex_scripts
p = resolve_cocoindex_scripts()
print(p if p else '', end='')
")"
    if [[ -z "$PLUGIN_SCRIPTS" || ! -d "$PLUGIN_SCRIPTS/.venv" ]]; then
        log "cocoindex update skipped: cocoindex plugin venv not found"
    elif ! command -v uv >/dev/null 2>&1; then
        log "cocoindex update skipped: uv not found in PATH"
    elif [[ ! -f "$SCRIPTS_DIR/main_memory.py" ]]; then
        log "cocoindex update skipped: main_memory.py not found ($SCRIPTS_DIR/main_memory.py)"
    else
        index_name="$(basename "$MEMORIES_DIR")"
        host_prefix="$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')"
        app_name="CodeIndex_${host_prefix}_${index_name}"
        (
            cd "$PLUGIN_SCRIPTS" \
            && SOURCE_PATH="$MEMORIES_DIR" \
                INDEX_NAME="$index_name" \
                PATTERNS="**/*.md" \
                nohup uv run cocoindex update -f "${SCRIPTS_DIR}/main_memory.py:${app_name}" \
                >> "$LOG_DIR_LOCAL/cocoindex-memories-update.log" 2>&1 &
        ) >/dev/null 2>&1 || true
        log "cocoindex update scheduled (post-sync)"
    fi
fi

if [[ $COLLIDED -gt 0 ]]; then
    notify "衝突あり" "${COLLIDED} 件の staged が移送先と内容差異。手動確認が必要です。" "Basso"
elif [[ $MOVED -gt 0 ]]; then
    notify "同期完了" "${MOVED} 件の staged を共有へ移送しました。"
fi

exit 0
