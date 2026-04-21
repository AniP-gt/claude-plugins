---
name: atlassian-run
description: Atlassian MCPツール（Jira・Confluence）を実行する。公式MCP Python SDK経由でイシュー検索・作成・更新、ページ検索・取得などを行い結果を返す。
context: fork
---

# Atlassian MCPツール実行

## 入力

$ARGUMENTS

## 前提

- Python 3.10 以上
- `mcp` と `httpx` パッケージ（初回は `pip3 install mcp httpx` で導入）
- `/atlassian-login` でログイン済みであること

## 手順

### 1. ツール一覧確認（必要な場合）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/atlassian_cli.py tools
```

### 2. コマンドを実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/atlassian_cli.py call <tool_name> --arg key=value
```

### 3. 出力の解析

結果を要約し、重要な情報を抽出する。全データを羅列せず、主要なフィールドを重点的に報告する。

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
- 結果の要約（イシュー一覧、ページ内容等）

## サブエージェント

メインコンテキストの消費を抑えるため、`atlassian-runner` サブエージェントに委任して実行できる。

## 注意事項

- 初回利用時は `login` でOAuth 2.1認証が必要（ブラウザが開く）
- 認証トークンとクライアント情報は `~/.config/atlassian-mcp/` にキャッシュされる
- トークン期限切れ時は公式SDKが refresh_token で自動更新する
- データアクセスはAtlassian Cloud上のユーザー権限に従う
