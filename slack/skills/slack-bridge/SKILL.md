---
name: slack-bridge
description: 登録済み Slack workspace を使って Slack MCP tool を実行する skill。`~/.config/slack/bin/slack-mcp call` 方式で、検索・チャンネル履歴・スレッド取得・送信を行う。「Slack を検索」「Slack の permalink を読んで」「Slack チャンネル履歴を見て」等で起動する。
argument-hint: <request> [--workspace <workspace_key>]
---

# Slack Bridge

登録済み Slack workspace を選び、`~/.config/slack/bin/slack-mcp call` で Slack MCP tool を実行する。ブラウザや Slack アプリを操作せず、MCP 経由だけで取得する。

## 目的

- Slack permalink や検索要求から workspace、channel ID、message ts、操作 tool を決める
- `~/.config/slack/bin/slack-mcp call` で Slack MCP tool を実行する
- 結果を workspace ごとに分けて要約する

## 制約

- `slack-core` を必ず参照する
- `computer-use` やブラウザ操作を使わない
- 未ログインの場合は `slack-connect` の実行を案内する
- `~/.config/slack/bin/slack-mcp` がなければ先に `slack-setup` を実行する
- token、Authorization header、`tokens.json` の内容を表示しない
- 送信系 tool はユーザーの明示承認なしに実行しない

## 完了条件

- Slack MCP から取得した結果を workspace / channel / timestamp 付きで報告している
- 未取得の場合は、未ログイン・権限不足・tool 引数不一致のどれかまで切り分けている

## 入力パラメータ

| 引数 | 必須 | 説明 |
|---|---|---|
| `<request>` | ✓ | Slack で実行したい検索・取得・送信内容 |
| `--workspace` | | 使用する workspace key |

---

## Phase 1: 対象解析

### 目的

ユーザー要求から workspace、channel ID、message ts、tool を決める。

### 制約

- Slack permalink は正規表現で解析する
- permalink の workspace subdomain と saved workspace key は同一とは限らないため、`workspaces` で確認する

### 完了条件

- 実行する CLI コマンド案が決まっている

#### Step 1: workspace 一覧確認

```bash
~/.config/slack/bin/slack-mcp workspaces
```

未ログインなら停止し、`slack-connect` を案内する。

#### Step 2: URL 解析

Slack URL から以下を抽出する。

```text
workspace_subdomain
channel_id
message_ts
```

`p1778331409115449` は `1778331409.115449` に変換する。

#### Step 3: tool 選択

単一 permalink の内容確認は `slack_read_channel` を優先する。

```bash
~/.config/slack/bin/slack-mcp --workspace <workspace_key> call slack_read_channel --arg channel_id=<channel_id> --arg oldest=<ts> --arg latest=<ts> --arg limit=5
```

スレッド返信が必要なら `slack_read_thread` を使う。

```bash
~/.config/slack/bin/slack-mcp --workspace <workspace_key> call slack_read_thread --arg channel_id=<channel_id> --arg message_ts=<ts> --arg limit=20
```

---

## Phase 2: MCP 実行

### 目的

Slack MCP tool を CLI 経由で実行し、必要な情報を取得する。

### 制約

- tool 名・引数が不明な場合は先に `tools` を実行する
- 複数 workspace は個別に実行し、結果を混ぜない
- エラー時は再試行前に原因を読む

### 完了条件

- 対象 tool の結果または具体的な失敗理由が得られている

#### Step 1: 最新 tool 一覧確認

必要時のみ実行する。

```bash
~/.config/slack/bin/slack-mcp --workspace <workspace_key> tools
```

#### Step 2: tool 実行

Phase 1 で決めた `call` コマンドを実行する。

#### Step 3: 追加取得

結果が permalink の親メッセージだけなら `slack_read_thread`、検索結果だけなら `slack_read_channel` で本文を補う。

---

## Phase 3: 結果報告

### 目的

Slack MCP 結果をユーザーが判断できる粒度に整理する。

### 制約

- workspace / channel ID / timestamp を明記する
- token や内部保存先の secret は出さない
- Slack 本文は必要最小限に引用し、長文は要約する

### 完了条件

- 各 Slack URL の内容、関連リンク、エラー種別、次アクションが分かる
