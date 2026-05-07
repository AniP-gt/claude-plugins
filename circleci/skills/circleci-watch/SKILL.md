---
name: circleci-watch
description: CircleCIワークフローを目的状態（terminal / success）に到達するまで自律監視し、状態変化のティックと最終レポートを返す。/loopではなくシェルループで完結し、ポーリング過多・停止条件曖昧・トークン浪費を防ぐ。
context: main
effort: low
---

# CircleCI ワークフロー監視手順

委任メッセージまたはユーザーの指示から監視対象のワークフローを特定し、目的状態に到達するまで `circleci.py watch` を起動して進捗を逐次報告する。

## 前提条件

- Python 3.8 以上（標準ライブラリのみ使用）
- 環境変数 `CIRCLECI_TOKEN`（Personal API Token）が設定済みであること
- セルフホスト環境では `CIRCLECI_BASE_URL` も設定する（デフォルト: `https://circleci.com`）

Personal API Token は https://app.circleci.com/settings/user/tokens から取得。

## 入力パラメータ

| パラメータ | 必須 | 説明 |
|---|---|---|
| `--project-url` / `--workflow-url` | ※ | pipeline / workflow / job の URL（最も簡単） |
| `--workflow-id` | ※ | ワークフローUUIDを直接指定 |
| `--project-slug` + `--branch` | ※ | プロジェクトslug＋ブランチで最新ワークフローを推定 |
| `--target-state` | 任意 | `terminal`(default) / `success`。terminalは success/failed/error/canceled/unauthorized いずれかで停止 |
| `--interval` | 任意 | ポーリング間隔（秒）。default `90`、最小 `30`、最大 `600` |
| `--max-wait` | 任意 | 全体タイムアウト（秒）。default `1800`（30分）、最大 `7200`（120分） |
| `--notify-on` | 任意 | `change`(default) / `every`。change はジョブ・ワークフロー状態が変化した時のみ進捗ティック出力 |

※ 上3パターンのうちいずれかで監視対象を一意に決められること。複数指定時の優先順位: `--workflow-id` > URL（`--workflow-url` / `--project-url`） > `--project-slug` + `--branch`。

## 停止条件（いずれかを満たすと終了）

1. ワークフローが `target-state` を満たした
2. `target-state=success` の場合、ワークフローまたは個別ジョブが failed/canceled/error/unauthorized で確定（失敗扱いで停止）
3. `--max-wait` を超過（タイムアウト報告）
4. ユーザーが手動中断（Ctrl-C もしくは Bash バックグラウンドプロセス kill）

## ワークフロー

1. **入力解釈**: ユーザー指示から URL / slug+branch / workflow-id を抽出。曖昧な場合は `circleci-investigate` の `status` で最新ワークフローIDを確定する
2. **watch 起動**: `circleci.py watch` を `run_in_background=true` で起動し、進捗を BashOutput で取得する。**メインターンを長時間ブロックしない**
3. **進捗報告**: 出力に `[circleci-watch] tick` または `FINAL` 行が出たタイミングで要約をユーザーへ伝える
4. **完了判定**: `[circleci-watch] FINAL status=success|failure|timeout` を検出したら最終レポートを整形して報告
5. **失敗時**: `circleci-investigate` の `failures` コマンドで失敗ジョブのログを補足取得し、ユーザーへ提示

## 実行コマンド

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py watch \
  --project-url "https://app.circleci.com/pipelines/github/org/repo/123/workflows/73a9e721-..." \
  --target-state terminal \
  --interval 90 \
  --max-wait 1800 \
  --notify-on change
```

ワークフローIDが分かっている場合:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py watch \
  --workflow-id 73a9e721-90f8-4cc9-98f2-36cb85db9e4b \
  --target-state success
```

ブランチの最新ワークフローを監視:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py watch \
  --project-slug github/org/repo \
  --branch main
```

ワークフロー状態を1度だけ取得（差分計算用途）:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py workflow-status \
  --workflow-id 73a9e721-90f8-4cc9-98f2-36cb85db9e4b
```

## 出力フォーマット

進捗ティック（`notify_on=change` 時はジョブ状態変化時のみ送信）:

```text
[circleci-watch] tick elapsed=1m30s workflow=running changed=1
  ~ deploy-front-web-production: queued → running
```

最終レポート（成功）:

```text
[circleci-watch] FINAL status=success elapsed=18m24s
  pipeline=#9249 workflow=73a9e721-90f8-4cc9-98f2-36cb85db9e4b
  workflow_status=success target=terminal
  jobs:
    checkout_code                       success    1m02s
    build-docker-image-web-production   success    7m11s
    deploy-front-web-production         success    8m30s
  url: https://app.circleci.com/pipelines/github/org/repo/9249/workflows/73a9e721-...
```

最終レポート（失敗・タイムアウト）の場合は `status=failure` / `status=timeout` となる。失敗時はメインエージェントが続けて `circleci-investigate failures --project-url <url>` を実行し、失敗ジョブのログ抜粋を付加する。

## 終了コード

| 終了コード | 意味 |
|---|---|
| 0 | 成功（target-state 到達 / terminal で success） |
| 1 | 入力エラー / API エラー |
| 2 | failure（target-state 未達で失敗扱い） |
| 3 | timeout（max-wait 超過） |

## 制約・注意

- `--interval` の最小値は 30 秒。CircleCI API レート制限に配慮するため、特別な理由がない限り default の 90 秒を使う
- `--max-wait` の上限は 7200 秒（120分）。それ以上の長時間監視はサポートしない（再起動して継続する）
- watch は `run_in_background=true` で起動することを強く推奨。メインターンで同期実行すると Claude が他の指示に応答できなくなる
- ワークフロー再実行で workflow_id が変わるケースには非対応。再実行時は新しい workflow_id で watch を再起動する
- `circleci-investigate` skill とは関心が異なる。単発の調査は investigate、目的状態到達まで待つ場合は本 skill を使う
