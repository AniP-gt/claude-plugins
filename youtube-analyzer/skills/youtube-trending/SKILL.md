---
name: youtube-trending
description: YouTube キーワードトレンド検索。YouTube Data API v3でキーワードに関連する動画を取得。
context: fork
---

# YouTube トレンド検索

## 入力

$ARGUMENTS

## 認証

OAuth2不要。APIキーのみで動作する。

APIキーの設定方法:
- 環境変数: `YOUTUBE_API_KEY`
- 設定ファイル: `~/.config/youtube-analyzer/config.json` の `api_key` フィールド

## コマンド実行

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py trending --keyword <kw> [--max-results N] [--region CC]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--keyword` | Yes | - | 検索キーワード |
| `--max-results` | No | 20 | 取得件数 |
| `--region` | No | JP | リージョンコード |

## クォータ注意事項

- trending 1回 = 100 units
- 1日の上限: 10,000 units
- クォータ超過時は明日以降に再試行

## サブエージェント

メインコンテキストの消費を抑えるため、`youtube-analyzer-runner` サブエージェントに委任して実行できる。

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドと操作内容
- 検索結果の要約（動画タイトル・チャンネル名・再生数・公開日）
- 必要に応じて生データ
