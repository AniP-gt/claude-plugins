---
name: youtube-reference
description: YouTubeプラグインのコマンドリファレンス。全サブコマンドと引数一覧。
user-invocable: false
context: fork
---

# YouTube コマンドリファレンス

## 実行方法

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py <subcommand> [options]
```

## サブコマンド一覧

### auth status

認証状態を確認する。未認証でもexit 0で状態を報告する。

```
youtube.py auth status
```

引数なし。

### auth login

OAuth2ブラウザ認証フローを実行する。

```
youtube.py auth login [--url-only] [--code <callback_url>]
```

| 引数 | 必須 | 説明 |
|------|------|------|
| `--url-only` | No | 認証URLをstdoutに出力してexit |
| `--code` | No | コールバックURLを受け取りtokenを保存 |

### analyze

YouTube Analytics APIでチャンネル統計を取得する。再生数・視聴時間・人気動画上位10件を表示。

```
youtube.py analyze [--days N]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--days` | No | 28 | 分析対象の日数 |

OAuth2認証が必要。未認証の場合は認証手順を案内してexit 1。

### trending

YouTube Data API v3でキーワードトレンド検索を実行する。

```
youtube.py trending --keyword <kw> [--max-results N] [--region CC]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--keyword` | Yes | - | 検索キーワード |
| `--max-results` | No | 20 | 取得件数 |
| `--region` | No | JP | リージョンコード |

OAuth2不要。APIキーのみで動作。

### config show

現在の設定・認証状態を表示する。

```
youtube.py config show
```

引数なし。

## 認証解決順

### trending（APIキーのみ）

1. `YOUTUBE_API_KEY` 環境変数
2. `~/.config/youtube-analyzer/config.json` の `api_key` フィールド

### analyze（OAuth2）

**credentials.json**:
1. `YOUTUBE_CREDENTIALS_PATH` 環境変数
2. `~/.config/youtube-analyzer/credentials.json`

**token.json**:
1. `YOUTUBE_TOKEN_PATH` 環境変数
2. `~/.config/youtube-analyzer/token.json`

## クォータ情報

- trending 1回 = 100 units/day
- 上限: 10,000 units/day
- クォータ超過時はexit 1 + エラーメッセージ
