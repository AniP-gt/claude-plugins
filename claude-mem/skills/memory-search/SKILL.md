---
name: memory-search
description: 永続メモリの検索・取得。3レイヤーワークフローで過去のセッション情報、観察、タイムラインを参照する。
context: fork
---

# claude-mem 利用手順

## 概要

claude-memのWorker HTTP API（localhost:37777）を使用して永続メモリを検索・取得するスキル。過去のセッション情報、観察、タイムラインの参照に使用する。

## サブエージェント

メインコンテキストから実行する場合は、`claude-mem-runner` サブエージェントに必ず委任すること。サブエージェント経由で実行することでメインコンテキストのトークン消費を抑えられる。

## いつ使うか

- 過去のセッションで行った作業を確認したいとき
- 「以前どうやって解決したか」を調べたいとき
- 特定のトピックに関する過去の観察・決定を検索したいとき

## 前提条件

- claude-mem Worker（localhost:37777）が起動していること
- Chromaサーバー（localhost:8000）が起動していること（セマンティック検索に必要）

## 3レイヤーワークフロー（必須）

コンテキスト消費を最小化するため、必ずこの順序で段階的に絞り込む。

### 1. 検索（インデックス取得）

IDとタイトルのみ返却される（1件あたり約50-100トークン）。

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py search "<検索語>" --limit 10
```

結果が少ない場合は `by-file` / `by-type` も試す。

| オプション | 説明 | デフォルト |
|---|---|---|
| `--limit`, `-l` | 結果件数 | 20 |
| `--project`, `-p` | プロジェクト名フィルタ | なし |
| `--type`, `-t` | 検索タイプ（observations/sessions/prompts） | observations |

### 2. タイムラインで前後関係を確認

検索結果のIDを使ってアンカー指定し、前後コンテキストを取得。

```bash
# アンカーID指定
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py timeline --anchor <ID>

# またはクエリで自動検索
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py timeline --query "<検索語>"
```

| オプション | 説明 | デフォルト |
|---|---|---|
| `--anchor`, `-a` | アンカーポイント（観察ID, セッションID `S123`, ISO timestamp） | なし |
| `--query`, `-q` | アンカー自動検索クエリ | なし |
| `--mode`, `-m` | 検索モード（auto/observations/sessions） | auto |
| `--before`, `-b` | アンカー前の深度 | 10 |
| `--after`, `-A` | アンカー後の深度 | 10 |
| `--project`, `-p` | プロジェクト名フィルタ | なし |

### 3. 必要な観察の詳細を取得

必要なIDだけを指定してフル詳細を取得。**フィルタリングなしに全件取得しないこと。**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py observation <ID>
```

## 追加の検索手段

```bash
# ファイルパスで検索
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py by-file "<path>" [--limit N] [--project NAME]

# 観察タイプで検索
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py by-type "<type>" [--limit N] [--project NAME]

# 最近のコンテキスト
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py recent [--project NAME] [--limit N]

# セッション・プロンプト取得（IDは数値のみ。タイムライン表示の「S440」→「440」）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py session <数値ID>
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py prompt <数値ID>
```

## 出力形式

取得した情報を以下の形式で返す:

- 検索クエリと検索結果の要約
- 関連する観察の詳細
- タイムライン上の文脈
