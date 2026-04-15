#!/bin/bash
# Ollama 起動・停止ヘルパー
#
# 使い方:
#   ollama.sh start   → Ollamaが未起動なら起動し、PIDファイルを記録
#   ollama.sh stop    → このスクリプトが起動したOllamaだけ停止
#
# EMBEDDING_PROVIDER=ollama のときだけ実際に動作する。
# 他プロバイダーのときはno-opとして終了する。

set -euo pipefail

PIDFILE="${TMPDIR:-/tmp}/cocoindex_ollama.pid"
ACTION="${1:-}"

# ollama プロバイダー以外はno-op
PROVIDER="${EMBEDDING_PROVIDER:-voyage}"
if [[ "$PROVIDER" != "ollama" ]]; then
  exit 0
fi

case "$ACTION" in
  start)
    # 既にOllamaが起動中か確認
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
      echo "Ollama: already running (not managed)"
      # 管理対象外なのでPIDファイルは作らない
      exit 0
    fi

    echo "Ollama: starting..."
    ollama serve > "${TMPDIR:-/tmp}/ollama.log" 2>&1 &
    OLLAMA_PID=$!
    echo "$OLLAMA_PID" > "$PIDFILE"

    # 起動待ち（最大10秒）
    for i in $(seq 1 20); do
      if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama: started (PID=$OLLAMA_PID)"
        exit 0
      fi
      sleep 0.5
    done

    echo "Ollama: failed to start (timeout)" >&2
    rm -f "$PIDFILE"
    exit 1
    ;;

  stop)
    if [[ ! -f "$PIDFILE" ]]; then
      # このスクリプトが起動していないので何もしない
      exit 0
    fi

    OLLAMA_PID=$(cat "$PIDFILE")
    rm -f "$PIDFILE"

    if kill -0 "$OLLAMA_PID" 2>/dev/null; then
      kill "$OLLAMA_PID"
      echo "Ollama: stopped (PID=$OLLAMA_PID)"
    fi
    ;;

  *)
    echo "Usage: ollama.sh start|stop" >&2
    exit 1
    ;;
esac
