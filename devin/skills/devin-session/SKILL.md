---
name: devin-session-step
description: Devin Session APIでタスクを委任・管理する手順。
context: fork
effort: low
---

# Devin Session API 利用手順

## いつ使うか

- Devinにタスクを委任したいとき

## 手順

### 1. セッション作成

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/deepwiki_cli.py run "タスク指示"
```

### 2. 状態確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/deepwiki_cli.py status <session_id>
```

### 3. メッセージ送信（必要に応じて）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/deepwiki_cli.py message <session_id> "メッセージ"
```

## runオプション

| オプション | 説明 |
|---|---|
| `--title` | セッションタイトル |
| `--tags` | タグ（カンマ区切り） |
| `--idempotent` | べき等モード |
| `--wait` | 完了まで待機（ポーリング） |
| `--interval` | ポーリング間隔秒数（デフォルト: 15） |
| `--timeout` | ポーリングタイムアウト秒数（デフォルト: 600） |

## セッション状態

| status_enum | 説明 |
|---|---|
| `working` | 作業中 |
| `blocked` | ブロック中（ユーザー入力待ち等） |
| `finished` | 完了 |
| `expired` | 期限切れ |

## 運用ガイド

- `run` でセッション作成後、statusが `working` になったら **statusポーリングはバックグラウンドで実行** する。Devinの作業完了には数分かかるため、フォアグラウンドで待機するとその間他の作業がブロックされる。
- `--wait` オプションを使う場合も同様にバックグラウンド実行を推奨。
- `blocked` または `finished` になったら、メッセージ内容とともに結果をユーザーに返却する。`blocked` はDevinが追加入力を待っている状態なので、ユーザーが次のアクションを判断できるよう情報を提示すること。

## 共通オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--api-key` | Bearer認証用APIキー | 環境変数 `DEVIN_API_KEY` |
| `--debug` | デバッグログを出力 | off |

## 認証

`DEVIN_API_KEY` が必要。以下のいずれかで指定:

1. 環境変数 `DEVIN_API_KEY`（`.claude/settings.local.json` の `env` で設定済み）
2. `--api-key` オプション
