# ga4

Google Analytics 4 データ取得プラグイン。google-analytics-data SDK を使ってアカウント・プロパティ・レポートを Claude Code から参照する。複数プロパティを名前で管理できる。

## Skills

| Skill | 説明 |
|-------|------|
| ga4-run | GA4データ取得（アカウント・プロパティ・レポート・リアルタイム） |
| ga4-reference | コマンドリファレンス（runner用） |

## Setup

### 1. GCPサービスアカウント作成

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Google Analytics Data API を有効化
3. サービスアカウントを作成し、JSONキーをダウンロード
4. GA4プロパティの「プロパティのアクセス管理」でサービスアカウントに閲覧者権限を付与

### 2. 認証情報配置

```bash
mkdir -p ~/.config/ga4
cp ~/Downloads/service-account-*.json ~/.config/ga4/credentials.json
```

または環境変数で指定:

```bash
export GA4_CREDENTIALS_PATH=/path/to/service-account.json
```

### 3. プロパティ設定

```bash
cd ga4/scripts && uv run python ga4.py property add mysite 123456789
```

### 4. 依存パッケージインストール

```bash
cd ga4/scripts && uv sync
```

### 5. プラグインインストール

```bash
claude plugin add --source /path/to/claude-plugins/ga4
```

## Usage

### アカウント一覧

```bash
cd ga4/scripts && uv run python ga4.py accounts
```

### プロパティ情報確認

```bash
cd ga4/scripts && uv run python ga4.py property mysite
```

### レポート取得

```bash
cd ga4/scripts && uv run python ga4.py report --metrics activeUsers,sessions --dimensions date
cd ga4/scripts && uv run python ga4.py report --metrics screenPageViews --dimensions pagePath --limit 10
```

### リアルタイムデータ

```bash
cd ga4/scripts && uv run python ga4.py realtime --metrics activeUsers
```

### 設定確認

```bash
cd ga4/scripts && uv run python ga4.py config show
```

## File Structure

```
ga4/
├── .claude-plugin/
│   └── plugin.json
├── scripts/
│   ├── ga4.py              # 単一CLIスクリプト（サブコマンド方式）
│   ├── pyproject.toml
│   └── uv.lock
├── agents/
│   └── runner.md
├── skills/
│   ├── ga4-run/
│   │   └── SKILL.md
│   └── ga4-reference/
│       └── SKILL.md
└── README.md
```
