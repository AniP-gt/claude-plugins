#!/bin/bash
# プラグインファイルが変更されているのに plugin.json のバージョンが変わっていない場合にブロックする

# stdin から Bash ツールのコマンドを取得
COMMAND=$(python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except:
    pass
")

# git commit コマンド以外はスルー
if ! echo "$COMMAND" | grep -qE "git commit"; then
  exit 0
fi

# git diff の出力はリポジトリルート基準のパスなので、ルートに移動してから判定する
cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

# ステージ済みファイルを取得
STAGED=$(git diff --cached --name-only 2>/dev/null)
if [ -z "$STAGED" ]; then
  exit 0
fi

# .claude-plugin/ 以外のファイルが変更されているプラグインを列挙
CHANGED_PLUGINS=$(echo "$STAGED" \
  | grep -v "^\.claude-plugin/" \
  | grep -E "^[a-zA-Z][^/]+/" \
  | sed 's|/.*||' \
  | sort -u)

MISSING=""
for PLUGIN in $CHANGED_PLUGINS; do
  # plugin.json が存在するディレクトリだけが対象（プラグイン判定）
  if [ ! -f "$PLUGIN/.claude-plugin/plugin.json" ]; then
    continue
  fi

  # plugin.json がステージされていなければバージョン未更新とみなす
  if ! echo "$STAGED" | grep -qE "^$PLUGIN/\.claude-plugin/plugin\.json$"; then
    MISSING="$MISSING $PLUGIN"
  fi
done

if [ -n "$MISSING" ]; then
  echo "ERROR: 以下のプラグインのバージョンが更新されていません:" >&2
  for P in $MISSING; do
    echo "  - $P/.claude-plugin/plugin.json" >&2
  done
  echo "" >&2
  echo ".claude-plugin/marketplace.json も忘れずに同期してください。" >&2
  exit 2
fi

exit 0
