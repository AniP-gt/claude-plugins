---
name: slack-login
description: Slack MCPへのOAuth認証手順。公式MCP Python SDKでブラウザ認証し、ワークスペース毎にトークンを保存する。
---

# Slack MCP ログイン

## 前提条件

- Python 3.10 以上
- `pip3 install 'mcp>=1.13' httpx`
  （Slack MCP サーバーがプロトコル `2025-06-18` を返すため、それ以前の mcp SDK ではハンドシェイクが失敗する）
- デスクトップ環境（ヘッドレス/コンテナでは実行不可）
- **v0.5.0 で保存形式が破壊的に変更**されました。v0.4.x からアップデートした場合は初回に再ログインが必要です（旧 `~/.config/slack-mcp/workspaces.json` は新実装では無視されます）。

## 入力

$ARGUMENTS

## 手順

### 1. ログイン実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py login
```

- ブラウザが自動で開き Slack の認証画面に遷移する
- ユーザーがワークスペースを選択して「許可」を押すと `http://localhost:3118/callback` 経由でトークンが自動保存される
- 認証URLはターミナル/チャットに提示しない（ユーザーのブラウザ操作で完結）

### 2. ログイン結果の確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py workspaces
```

ワークスペース名とデフォルト設定が表示されれば認証完了。

### 3. 複数ワークスペース（任意）

追加ワークスペースが必要な場合は `login` を再実行。デフォルトの切り替え:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py set-default <workspace_key>
```

### ワークスペース管理コマンド

```bash
# 保存済みワークスペース一覧
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py workspaces

# デフォルトワークスペース変更
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py set-default <workspace_key>

# ワークスペースのトークン削除
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py logout <workspace_key>
```

## トークン管理

- 保存先: `~/.config/slack-mcp/<workspace_key>/` 配下 (ディレクトリ 0700、ファイル 0600)
  - `tokens.json` — アクセス/リフレッシュトークン
  - `client_info.json` — 固定 CLIENT_ID の OAuth クライアント情報
  - `meta.json` — team_id / team_name / scope
- `~/.config/slack-mcp/default.txt` — デフォルトワークスペースキー
- トークン有効期限: 12時間 → 有効期限を過ぎると公式SDKが自動リフレッシュ
- リフレッシュに失敗した場合は `login` を再実行

## 出力

認証結果を報告する:
- ワークスペース名と team_id
- 保存されたワークスペースキー
- デフォルト設定の状態
