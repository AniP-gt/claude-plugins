---
name: youtube-login
description: YouTube OAuth2認証手順。credentials.jsonの配置からブラウザ認証・トークン保存まで。
context: fork
---

# YouTube OAuth2 ログイン

## 入力

$ARGUMENTS

## 前提条件

GCPコンソールでOAuth 2.0クライアントIDを作成し、credentials.jsonをダウンロードすること。
YouTube Data API v3 と YouTube Analytics API を有効にすること。

## 手順

### 1. credentials.json の存在確認

`~/.config/youtube-analyzer/credentials.json` にファイルが配置されているか確認する。
環境変数 `YOUTUBE_CREDENTIALS_PATH` で別のパスを指定することもできる。

未配置の場合はGCPコンソールでの取得手順を案内すること。

### 2. 認証URLを取得

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py auth login --url-only
```

### 3. ユーザーに認証を依頼

コマンドの出力（認証URL）を **省略せず全文** ユーザーに提示し、以下を依頼する:

1. このURLをブラウザで開いてGoogleアカウントで認証してください
2. 認証後、ブラウザのアドレスバーに `localhost:8080/?code=...&scope=...` というURLが表示されます（ページ自体はエラーになることがあります）
3. そのURLをコピーして貼り付けてください

**ユーザーからコールバックURLを受け取るまで次に進まないこと。**

### 4. コールバックURLでトークン取得

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py auth login --code "<ユーザーが貼り付けたURL>"
```

### 5. ログイン確認

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py auth status
```

「認証済み」と表示されれば認証完了。

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- トークンの有効期限
