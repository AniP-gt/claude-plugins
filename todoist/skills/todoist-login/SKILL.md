---
name: todoist-login
description: Todoist MCPへのOAuth 2.1認証手順。mcp-remote経由でブラウザ認証し、トークンを保存する。
---

# Todoist MCP ログイン

## 入力

$ARGUMENTS

## 手順

### 1. ログイン実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py login
```

ヘッドレス環境では、mcp-remoteが出力する認証URLが標準出力に表示される。

コマンド出力に認証URLが含まれる場合、そのURLを **省略せず全文** ユーザーに提示し、以下を依頼する:

1. このURLをブラウザで開いてTodoistアカウントで認証してください
2. 認証が完了するとmcp-remoteが自動でトークンを取得します

**ユーザーに認証URLを提示し、認証完了を待つこと。**

mcp-remoteがOAuth 2.1認証を処理し、トークンを `~/.mcp-auth/` に自動保存する。

### 2. ログイン確認

「Login successful!」と表示されれば認証完了。

### トラブルシューティング

認証エラーが発生した場合:

```bash
# 認証キャッシュをクリアして再認証
rm -rf ~/.mcp-auth/
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py login
```

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- サーバー情報
