---
name: slack-troubleshooting
description: Slack MCPの既知の問題と対処法のリファレンス。
user-invocable: false
---

# Slack MCP トラブルシューティング

| 症状 | 対処 |
|---|---|
| `ワークスペースが未設定です` | `login` でワークスペースを追加 |
| `ヘッドレス環境を検出しました` | デスクトップ環境（macOS / OrbStack Linux VM / Wayland or X11 付きLinux）で `login` を実行 |
| `ModuleNotFoundError: No module named 'mcp'` / `httpx` | `pip3 install 'mcp>=1.13' httpx` を実行 |
| `RuntimeError: Unsupported protocol version from the server: 2025-06-18` | mcp SDK が古い。`pip3 install -U 'mcp>=1.13'` で更新 |
| 自動リフレッシュ後も 401 が返る | `logout <workspace_key>` → `login` で再認証 |
| `auth.test failed: ...` | トークンがスコープ不足または無効化されている。`logout` → `login` で再認証 |
| `State parameter mismatch` | 別の認証フローが並走している可能性。`_pending` が残っていれば `rm -rf ~/.config/slack-mcp/_pending` してから再試行 |
| `MCP Error [...]` | ツール名・引数を確認。`tools` で利用可能なツール一覧を確認 |
| ポート3118が使用中 | `login` 実行前に他のSlack MCP認証プロセスを終了（`lsof -i :3118`） |
| `ワークスペースが見つかりません: <key>` | `workspaces` でキーを確認。部分一致検索にも対応 |
