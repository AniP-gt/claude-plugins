---
name: slack-run
description: Slack MCPツールを実行する。メッセージ検索・送信・チャンネル読み取り等の操作を行い結果を返す。
context: fork
---

# Slack MCP ツール実行

## 前提条件

- Python 3.10 以上 と `pip3 install 'mcp>=1.13' httpx`
- `slack-login` で認証済みのワークスペースが 1 つ以上存在すること

## 入力

$ARGUMENTS

## 手順

### 1. ワークスペース確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py workspaces
```

未ログインの場合はメインエージェントに通知する（loginはユーザーのブラウザ操作が必要なため、このスキル内では実行しない）。

### 2. ツール実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py call <tool_name> --arg key=value
```

引数は `--arg` で複数指定可能:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py call slack_search_public --arg query="キーワード" --arg limit=5
```

### ツール一覧

| ツール名 | 説明 | 主要引数 |
|---|---|---|
| `slack_send_message` | メッセージ送信 | `channel_id`*, `message`*, `thread_ts` |
| `slack_schedule_message` | メッセージ予約送信 | `channel_id`*, `message`*, `post_at`* |
| `slack_send_message_draft` | 下書き作成 | `channel_id`*, `message`*, `thread_ts` |
| `slack_search_public` | パブリックチャンネル検索 | `query`*, `limit`, `sort`, `sort_dir` |
| `slack_search_public_and_private` | 全チャンネル検索（DM含む） | `query`*, `channel_types`, `limit` |
| `slack_search_channels` | チャンネル名・説明で検索 | `query`*, `channel_types`, `limit` |
| `slack_search_users` | ユーザー検索 | `query`*, `limit` |
| `slack_read_channel` | チャンネルメッセージ読み取り | `channel_id`*, `limit`, `oldest`, `latest` |
| `slack_read_thread` | スレッド返信取得 | `channel_id`*, `message_ts`*, `limit` |
| `slack_read_canvas` | Canvas読み取り | `canvas_id`* |
| `slack_create_canvas` | Canvas作成 | `title`*, `content`* |
| `slack_read_user_profile` | ユーザープロフィール取得 | `user_id` |

**注意**: ツール一覧はサーバー側で変更される可能性があります。最新の一覧は以下で確認:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py tools
```

### コマンドオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--workspace` | ワークスペースキー | `~/.config/slack-mcp/default.txt` のキー |

ワークスペース指定例:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py --workspace <workspace_key> call <tool_name> --arg key=value
```

## トークン保存先

- `~/.config/slack-mcp/<workspace_key>/tokens.json` (0600)
- 有効期限切れ時は公式 MCP Python SDK が自動リフレッシュ

## サブエージェント

メインコンテキストの消費を抑えるため、`slack-runner` サブエージェントに委任して実行できる。

## 出力

取得した情報を以下の形式で返す:
- 実行したツール名とパラメータ
- 取得結果の要約
- 必要に応じて生データ
