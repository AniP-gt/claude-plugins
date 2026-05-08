---
name: claude-mem-troubleshooting
description: claude-memのトラブルシューティング。Chromaサーバー接続エラーやGemini API問題の解決手順。
user-invocable: false
---

# claude-mem トラブルシューティング

## Chromaサーバーが停止している

Chromaサーバー（localhost:8000）が停止している場合、セマンティック検索が機能しない。

### 確認方法

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v2/heartbeat
# 200: 正常 / 000: 停止中
```

### 起動方法（Python版chromadb）

```bash
# chromadbが未インストールの場合
uv pip install --system chromadb

# Chromaサーバーの起動
chroma run --path ~/.claude-mem/vector-db --host 127.0.0.1 --port 8000
```

### npm版での自動起動（代替）

Workerは起動時にChromaを自動起動しようとするが、`chromadb` npmパッケージが未インストールの場合は失敗する。

```bash
cd ~/.claude/plugins/cache/thedotmack/claude-mem/<VERSION>/
bun add chromadb
```

npmパッケージが大容量DB（数百MB以上）でハングする場合は、上記のPython版を使用すること。

## Gemini API バージョンの既知の問題

Gemini 3系モデル（`gemini-3-flash`, `gemini-3-flash-preview`）を使用すると404エラーになる。

**原因**: `worker-service.cjs` のGemini APIエンドポイントが `v1` にハードコードされているが、Gemini 3系は `v1beta` でのみ利用可能。

**修正方法**: `worker-service.cjs` 内のエンドポイントを修正する:

```bash
# 修正（v1 → v1beta）
cd ~/.claude/plugins/cache/thedotmack/claude-mem/<VERSION>/scripts/
sed -i '' 's|generativelanguage.googleapis.com/v1/models|generativelanguage.googleapis.com/v1beta/models|' worker-service.cjs
```

修正後はworkerの再起動が必要。プラグインの更新で上書きされる点に注意。

参照: https://github.com/thedotmack/claude-mem/issues/1148

## OpenCode MCP 起動エラー

OpenCode で `claude-mem:mcp-search` が `mcp server not found` になる場合は、同梱の OpenCode 用ランチャーで upstream MCP サーバーを解決できるか確認する。

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/opencode-mcp-launcher.cjs" --print-path
```

自動探索で見つからない場合は、upstream `thedotmack/claude-mem` の `scripts/mcp-server.cjs` を指す環境変数を設定する。

```bash
export CLAUDE_MEM_MCP_SERVER_PATH="$HOME/.claude/plugins/cache/thedotmack/claude-mem/<VERSION>/scripts/mcp-server.cjs"
```

または plugin root を指定する。

```bash
export CLAUDE_MEM_UPSTREAM_PLUGIN_ROOT="$HOME/.claude/plugins/cache/thedotmack/claude-mem/<VERSION>"
```
