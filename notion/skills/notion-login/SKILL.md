---
name: notion-login
description: Notion MCPへのOAuth 2.1認証手順。公式MCP Python SDKでブラウザ認証し、認証ユーザーの email/teams をメタ情報として保存する。複数アカウント追加可能。
---

# Notion MCP ログイン

## 入力

$ARGUMENTS

## 前提

- Python 3.10 以上
- `mcp` と `httpx` パッケージ（初回は `pip3 install mcp httpx` で導入）

## 手順

### 1. ログイン実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py login
```

公式 MCP Python SDK が以下を自動処理する:

1. `https://mcp.notion.com/.well-known/oauth-protected-resource/mcp` からメタデータ取得
2. RFC 7591 動的クライアント登録
3. PKCE + authorization_code フロー → **ブラウザが自動で開く**
4. `http://localhost:3032/callback` で認可コード受信
5. トークン交換後、`notion-get-users user_id=self` を呼んで認証ユーザーの email/name を取得
6. `notion-get-teams` を呼んでアクセス可能な teamspace 一覧を取得
7. `~/.config/notion-mcp/<email-slug>/` 配下に `tokens.json` / `client_info.json` / `meta.json` を保存（パーミッション 0600）

### 2. ユーザーへの案内

ユーザーに対しては **認証URLを提示せず**、以下のみを伝える:

- 「ブラウザが開きますので、Notion アカウントで認証してください」
- 「ワークスペースとアクセスを許可するページ／データベースを選択してください」

**禁止事項**:
- エージェントが認証URLをユーザーに貼り付けて「このURLをブラウザで開いてください」と依頼すること
- コールバックURLのコピー＆ペーストを依頼すること

### 3. ログイン確認

ターミナルに以下のような出力が表示されれば認証完了:

```text
Login successful: user@example.com
Account key: user-example-com
Teams: チームA, チームB
```

## 複数アカウント

Notion は同一ブラウザでも複数ワークスペース（個人 / 組織等）を持てる。本プラグインは email-slug 単位でアカウントを保存するため、`login` を再実行するだけで別アカウントを追加できる。

```bash
# アカウント追加（別アカウントで再ログイン）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py login

# 一覧確認
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py accounts

# デフォルト切替
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py set-default <account_key_or_email>

# 個別ログアウト
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py logout <account_key_or_email>
```

`accounts` の出力例:

```text
  user-example-com [default]
    Email: user@example.com
    Name:  Example User
    Teams: チームA, チームB

  another-org-com
    Email: another@org.com
    Name:  Another User
    Teams: 営業, エンジニアリング
```

### メタ情報の再取得

teams や name など meta.json の情報だけを更新したい場合は、再認証なしで:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py refresh-meta [--account <key>]
```

### トラブルシューティング

認証エラーが発生した場合:

```bash
# 該当アカウントのトークンとクライアント情報を削除
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py logout <account_key>
# 再ログイン
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/notion_cli.py login
```

## 注意事項

- ポート 3032 が他プロセスで使用されていると失敗する
- ヘッドレス環境（Dockerコンテナ・CI等）ではブラウザが自動起動しないため、デスクトップ環境で実行すること
- ヘッドレス環境で実行された場合も、エージェントは認証URLをユーザーに転送・提示しない
- OrbStack Linux VM ではホストmacOSのブラウザが自動で開く（`/opt/orbstack-guest/bin/open` を使用）
- アクセス可能なページ／データベースは Notion 認可画面で **ユーザー本人** が選択する。エージェントが追加権限の付与を促してはならない

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- アカウントキー（email-slug）と email / teams
- トークン保存場所（`~/.config/notion-mcp/<account_key>/tokens.json`）
