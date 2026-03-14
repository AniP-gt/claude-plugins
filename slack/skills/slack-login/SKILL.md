---
name: slack-login
description: Slack MCPへのOAuth認証手順。ブラウザでSlackワークスペースを認証し、トークンを保存する。
---

# Slack MCP ログイン

## 入力

$ARGUMENTS

## 手順

### 1. ログイン実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py login
```

**通常環境:** ブラウザが自動で開きます。ユーザーにSlackワークスペースの認証を依頼してください。

**ヘッドレス環境（Docker等）:** 2ステップで認証します:

```bash
# ステップ1: 認証URLを取得（即終了）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py login --url-only
```

出力されたURLをユーザーにホスト側ブラウザで開くよう依頼してください。認証後、ブラウザのアドレスバーに `localhost:3118/callback?code=...` のURLが表示されます。

```bash
# ステップ2: コールバックURLでトークン取得（即終了）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py login --code "http://localhost:3118/callback?code=...&state=..."
```

### 2. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py workspaces
```

ワークスペース名とデフォルト設定が表示されれば認証完了。

### 3. 複数ワークスペース（オプション）

追加ワークスペースが必要な場合は `login` を再実行。デフォルトの切り替え:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py set-default <workspace_key>
```

### ワークスペース管理コマンド

```bash
# ワークスペースのトークン削除
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py logout <workspace_key>

# 保存済みワークスペース一覧
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py workspaces

# デフォルトワークスペース変更
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py set-default <workspace_key>
```

## トークン管理

- 保存先: `~/.config/slack-mcp/workspaces.json` (パーミッション 0600)
- トークン有効期限: 12時間
- 有効期限5分前に自動リフレッシュ
- リフレッシュに失敗した場合は `login` を再実行

## 出力

認証結果を報告する:
- ワークスペース名とID
- デフォルト設定の状態
