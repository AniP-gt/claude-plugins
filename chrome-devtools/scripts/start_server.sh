#!/bin/bash
# Chrome DevTools MCP Server を mcp-proxy 経由で HTTPモードで起動
# 自動的に空きポートを探し、JSON形式でポート情報を返す

AVAILABLE_PORTS=(8941 8942 8943)

# プロジェクト単位でPIDを管理（1プロジェクト=1 Chrome DevToolsインスタンス）
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PID_DIR="${PROJECT_DIR}/tmp/chrome-devtools"
mkdir -p "$PID_DIR"

# 空きポートを探す
SELECTED_PORT=""
for PORT in "${AVAILABLE_PORTS[@]}"; do
    if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        SELECTED_PORT=$PORT
        break
    fi
done

# 全て使用中の場合は8941を停止して再利用
if [ -z "$SELECTED_PORT" ]; then
    PID=$(lsof -ti :8941)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null
        sleep 1
    fi
    SELECTED_PORT=8941
    STATUS="reused"
else
    STATUS="started"
fi

# ログファイルにリダイレクト
LOG_FILE="/tmp/chrome_devtools_${SELECTED_PORT}.log"
echo "Starting Chrome DevTools MCP Server on port $SELECTED_PORT..." > "$LOG_FILE"
echo "Press Ctrl+C to stop" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
echo "Server URL: http://localhost:$SELECTED_PORT/mcp" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# mcp-proxy経由でchrome-devtools-mcpをHTTPモードで起動
# --isolated: 独立したブラウザプロファイル
# --no-usage-statistics: 使用統計を無効化
npx mcp-proxy@6.4.2 --port "$SELECTED_PORT" -- npx -y chrome-devtools-mcp@0.20.0 --isolated --no-usage-statistics >> "$LOG_FILE" 2>&1 &
echo $! > "${PID_DIR}/server.pid"
echo "$SELECTED_PORT" > "${PID_DIR}/server.port"

# サーバーが起動するまで待機（2段階npxのため長めに設定）
for i in {1..30}; do
    if lsof -Pi :$SELECTED_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# JSON形式で情報を出力
echo "{\"port\": $SELECTED_PORT, \"url\": \"http://localhost:$SELECTED_PORT/mcp\", \"status\": \"$STATUS\"}"
