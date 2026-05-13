---
name: ga4-run
description: GA4データ取得手順。認証セットアップからアカウント/プロパティ確認・レポート取得まで。
context: fork
---

# GA4 データ取得

## 入力

$ARGUMENTS

## 認証セットアップ

### 方式1: gcloud ADC (個人利用向け)

```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/analytics.readonly
```

### 方式2: Service Account JSON (自動化・チーム利用向け)

1. GCPコンソールでサービスアカウントを作成し、GA4プロパティにアクセス権を付与
2. JSONキーをダウンロードして配置:

```bash
mkdir -p ~/.config/ga4/credentials
mv ~/Downloads/service-account.json ~/.config/ga4/credentials/
```

3. config.jsonに `credentials_file` を設定するか、環境変数で指定:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/ga4/credentials/service-account.json
```

## 設定ファイル

`~/.config/ga4/config.json` を作成して複数プロパティを管理できる:

```bash
mkdir -p ~/.config/ga4
cat > ~/.config/ga4/config.json << 'EOF'
{
  "default": "my-blog",
  "properties": {
    "my-blog": "123456789",
    "corporate-site": "987654321"
  },
  "credentials_file": "~/.config/ga4/credentials/service-account.json"
}
EOF
```

`default` に設定した名前が `--property` 未指定時に使われる。

## 典型ワークフロー

### 1. 認証・設定確認

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python ga4.py config show
```

### 2. アカウント/プロパティ一覧を確認

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python ga4.py accounts
```

### 3. プロパティ詳細を確認

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python ga4.py property my-blog
```

### 4. レポート取得

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python ga4.py report --metrics activeUsers,sessions --dimensions date --limit 30
```

### 5. リアルタイムデータ

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python ga4.py realtime --metrics activeUsers --dimensions country
```

## サブエージェント

メインコンテキストの消費を抑えるため、`ga4-runner` サブエージェントに委任して実行できる。

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドと操作内容
- 取得結果の要約
- 必要に応じて生データ
