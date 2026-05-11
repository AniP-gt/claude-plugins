#!/usr/bin/env bash
# memory プラグイン共通: ログファイルのサイズ超過時に gzip ローテーションする。
#
# ~/.local/state/episodic/logs/*.log は永続領域だが、運用中（数日〜数週間）には
# Codex プロンプト全文・cocoindex 進捗・stack trace が積み重なって GB 級まで肥大する
# 可能性がある。各 runner の起動直後に rotate_log_if_needed を 1 回呼ぶ運用で抑える。
#
# 仕様:
#   - 閾値（既定 5MB）を超えていたら、現在の log を <log>.YYYYMMDDHHMMSS.gz に圧縮退避し、
#     active log を空にする
#   - 同一 prefix の .gz は世代数（既定 3）で打ち切り、古いものから順に削除
#   - ローテーション中の他 runner からの append とは競合し得るが、ロスが許容できる
#     ベストエフォート用途のため atomic 保証は行わない
#
# Usage:
#   source "${PLUGIN_ROOT}/scripts/lib/log_rotate.sh"
#   rotate_log_if_needed "$LOG_FILE"
#   rotate_log_if_needed "$LOG_FILE" 10485760 5  # 10MB / 5 世代
#
# 環境変数（個別呼び出しの引数より優先度低）:
#   MEMORIES_LOG_ROTATE_BYTES   閾値バイト数（既定 5242880 = 5MB）
#   MEMORIES_LOG_ROTATE_KEEP    保持世代数（既定 3）

rotate_log_if_needed() {
    local log_path="$1"
    local threshold="${2:-${MEMORIES_LOG_ROTATE_BYTES:-5242880}}"
    local keep="${3:-${MEMORIES_LOG_ROTATE_KEEP:-3}}"

    [[ -z "$log_path" ]] && return 0
    [[ ! -f "$log_path" ]] && return 0

    if ! [[ "$threshold" =~ ^[0-9]+$ ]] || ! [[ "$keep" =~ ^[0-9]+$ ]]; then
        return 0
    fi
    [[ "$threshold" == "0" ]] && return 0

    # macOS は stat -f %z、Linux は stat -c %s。両対応。
    local size
    size=$(stat -f %z "$log_path" 2>/dev/null || stat -c %s "$log_path" 2>/dev/null || echo 0)
    if ! [[ "$size" =~ ^[0-9]+$ ]]; then
        return 0
    fi
    if [[ "$size" -lt "$threshold" ]]; then
        return 0
    fi

    local ts
    ts=$(date '+%Y%m%d%H%M%S')
    local rotated="${log_path}.${ts}.gz"

    # gzip が無い環境ではローテーション自体をスキップ（best effort）。
    if ! command -v gzip >/dev/null 2>&1; then
        return 0
    fi

    if gzip -c "$log_path" > "$rotated" 2>/dev/null; then
        : > "$log_path"
    else
        rm -f "$rotated" 2>/dev/null
        return 0
    fi

    # 世代数超過分を mtime 古い順に削除。
    if [[ "$keep" -gt 0 ]]; then
        local prefix
        prefix="$(basename "$log_path")"
        local dir
        dir="$(dirname "$log_path")"
        # ls -1t は新しい順。tail -n +$((keep+1)) で世代外を抽出。
        local victim
        # shellcheck disable=SC2012
        ls -1t "$dir"/"${prefix}".*.gz 2>/dev/null | tail -n +$((keep + 1)) | while IFS= read -r victim; do
            [[ -n "$victim" ]] && rm -f "$victim"
        done
    fi
    return 0
}
