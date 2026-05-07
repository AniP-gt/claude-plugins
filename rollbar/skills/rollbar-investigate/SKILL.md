---
name: rollbar-investigate
description: Rollbarエラートラッキングの調査を実行。URLやアイテム番号からエラー詳細を取得し、トップエラーやデプロイ履歴を確認する。
context: fork
effort: low
---

# Rollbar 調査手順

委任メッセージまたはユーザーの指示から調査対象・目的を把握し、Rollbar のエラートラッキングデータを取得する。

## 前提条件

- 環境変数 `ROLLBAR_ACCESS_TOKEN`（Project Access Token、`read` スコープ）が設定済みであること
- `update` コマンドを使う場合は `write` スコープが必要

## ワークフロー

1. **調査目的を判定**:
   - URL が指定されている → `url` コマンドでアイテム詳細を取得
   - アイテム番号が指定されている → `item` コマンドで詳細を取得
   - エラー傾向の調査 → `top` コマンドでトップエラーを確認
   - その他 → 下記コマンド一覧から適切なコマンドを選択
2. **コマンド実行**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py <subcommand> [options]`
3. **結果の解析と報告**

## コマンド一覧

| コマンド | 説明 |
|---|---|
| `url <rollbar_url>` | Rollbar の URL からアイテム詳細を取得 |
| `item <number>` | アイテム番号から詳細を取得 |
| `top` | 過去24時間のトップエラーを取得 |
| `list` | アイテム一覧（`--status`, `--env`, `--query` でフィルタ可） |
| `deploys` | デプロイ履歴を取得 |
| `version <version>` | バージョン詳細を取得（`--env` でフィルタ可） |
| `update <number>` | アイテムのステータス等を更新（`write` スコープ必須） |

## 使用例

```bash
# URL からアイテム詳細を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py url "https://app.rollbar.com/a/org/fix/item/project/4906"

# production 環境のトップエラーを確認
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py top --env production

# active なエラーを一覧表示
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py list --status active

# デプロイ一覧を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py deploys

# バージョン詳細を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py version <version> --env production

# アイテムのステータスを更新
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py update <item_number> --status resolved
```

その他のオプションは `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rollbar.py --help` を参照。

## 出力形式

取得した情報を以下の形式で返す:

- 実行したコマンドと対象
- エラー詳細またはエラー一覧の要約
- 対応が必要な場合の推奨アクション
