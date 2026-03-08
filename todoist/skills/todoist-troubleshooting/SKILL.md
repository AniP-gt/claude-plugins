---
name: todoist-troubleshooting
description: Todoist MCPの既知の問題と対処法のリファレンス。
user-invocable: false
---

# Todoist MCP トラブルシューティング

| 症状 | 対処 |
|---|---|
| `Not authenticated` | `login` で認証を実行 |
| `HTTP request failed` | ネットワーク接続を確認。`--debug` で詳細ログを出力 |
| `MCP Error` | ツール名・引数を確認。`tools` で利用可能なツール一覧を確認 |
| `Client registration failed` | ネットワーク接続を確認。再度 `login` を実行 |
| ポート3120が使用中 | `login` 実行前に他のTodoist MCP認証プロセスを終了 |
| `Invalid SSE format` | `--debug` で詳細を確認。セッションキャッシュをクリア: `rm /tmp/todoist_mcp_session.json` |
