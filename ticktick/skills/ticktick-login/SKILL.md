---
name: ticktick-login
description: TickTick APIへのOAuth認証手順。初回セットアップとブラウザ認証を経てトークンを保存する。
---

# TickTick MCP ログイン

## 入力

$ARGUMENTS

## 前提条件

**初回のみ**: https://developer.ticktick.com/ でアプリを登録し、client_id と client_secret を取得すること。
Redirect URI には `http://localhost:3121/callback` を設定すること。

## 手順

### 0. 初回セットアップ（未設定の場合のみ）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py setup \
  --client-id "<CLIENT_ID>" \
  --client-secret "<CLIENT_SECRET>"
```

ユーザーが client_id / client_secret を持っていない場合は、
https://developer.ticktick.com/ での登録を案内すること。

### 1. 認証URLを取得

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py login --url-only 2>&1
```

stderr に `[pending_file:/tmp/ticktick_oauth_XXXXX.json]` が出力される。
このパスを次ステップ用に保持すること。

### 2. ユーザーに認証を依頼

コマンドの出力（認証URL）を **省略せず全文** ユーザーに提示し、以下を依頼する:

1. このURLをブラウザで開いてTickTickアカウントで認証してください
2. 認証後、ブラウザのアドレスバーに `localhost:3121/callback?code=...&state=...` というURLが表示されます（ページ自体はエラーになることがあります）
3. そのURLをコピーして貼り付けてください

**ユーザーからコールバックURLを受け取るまで次に進まないこと。**

### 3. コールバックURLでトークン取得

ステップ1で取得した pending_file パスを環境変数に設定してから実行:

```bash
TICKTICK_OAUTH_PENDING_FILE="<pending_fileパス>" \
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py login --code "<ユーザーが貼り付けたURL>"
```

### 4. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ticktick_cli.py status
```

「Status: Authenticated」と表示されれば認証完了。

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- スコープ情報
