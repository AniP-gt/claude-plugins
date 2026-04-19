# youtube-analyzer

YouTube チャンネル分析とトレンド検索プラグイン。YouTube Analytics API と YouTube Data API v3 を使い、チャンネル統計取得とキーワードトレンド検索を Claude Code から実行する。

## Skills

| Skill | 説明 |
|-------|------|
| youtube-analyze | チャンネル分析（再生数・視聴時間・人気動画） |
| youtube-trending | キーワードトレンド検索 |
| youtube-login | OAuth2認証手順 |
| youtube-reference | コマンドリファレンス（runner用） |

## Setup

### 1. GCPプロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. YouTube Data API v3 と YouTube Analytics API を有効化
3. OAuth 2.0 クライアント ID を作成（デスクトップアプリケーション）
4. credentials.json をダウンロード

### 2. credentials.json 配置

```bash
mkdir -p ~/.config/youtube-analyzer
cp ~/Downloads/client_secret_*.json ~/.config/youtube-analyzer/credentials.json
```

または環境変数で指定:

```bash
export YOUTUBE_CREDENTIALS_PATH=/path/to/credentials.json
```

### 3. APIキー設定（トレンド検索用）

GCPコンソールで API キーを作成し、環境変数に設定:

```bash
export YOUTUBE_API_KEY=your_api_key_here
```

または設定ファイルに記載:

```bash
cat > ~/.config/youtube-analyzer/config.json << 'EOF'
{
  "api_key": "your_api_key_here"
}
EOF
```

### 4. 依存パッケージインストール

```bash
cd youtube-analyzer/scripts && uv sync
```

### 5. プラグインインストール

```bash
claude plugin add --source /path/to/claude-plugins/youtube-analyzer
```

## Usage

### チャンネル分析（OAuth2認証が必要）

```bash
cd youtube-analyzer/scripts && uv run python youtube.py analyze --days 28
```

### トレンド検索（APIキーのみ）

```bash
cd youtube-analyzer/scripts && uv run python youtube.py trending --keyword "Claude AI" --max-results 10 --region JP
```

### 認証

```bash
cd youtube-analyzer/scripts && uv run python youtube.py auth status
cd youtube-analyzer/scripts && uv run python youtube.py auth login --url-only
```

### 設定確認

```bash
cd youtube-analyzer/scripts && uv run python youtube.py config show
```

## File Structure

```
youtube-analyzer/
├── .claude-plugin/
│   └── plugin.json
├── scripts/
│   ├── youtube.py          # 単一CLIスクリプト（サブコマンド方式）
│   ├── pyproject.toml
│   └── .gitignore
├── agents/
│   └── runner.md
├── skills/
│   ├── youtube-analyze/
│   │   └── SKILL.md
│   ├── youtube-trending/
│   │   └── SKILL.md
│   ├── youtube-login/
│   │   └── SKILL.md
│   └── youtube-reference/
│       └── SKILL.md
└── README.md
```
