---
name: compass-search
description: コードベースのベクトル検索を実行する。ヘルスチェックから検索・インデックス構築までを一貫して行う。
context: fork
effort: low
---

# compass コードベース検索

## 入力

$ARGUMENTS

## ワークフロー

### 1. 検索を実行

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/search.sh "$ARGUMENTS"
```

または直接 Python で:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python search.py "$ARGUMENTS" --project-dir "${CLAUDE_PROJECT_DIR:-$PWD}"
```

**検索フロー（既定）:**
1. vector 検索で Top-K 候補（既定 30、`RERANK_CANDIDATES`）を取得
2. voyage rerank（既定 `rerank-2.5`、`RERANK_MODEL`）で再評価
3. 上位 N 件（`--top`、既定 5）を表示

**検索オプション:**
- `--project-dir`: プロジェクトディレクトリ（`$CLAUDE_PROJECT_DIR` 優先、未設定時は `$PWD`）
- `--top`: 表示件数（デフォルト: 5）
- `--no-rerank`: rerank を無効化し vector 検索のみ（環境変数 `RERANK_ENABLED=0` でも同じ）
- スコア表示は rerank ON 時は voyage rerank の relevance_score（0.8〜0.95 帯）、OFF 時は cosine similarity（0.6〜0.8 帯）

### 2. 検索失敗時の分岐

#### Index: NOT FOUND（テーブル未作成）

cocoindex 1.0 の CLI でインデックスを構築する。

```bash
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")
INDEX_NAME=$(echo "${HOST_PREFIX}_${PROJECT_NAME}" | sed 's/[^a-zA-Z0-9]/_/g')
APP_NAME="CompassIndex_${INDEX_NAME}"

cd ${CLAUDE_PLUGIN_ROOT}/scripts \
  && SOURCE_PATH="${CLAUDE_PROJECT_DIR:-$PWD}" \
     INDEX_NAME="$INDEX_NAME" \
     PATTERNS="**/*.rb,**/*.py" \
     uv run cocoindex update -f "main.py:${APP_NAME}"
```

**主な環境変数:**
- `SOURCE_PATH` — インデックス対象ディレクトリ（必須、絶対パス）
- `INDEX_NAME` — `hostname_プロジェクト名`（未指定時は SOURCE_PATH のベース名）
- `PATTERNS` — 対象パターン csv（既定 `**/*.rb`）
- `EXCLUDE` — 追加除外 csv
- `NO_DEFAULT_EXCLUDES` — `1` でデフォルト除外を無効化
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — RecursiveSplitter パラメータ（既定 800/200）
- `EMBEDDING_DIMENSION` — Matryoshka 対応モデルの出力次元

DB URL / API キーは fallback chain で解決:
1. プロセス環境変数
2. `~/.config/compass/secrets.env` / `~/.config/compass/.env`
3. `~/.config/cocoindex/secrets.env`（共通 hub）

**主な CLI フラグ:**
- `--reset` — 既存セットアップを drop してから rebuild
- `--full-reprocess` — キャッシュ無視で全再 embed
- `-L` / `--live` — LiveUpdater モード（差分監視を継続）
- テーブル名: `compassindex_<INDEX_NAME>__chunks`

構築完了後、再度検索を実行する。

#### PostgreSQL 接続 NG

DB 起動はスキルの責務外。ユーザーに以下を案内する:

```text
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

**重要**: スクリプトは `uv run` 経由で実行すること。`python3` で直接実行すると依存パッケージが見つからずエラーになる。

## サブエージェント

メインコンテキストから実行する場合は、`compass-runner` サブエージェントに必ず委任すること。サブエージェント経由で実行することでメインコンテキストのトークン消費を抑えられる。

## 出力

検索結果から関連ファイルのリストを構造化して報告する:
- 各ファイルのパスとスコア
- ファイルの概要（検索結果から読み取れる範囲で）
