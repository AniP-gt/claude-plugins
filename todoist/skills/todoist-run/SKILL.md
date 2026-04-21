---
name: todoist-run
description: Todoist MCPツールを実行する。公式MCP Python SDK経由でタスク管理・プロジェクト操作等を行う。
context: fork
---

# Todoist MCPツール実行

## 入力

$ARGUMENTS

## 手順

### 1. ツール一覧確認（必要な場合）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py tools
```

### 2. コマンドを実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py call <tool_name> --arg key=value
```

引数は `--arg` で複数指定可能:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py call add-tasks --arg tasks='[{"content":"Buy groceries","due_string":"tomorrow"}]'
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

## ツール一覧

| ツール名 | 説明 | 主要引数 |
|---|---|---|
| `user-info` | ユーザー情報・タイムゾーン・目標進捗 | - |
| `get-overview` | プロジェクト概要（全体 or 特定） | `projectId` |
| `find-tasks` | タスク検索 | `searchText`, `projectId`, `labels` |
| `find-tasks-by-date` | 日付範囲でタスク取得 | `startDate`, `daysCount` |
| `find-completed-tasks` | 完了済みタスク取得 | `since`*, `until`* |
| `add-tasks` | タスク追加 | `tasks`* |
| `update-tasks` | タスク更新 | `tasks`* |
| `complete-tasks` | タスク完了 | `ids`* |
| `delete-object` | オブジェクト削除 | `type`*, `id`* |
| `fetch-object` | オブジェクト詳細取得 | `type`*, `id`* |
| `add-comments` | コメント追加 | `comments`* |
| `find-comments` | コメント取得 | `taskId`/`projectId`/`commentId` |
| `update-comments` | コメント更新 | `comments`* |
| `add-projects` | プロジェクト追加 | `projects`* |
| `update-projects` | プロジェクト更新 | `projects`* |
| `find-projects` | プロジェクト検索 | `search` |
| `project-management` | プロジェクトアーカイブ/復元 | `action`*, `projectId`* |
| `project-move` | プロジェクト移動 | `action`*, `projectId`* |
| `add-sections` | セクション追加 | `sections`* |
| `update-sections` | セクション更新 | `sections`* |
| `find-sections` | セクション検索 | `projectId`*, `search` |
| `find-activity` | アクティビティログ取得 | `objectType`, `eventType` |
| `manage-assignments` | タスク割り当て管理 | `operation`*, `taskIds`* |
| `find-project-collaborators` | コラボレーター検索 | `projectId`* |
| `list-workspaces` | ワークスペース一覧 | - |
| `search` | タスク・プロジェクト横断検索 | `query`* |
| `fetch` | ID指定で詳細取得 | `id`* (format: `task:{id}`) |

**注意**: ツール一覧はサーバー側で変更される可能性があります。最新の一覧は `tools` サブコマンドで確認。

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドとツール名
- 結果の要約（タスク一覧、プロジェクト情報等）

## サブエージェント

メインコンテキストの消費を抑えるため、`todoist-runner` サブエージェントに委任して実行できる。

## 注意事項

- 初回利用時は `login` でOAuth 2.1認証が必要（ブラウザが開く）
- 認証トークンとクライアント情報は `~/.config/todoist-mcp/` にキャッシュされる
- トークン期限切れ時は公式SDKが refresh_token で自動更新する
- データアクセスはTodoistアカウント上のユーザー権限に従う
- 前提: Python 3.10+、`pip3 install mcp httpx`
