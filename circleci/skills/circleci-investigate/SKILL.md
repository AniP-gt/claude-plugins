---
name: circleci-investigate
description: CircleCIのビルド・パイプライン・テスト結果を調査する。URLやプロジェクトslugからビルド失敗ログ、テスト結果、flakyテスト、最新パイプラインステータスを取得し、必要に応じてワークフロー再実行・パイプライン実行・config検証を行う。
context: fork
effort: low
agent: general-purpose
---

# CircleCI 調査手順

委任メッセージまたはユーザーの指示から調査対象・目的を把握し、CircleCI のビルド・パイプライン情報を取得する。

## 前提条件

- Node.js 18以上
- 環境変数 `CIRCLECI_TOKEN`（Personal API Token）が設定済みであること
- セルフホスト環境の場合は `CIRCLECI_BASE_URL` を併せて設定する（デフォルト: `https://circleci.com`）

Personal API Token は https://app.circleci.com/settings/user/tokens から取得。

## ワークフロー

1. **調査目的を判定**:
   - CircleCI URL（pipeline/workflow/job）が指定されている → `url` コマンドでビルド失敗ログを取得
     - テスト結果が必要なら `--tests`、最新ステータスなら `--status`、アーティファクト一覧なら `--artifacts`
   - プロジェクトslugとブランチが分かっている → `failures` / `tests` / `status` / `artifacts`
   - flaky テストの調査 → `flaky` コマンド
   - 失敗箇所からの再実行が必要 → `rerun --from-failed`
   - 新規パイプライン実行 → `run-pipeline`
   - config.yml の妥当性検証 → `config`
   - フォロー中プロジェクト一覧 → `projects`
2. **コマンド実行**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py <subcommand> [options]`
3. **結果の解析と報告**

## コマンド一覧

| コマンド | 引数 | 説明 |
|---|---|---|
| `url <circleci_url>` | `circleci_url`: CircleCI URL（必須）, `--tests` / `--status` / `--artifacts` / `--flaky`（任意・排他） | URL から関連情報を取得（デフォルト: ビルド失敗ログ） |
| `failures` | `--project-slug/-p <slug>`, `--branch/-b <branch>`, `--project-url/-u <url>`, `--output-dir/-o <dir>` | ビルド失敗ログを取得（`--output-dir` 指定で大容量ログをファイル保存） |
| `tests` | `--project-slug/-p <slug>`, `--branch/-b <branch>`, `--project-url/-u <url>` | ジョブのテスト結果を取得 |
| `status` | `--project-slug/-p <slug>`, `--branch/-b <branch>`, `--project-url/-u <url>` | 最新パイプラインのステータスを取得 |
| `artifacts` | `--project-slug/-p <slug>`, `--branch/-b <branch>`, `--project-url/-u <url>` | ジョブのアーティファクト一覧を取得 |
| `flaky` | `--project-slug/-p <slug>`, `--project-url/-u <url>` | プロジェクトの flaky テストを検出 |
| `projects` | なし | フォロー中の CircleCI プロジェクト一覧 |
| `rerun` | `--workflow-id/-w <uuid>` または `--workflow-url/-u <url>`（いずれか必須）, `--from-failed`（任意） | ワークフローを再実行（既定は最初から、`--from-failed` で失敗箇所から） |
| `run-pipeline` | `--project-slug/-p <slug>`, `--branch/-b <branch>`, `--project-url/-u <url>`, `--pipeline-name/-n <name>` | パイプラインを実行（複数定義時は `--pipeline-name` 必須） |
| `config <path>` | `path`: `.circleci/config.yml` のパス（必須） | config.yml の妥当性を検証 |

## 使用例

```bash
# CircleCI URL からビルド失敗ログを取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py url \
  "https://app.circleci.com/pipelines/github/org/repo/123/workflows/abc/jobs/456"

# 同 URL でテスト結果を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py url \
  "https://app.circleci.com/pipelines/github/org/repo/123" --tests

# プロジェクトslugとブランチで失敗ログ取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py failures \
  --project-slug "github/org/repo" --branch main

# 大容量ログをファイルに保存
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py failures \
  --project-slug "github/org/repo" --branch main --output-dir /tmp/circleci-logs

# flaky テストを検出
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py flaky \
  --project-slug "github/org/repo"

# ワークフローを失敗箇所から再実行
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py rerun \
  --workflow-url "https://app.circleci.com/.../workflows/a12145c5-90f8-4cc9-98f2-36cb85db9e4b" \
  --from-failed

# config.yml の妥当性検証
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py config .circleci/config.yml

# フォロー中プロジェクト一覧
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py projects
```

その他のオプションは `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/circleci.py --help` を参照。

## 入力パターン

CircleCI MCP ツールは以下のいずれかの方法でターゲットを特定する：

1. **`--project-slug` + `--branch`**: 最も明示的。事前に `projects` コマンドで slug を確認
2. **`--project-url`**: pipeline / workflow / job のいずれかの URL を渡す（最も簡単）
3. **ローカルワークスペース推論**: `--project-slug` も `--project-url` も指定しない場合、MCP サーバが git remote から推論する（要 git 管理下）

## 出力形式

取得した情報を以下の形式で返す:

- 実行したコマンドと対象
- ビルド失敗・テスト結果・パイプライン状態の要約
- 対応が必要な場合の推奨アクション（再実行・config 修正等）
