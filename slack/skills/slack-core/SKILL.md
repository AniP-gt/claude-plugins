---
name: slack-core
description: Slack MCP 連携の共通リファレンス。公式 MCP Python SDK、固定 Slack CLIENT_ID、ワークスペース単位の OAuth token 保存、Slack MCP CLI の実行規約を定義する。slack-connect / slack-bridge から参照する。
user-invocable: false
---

# Slack Core

Slack MCP 連携の共通設計を定義する参照用 skill。過去の Slack plugin v0.5.0 の方式を踏襲し、公式 MCP Python SDK で `https://mcp.slack.com/mcp` に接続する。Codex / Claude / terminal では `~/.config/slack/bin/slack-mcp` を標準入口にする。

## 採用方式

Slack MCP は Dynamic Client Registration に対応しないため、Codex/Claude の HTTP MCP OAuth 直結では失敗する。過去実装と同じく、Slack の固定 `CLIENT_ID` を SDK の `client_info.json` に事前投入し、OAuth 2.0 PKCE public client として認証する。

CLI は以下を使う。`~/.config/slack/bin/slack-mcp` が存在しない場合は `slack-setup` を実行する。

```bash
~/.config/slack/bin/slack-mcp <command>
```

## 保存先

ワークスペース単位で保存する。

```text
~/.config/slack/<workspace_key>/tokens.json
~/.config/slack/<workspace_key>/client_info.json
~/.config/slack/<workspace_key>/meta.json
~/.config/slack/default.txt
~/.config/slack/bin/slack-mcp
```

保存ファイルは `0600`、ディレクトリは `0700` とする。`tokens.json` には access token と refresh token が含まれるため、会話・ログ・監査出力に出さない。

## ワークスペースキー

`slack_cli.py login` は Slack `auth.test` の `team` と `team_id` から `<team-name>-<team-id>` を作る。複数アカウント・複数ワークスペースは、この `workspace_key` を指定して使い分ける。

```bash
~/.config/slack/bin/slack-mcp workspaces
~/.config/slack/bin/slack-mcp set-default <workspace_key>
```

## 依存

Python 3.10 以上と以下の Python パッケージを使う。

```bash
pip3 install -U 'mcp>=1.13' httpx
```

Slack MCP サーバーは protocol `2025-06-18` を返すため、古い `mcp` SDK では接続できない。

## CLI コマンド

```bash
~/.config/slack/bin/slack-mcp login
~/.config/slack/bin/slack-mcp workspaces
~/.config/slack/bin/slack-mcp tools
~/.config/slack/bin/slack-mcp --workspace <workspace_key> call <tool_name> --arg key=value
~/.config/slack/bin/slack-mcp logout <workspace_key>
```

### `--arg key=value` の型解釈

- `true` / `false` は bool、整数リテラル（例: `limit=20`）は int に変換する
- 先頭が `"`, `[`, `{` の場合は JSON として解釈する（例: `meta={"k":1}`）
- 上記以外（小数点を含む数値・裸の文字列）はすべて string で送信する
- Slack ts（例: `message_ts=1776821335.819279`）は裸のまま渡してよい。float 化されず string で送信される

## 主要ツール

最新のツール一覧は `tools` で取得する。過去実装時点の代表例は以下。

| ツール名 | 用途 |
|---|---|
| `slack_search_public` | パブリックチャンネル検索 |
| `slack_search_public_and_private` | public/private/DM を含む検索 |
| `slack_search_channels` | チャンネル検索 |
| `slack_read_channel` | チャンネル履歴取得 |
| `slack_read_thread` | スレッド取得 |
| `slack_send_message` | メッセージ送信 |

## URL からの読み取り

Slack permalink は次の形を持つ。

```text
https://<workspace>.slack.com/archives/<channel_id>/p<timestamp>
```

`p1778331409115449` は Slack `ts` の `1778331409.115449` に変換する。単一メッセージの確認は `slack_read_channel` で `channel_id`、`oldest`、`latest` を指定する。スレッドが必要なら `slack_read_thread` に `message_ts` を渡す。

## 禁止事項

- `computer-use` やブラウザ操作で Slack を読むことは禁止する
- token、Authorization header、`tokens.json` の中身を表示しない
- 送信系ツールはユーザーの明示承認なしに実行しない
- `CLAUDE_PLUGIN_ROOT` に依存したコマンド例を標準手順にしない
