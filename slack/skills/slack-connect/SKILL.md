---
name: slack-connect
description: Slack MCP 用の初回接続 skill。`~/.config/slack/bin/slack-mcp login` で公式 MCP Python SDK による OAuth 認証を実行し、ワークスペース単位で token を保存する。「Slack を接続」「Slack MCP の初回登録」等で起動する。
argument-hint: [login|workspaces|set-default <workspace_key>|logout <workspace_key>]
---

# Slack Connect

Slack MCP を使うための認証・ワークスペース管理を行う。実装は `slack-core` の規約に従い、`~/.config/slack/bin/slack-mcp` を使う。

## 目的

- Slack MCP への OAuth 2.0 PKCE 認証を実行する
- `~/.config/slack/<workspace_key>/` に token と client 情報を保存する
- 複数ワークスペースを `workspace_key` で切り替えられる状態にする

## 制約

- `slack-core` を必ず参照する
- 認証 URL、token、`tokens.json` の内容を会話に出さない
- `computer-use` やブラウザ自動操作を使わない
- ブラウザ操作が必要な場合は `~/.config/slack/bin/slack-mcp login` に任せる
- `~/.config/slack/bin/slack-mcp` がなければ先に `slack-setup` を実行する
- 既存 token の中身は読まず、存在確認と CLI コマンドの結果だけを見る

## 完了条件

- `workspaces` で対象ワークスペースが表示される
- 必要に応じて default workspace が設定される
- 未認証・依存不足・ヘッドレス環境のいずれかなら原因と次手を報告する

---

## Phase 1: 事前確認

### 目的

既存認証と依存を確認し、ログインが必要か判定する。

### 制約

- token ファイルの内容を表示しない
- `pip install` が必要な場合はユーザー承認を取る

### 完了条件

- 既存 workspace の有無と依存状態が分かっている

#### Step 1: slack-core の確認

`slack-core` を読み、保存先、CLI、禁止事項を確認する。

#### Step 2: workspace 一覧の確認

```bash
~/.config/slack/bin/slack-mcp workspaces
```

未ログインなら Phase 2 に進む。表示された場合は、必要な workspace があるか確認する。

#### Step 3: 依存確認

`ModuleNotFoundError` または protocol version error が出た場合は以下を実行する。

```bash
pip3 install -U 'mcp>=1.13' httpx
```

---

## Phase 2: OAuth ログイン

### 目的

Slack OAuth を完了し、ワークスペース単位で token を保存する。

### 制約

- ログインは `~/.config/slack/bin/slack-mcp login` のみで実行する
- 認証フローをブラウザ自動操作で代替しない
- 複数ワークスペースが必要な場合は `login` を必要回数実行する

### 完了条件

- `workspaces` で新規 workspace が確認できる

#### Step 1: ログイン実行

```bash
~/.config/slack/bin/slack-mcp login
```

CLI がブラウザを開く。ユーザーが Slack 側で対象ワークスペースを選択し、許可する。

#### Step 2: 登録確認

```bash
~/.config/slack/bin/slack-mcp workspaces
```

対象 workspace key、team name、team id を確認する。

#### Step 3: default 設定

必要に応じて default workspace を設定する。

```bash
~/.config/slack/bin/slack-mcp set-default <workspace_key>
```
