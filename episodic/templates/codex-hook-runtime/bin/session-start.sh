#!/usr/bin/env bash
# SessionStart: SMB 共有のマウントを試み、続いて staging を正規パスへ移送する。
# 失敗してもセッション開始を妨げない（常に exit 0）。
#
# 旧設計では LaunchAgent (com.user.mount-memory) が起動時にマウントを担っていたが、
# プラグイン構成変更でパスが乖離したため、SessionStart で都度マウント試行する設計に統一する。
# mount-memory-share.sh は既マウント時は何もせず exit 0 のため、頻発呼び出しでも安全。
BIN_DIR="$(cd "$(dirname "$0")" && pwd)"

# マウント試行（失敗してもログだけ残して後続へ。sync-pending 側がマウント未確立を検知して skip する）
"${BIN_DIR}/mount-memory-share.sh" || true

exec "${BIN_DIR}/sync-pending.sh"
