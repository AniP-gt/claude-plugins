---
name: ticktick-run
description: TickTick APIを実行する。タスク管理・プロジェクト操作等を行い結果を返す。
context: fork
---

# TickTick API 実行

## 入力

$ARGUMENTS

## 手順

### 1. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py status
```

未認証の場合はメインエージェントに通知する（loginはユーザーのブラウザ操作が必要なため、このスキル内では実行しない）。

### 2. 操作実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py call <operation> --arg key=value
```

引数は `--arg` で複数指定可能:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py call create-task \
  --arg title="Buy groceries" \
  --arg projectId="<id>" \
  --arg dueDate="2026-04-20T12:00:00+0900" \
  --arg priority=3
```

### 操作一覧

#### プロジェクト操作

| 操作名 | 説明 | 主要引数 |
|---|---|---|
| `get-projects` | 全プロジェクト一覧 | - |
| `get-project` | プロジェクト詳細 | `projectId`* |
| `get-project-data` | プロジェクト＋タスク一覧 | `projectId`* |
| `create-project` | プロジェクト作成 | `name`*, `color`, `viewMode`, `kind` |
| `update-project` | プロジェクト更新 | `projectId`*, `name`, `color` |
| `delete-project` | プロジェクト削除 | `projectId`* |

#### タスク操作

| 操作名 | 説明 | 主要引数 |
|---|---|---|
| `get-task` | タスク取得 | `projectId`*, `taskId`* |
| `create-task` | タスク作成 | `title`*, `projectId`, `content`, `dueDate`, `priority`, `tags`, `isAllDay` |
| `update-task` | タスク更新 | `taskId`*, 更新フィールド |
| `complete-task` | タスク完了 | `projectId`*, `taskId`* |
| `delete-task` | タスク削除 | `projectId`*, `taskId`* |
| `batch-tasks` | バッチ操作 | `add`, `update`, `delete` |

**タスク優先度**: `0`=なし, `1`=低, `3`=中, `5`=高

**日時フォーマット**: ISO 8601 (`2026-04-20T12:00:00+0900`)

### コマンドオプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--debug` | デバッグログを出力 | off |

## サブエージェント

メインコンテキストの消費を抑えるため、`ticktick-runner` サブエージェントに委任して実行できる。

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドと操作内容
- 取得結果の要約
- 必要に応じて生データ
