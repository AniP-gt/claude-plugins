---
name: youtube-analyze
description: チャンネル分析手順。YouTube Analytics APIで再生数・視聴時間・人気動画を取得。
context: fork
---

# YouTube チャンネル分析

## 入力

$ARGUMENTS

## 認証確認

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py auth status
```

未認証の場合は `youtube-login` スキルの手順に従って認証を行うこと。

## コマンド実行

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python youtube.py analyze [--days N]
```

| 引数 | デフォルト | 説明 |
|------|-----------|------|
| `--days` | 28 | 分析対象の日数 |

## サブエージェント

メインコンテキストの消費を抑えるため、`youtube-analyzer-runner` サブエージェントに委任して実行できる。

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドと操作内容
- 取得結果の要約（再生数・視聴時間・人気動画）
- 必要に応じて生データ
