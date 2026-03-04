---
name: investigate
description: Sentryエラートラッキングの調査を実行。URLやイシューIDからエラー詳細を取得し、プロジェクト・組織情報の確認、エラー統計・推移分析を行う。
context: fork
agent: general-purpose
---

# Sentry 調査手順

委任メッセージまたはユーザーの指示から調査対象・目的を把握し、Sentry のエラートラッキングデータを取得する。

## 前提条件

- Node.js 20以上（推奨: Node 22）
- 環境変数 `SENTRY_ACCESS_TOKEN`（User Auth Token）が設定済みであること

Auth Token は Sentry > Settings > Account > API > Auth Tokens から取得。

## ワークフロー

1. **調査目的を判定**:
   - URL が指定されている → `url` コマンドでイシュー詳細を取得
   - イシューID が分かっている → `issue` コマンドで詳細を取得
   - 統計・推移を確認したい → `stats` コマンドでエラー統計を取得
   - 頻出エラーを知りたい → `top-issues` コマンドでイシューランキングを取得
   - プロジェクト一覧が必要 → `projects` コマンドで取得
   - 組織一覧が必要 → `orgs` コマンドで取得
   - イシューのステータス変更が必要 → `update` コマンドで更新
   - 認証確認が必要 → `whoami` コマンドで確認
2. **コマンド実行**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py <subcommand> [options]`
3. **結果の解析と報告**

## コマンド一覧

| コマンド | 引数 | 説明 |
|---|---|---|
| `url <sentry_url>` | `sentry_url`: SentryイシューのURL（必須） | Sentry の URL からイシュー詳細を取得 |
| `issue <issue_id>` | `issue_id`: イシューID（必須） | イシュー ID から詳細を取得 |
| `projects` | `--org <slug>`: 組織slug（任意） | プロジェクト一覧を取得 |
| `orgs` | なし | 組織一覧を取得 |
| `whoami` | なし | 認証ユーザー情報を取得 |
| `stats <org>` | `org`: 組織slug（必須）, `--project/-p <slug>`: プロジェクト（任意）, `--period/-t <期間>`: 期間 `1h,24h,7d,14d,30d`（デフォルト: `14d`）, `--group-by/-g <軸>`: 集計軸 `day,error-type,title`（デフォルト: `day`）, `--limit/-l <数>`: 最大結果数（デフォルト: `30`） | エラー統計・推移データを取得 |
| `top-issues <org>` | `org`: 組織slug（必須）, `--project/-p <slug>`: プロジェクト（任意）, `--sort/-s <順>`: ソート `freq,date,new`（デフォルト: `freq`）, `--query/-q <クエリ>`: Sentry検索クエリ（デフォルト: `is:unresolved`）, `--limit/-l <数>`: 最大件数（デフォルト: `10`） | 頻出イシューランキングを取得 |
| `update <issue_id>` | `issue_id`: イシューID（必須）, `--status <resolved\|unresolved\|ignored>`: ステータス（任意）, `--assignee <email>`: 担当者（任意） | イシューのステータス等を更新 |

## 使用例

```bash
# URL からイシュー詳細を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py url "https://myorg.sentry.io/issues/12345/"

# イシューIDから詳細を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py issue 12345

# プロジェクト一覧を取得（組織指定）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py projects --org myorg

# 全プロジェクト一覧を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py projects

# 組織一覧を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py orgs

# 認証ユーザー情報を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py whoami

# イシューを resolved に更新
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py update MYPROJECT-123 --status resolved

# 直近14日間の日別エラー推移
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py stats myorg

# プロジェクト指定で7日間エラータイプ別集計
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py stats myorg -p myproject -t 7d -g error-type

# エラータイトル別Top10
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py stats myorg -g title -l 10

# 頻出イシューTop10
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py top-issues myorg

# 新着イシュー5件（プロジェクト指定）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py top-issues myorg -p myproject -s new -l 5

# 未解決の特定エラーを検索
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py top-issues myorg -q "is:unresolved TypeError"
```

その他のオプションは `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/sentry.py --help` を参照。

## 備考

- セルフホスト環境の URL の場合、`SENTRY_HOST` を自動算出する（手動設定は不要）
- `sentry.io` / `*.sentry.io` の URL はデフォルト扱い

## 出力形式

取得した情報を以下の形式で返す:

- 実行したコマンドと対象
- イシュー詳細の要約
- 対応が必要な場合の推奨アクション
