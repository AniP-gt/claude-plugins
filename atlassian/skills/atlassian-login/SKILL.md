---
name: atlassian-login
description: Atlassian MCPへのOAuth 2.1認証手順。公式MCP Python SDKでブラウザ認証し、トークンを保存する。
---

# Atlassian MCP ログイン

## 入力

$ARGUMENTS

## 前提

- Python 3.10 以上
- `mcp` と `httpx` パッケージ（初回は `pip3 install mcp httpx` で導入）

## 手順

### 1. ログイン実行

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/atlassian_cli.py login
```

公式 MCP Python SDK (`OAuthClientProvider` + `streamablehttp_client`) が以下を自動処理する:

1. `https://mcp.atlassian.com/.well-known/oauth-authorization-server` からメタデータ取得
2. RFC 7591 動的クライアント登録（`~/.config/atlassian-mcp/client_info.json` に永続化）
3. PKCE + authorization_code フロー開始 → **ブラウザが自動で開く**
4. `http://localhost:3031/callback` で認可コード受信
5. トークン交換 → `~/.config/atlassian-mcp/tokens.json` に保存（パーミッション 0600）

### 2. ユーザーへの案内

ユーザーに対しては **認証URLを提示せず**、以下のみを伝える:

- 「ブラウザが開きますので、Atlassianアカウントで認証してください」

**禁止事項**:
- エージェントが認証URLをユーザーに貼り付けて「このURLをブラウザで開いてください」と依頼すること
- コールバックURLのコピー＆ペーストを依頼すること

### 3. ログイン確認

ターミナルに「Login successful!」と表示されれば認証完了。

### トラブルシューティング

認証エラーが発生した場合:

```bash
# 保存済みトークン・クライアント情報を削除して再認証
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/atlassian_cli.py logout
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/atlassian_cli.py login
```

## 注意事項

- ポート 3031 が他プロセスで使用されていると失敗する
- ヘッドレス環境（Dockerコンテナ・CI等）ではブラウザが自動起動しないため、デスクトップ環境で実行すること
- ヘッドレス環境で実行された場合も、エージェントは認証URLをユーザーに転送・提示しない
- OrbStack Linux VM ではホストmacOSのブラウザが自動で開く（`/opt/orbstack-guest/bin/open` を使用）

## 出力

認証結果を報告する:
- 認証状態（成功/失敗）
- トークン保存場所（`~/.config/atlassian-mcp/tokens.json`）
