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

**通常環境:** ブラウザが自動で開きます。ユーザーにTodoistアカウントの認証を依頼してください。

**ヘッドレス環境（Docker等）:** 2ステップで認証します:

```bash
# ステップ1: 認証URLを取得（即終了）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py login --url-only
```

出力されたURLをユーザーにホスト側ブラウザで開くよう依頼してください。認証後、ブラウザのアドレスバーに `localhost:3120/callback?code=...` のURLが表示されます。

```bash
# ステップ2: コールバックURLでトークン取得（即終了）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py login --code "http://localhost:3120/callback?code=...&state=..."
```

初回はクライアント登録も自動で実行されます。

### 2. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py status
```

「Status: Authenticated」と表示されれば認証完了。

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- スコープ情報
