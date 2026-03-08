---
name: todoist-run
description: Todoist MCPツールを実行する。タスク管理・プロジェクト操作等を行い結果を返す。
context: fork
---

# Todoist MCP ツール実行

## 入力

$ARGUMENTS

## 手順

### 1. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py status
```

未認証の場合はメインエージェントに通知する（loginはユーザーのブラウザ操作が必要なため、このスキル内では実行しない）。

### 2. ツール実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py call <tool_name> --arg key=value
```

引数は `--arg` で複数指定可能:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py call add-tasks --arg tasks='[{"content":"Buy groceries","due_string":"tomorrow"}]'
```

### ツール一覧

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

**注意**: ツール一覧はサーバー側で変更される可能性があります。最新の一覧は以下で確認:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/todoist_cli.py tools
```

### コマンドオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--debug` | デバッグログを出力 | off |

## サブエージェント

メインコンテキストの消費を抑えるため、`todoist-runner` サブエージェントに委任して実行できる。

## 出力

取得した情報を以下の形式で返す:
- 実行したツール名とパラメータ
- 取得結果の要約
- 必要に応じて生データ
