---
name: ga4-reference
description: GA4プラグインのコマンドリファレンス。全サブコマンドと引数一覧。
user-invocable: false
context: fork
---

# GA4 コマンドリファレンス

## 実行方法

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python ga4.py <subcommand> [options]
```

## サブコマンド一覧

### accounts

アカウント/プロパティ一覧を取得する。

```
ga4.py accounts
```

引数なし。

### property

プロパティ詳細を取得する。

```
ga4.py property <name_or_id>
```

| 引数 | 必須 | 説明 |
|------|------|------|
| `name_or_id` | Yes | プロパティ名 (config.jsonのキー) またはプロパティID |

### ads-links

Google Adsリンク一覧を取得する。

```
ga4.py ads-links <name_or_id>
```

| 引数 | 必須 | 説明 |
|------|------|------|
| `name_or_id` | Yes | プロパティ名またはプロパティID |

### report

レポートを取得する。

```
ga4.py report [--property <name_or_id>] --metrics <m> [--dimensions <d>] [--limit N]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--property` | No | config default | プロパティ名またはID |
| `--metrics` | Yes | - | メトリクス (カンマ区切り) |
| `--dimensions` | No | - | ディメンション (カンマ区切り) |
| `--limit` | No | 100 | 取得件数上限 |

### realtime

リアルタイムレポートを取得する。

```
ga4.py realtime [--property <name_or_id>] --metrics <m> [--dimensions <d>] [--limit N]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--property` | No | config default | プロパティ名またはID |
| `--metrics` | Yes | - | メトリクス (カンマ区切り) |
| `--dimensions` | No | - | ディメンション (カンマ区切り) |
| `--limit` | No | 100 | 取得件数上限 |

### custom-dims

カスタムディメンション/メトリクスを取得する。

```
ga4.py custom-dims [--property <name_or_id>]
```

| 引数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `--property` | No | config default | プロパティ名またはID |

### config show

現在の設定・認証状態を表示する。

```
ga4.py config show
```

引数なし。

## config.json スキーマ

パス: `~/.config/ga4/config.json`

```json
{
  "default": "my-blog",
  "properties": {
    "my-blog": "123456789",
    "blog-b": "987654321"
  },
  "credentials_file": "~/.config/ga4/credentials/service-account.json"
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| `default` | string | `--property` 未指定時に使うプロパティ名 |
| `properties` | object | プロパティ名→ID のマッピング |
| `credentials_file` | string | Service Account JSONファイルのパス (`~` 展開対応) |

## プロパティ解決順

1. `--property` 引数
2. `GA4_PROPERTY_ID` 環境変数
3. config.json の `default`

名前解決: 数字のみならそのままIDとして使用。config.jsonの `properties` にあれば対応するIDに変換。
