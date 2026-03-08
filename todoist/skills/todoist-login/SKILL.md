---
name: todoist-login
description: Todoist MCPへのOAuth認証手順。ブラウザでTodoistアカウントを認証し、トークンを保存する。
---

# Todoist MCP ログイン

## 入力

$ARGUMENTS

## 手順

### 1. ログイン実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py login
```

**ブラウザが開きます。ユーザーにTodoistアカウントの認証を依頼してください。**

スクリプトがブラウザを起動し、Todoistの認証ページを表示します。ユーザーが認証を完了すると、トークンが自動保存されます。初回はクライアント登録も自動で実行されます。

### 2. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py status
```

「Status: Authenticated」と表示されれば認証完了。

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- スコープ情報
