---
name: notion-run
description: Notion MCPツール（ページ・データベース操作）を実行する。公式MCP Python SDK経由で検索・取得・作成・更新を行い結果を返す。Notion URL から議事録用に本文 Markdown を取得する用途も含む。
context: fork
effort: low
---

# Notion MCPツール実行

## 入力

$ARGUMENTS

## 前提

- Python 3.10 以上
- `mcp` と `httpx` パッケージ（初回は `pip3 install mcp httpx` で導入）
- `/notion-login` でログイン済みであること

## 手順

### 1. ツール一覧確認（必要な場合）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py tools
```

利用可能なツールはサーバー側の更新で変動するため、ツール名・引数は **必ず `tools` で確認** してから呼ぶこと。2026 年 5 月時点の代表例:

- `notion-search` — ページ・データソースのセマンティック検索（Slack / GitHub / Jira 等の接続先も対象になり得る）
- `notion-fetch` — URL または ID からページ・データベース・データソースを取得（議事録は `id="https://www.notion.so/..."` で Markdown 取得）
- `notion-create-pages` / `notion-update-page` / `notion-move-pages` / `notion-duplicate-page` — ページ操作
- `notion-create-database` / `notion-update-data-source` — データベース／データソース操作
- `notion-create-comment` / `notion-get-comments` — コメント操作
- `notion-get-teams` — ワークスペース内のチーム一覧

### 2. コマンドを実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py call <tool_name> --arg key=value
```

**複数アカウントが登録されている場合**: 既定では `default.txt` のアカウントを使う。明示切替は `--account <slug or email>` を `call` の前に置く:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py --account user@example.com call <tool_name> ...
```

`--account` 未指定でデフォルト未設定かつアカウントが複数登録されている場合、対話プロンプトで選択を求める（TTY 必須）。サブエージェント等の非 TTY 環境では `--account` または事前の `set-default` を必ず指定する。

### 3. 出力の解析

結果を要約し、重要な情報を抽出する。全データを羅列せず、主要なフィールドを重点的に報告する。

ただし **議事録用途（呼び出し元から「本文を返して」と指示があった場合）は要約せず原文を返す** こと。

## コマンドオプション

- `--arg key=value` - ツール引数（複数指定可）

`--arg` の値は自動的に型変換される:
- `true` / `false` → bool
- 数値文字列 → int / float
- JSON文字列 → パース結果
- その他 → 文字列

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドとツール名
- 結果の要約（ページ一覧、ページ内容等）
- 議事録用途の場合は本文 Markdown をそのまま返す

## サブエージェント

メインコンテキストの消費を抑えるため、`notion-runner` サブエージェントに委任して実行できる。

## 注意事項

- 初回利用時は `login` でOAuth 2.1認証が必要（ブラウザが開く）
- 認証トークンとクライアント情報は `~/.config/notion-mcp/<account_key>/` 配下にアカウント単位でキャッシュされる（`account_key` は認証ユーザーの email から生成された slug）
- トークン期限切れ時は公式SDKが refresh_token で自動更新する
- データアクセスは Notion ワークスペース上で **ユーザーが許可したページ／データベース** に限られる（ワークスペース全体ではない）
- 複数アカウントの管理コマンド: `accounts` / `set-default <key>` / `logout <key>` / `refresh-meta`（meta.json のみ再取得、再認証不要）
