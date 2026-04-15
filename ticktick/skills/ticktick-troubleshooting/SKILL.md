---
name: ticktick-troubleshooting
description: TickTick APIの既知の問題と対処法のリファレンス。
user-invocable: false
---

# TickTick トラブルシューティング

| 症状 | 対処 |
|---|---|
| `Not authenticated` | `setup` でクライアント情報を設定後、`login` で認証を実行 |
| `クライアント情報が設定されていません` | `setup --client-id <id> --client-secret <secret>` を実行 |
| `HTTP 401` | トークンが無効。`logout` 後に `login` で再認証 |
| `HTTP 429` | レートリミット超過。しばらく待ってから再試行 |
| `HTTP 400: redirect_uri` | developer.ticktick.com のアプリ設定で `http://localhost:3121/callback` を正確に登録しているか確認 |
| `State mismatch` | `login --url-only` を再実行してURLを取り直す |
| `Network error` | ネットワーク接続を確認。`--debug` で詳細ログを出力 |
| ポート3121が使用中 | `login` 実行前に他のTickTick認証プロセスを終了 |
| コールバックURLにcodeがない | 認証URLの有効期限切れ。`login --url-only` を再実行 |
