---
name: cocoindex-code-search
description: コードベースのベクトル検索を実行する。ヘルスチェックから検索・インデックス構築までを一貫して行う。
context: fork
effort: low
---

# CocoIndex ベクトル検索

## 入力

$ARGUMENTS

## ワークフロー

### 1. ヘルスチェック（PostgreSQL + インデックス確認）

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check.sh
```

以下を一括確認する:
- PostgreSQL接続
- 現プロジェクトのインデックステーブルの存在とチャンク数

### 2. 結果に応じて実行

#### 全てOK → 検索を実行

検索は cocoindex CLI を経由せず、`scripts/search.py` を直接実行する（psycopg2 で PostgreSQL に直接クエリ）:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python search.py "$ARGUMENTS" --project-dir "${CLAUDE_PROJECT_DIR:-$PWD}"
```

**検索オプション:**
- `--project-dir`: プロジェクトディレクトリ（`$CLAUDE_PROJECT_DIR` を優先、未設定時は `$PWD` にフォールバック）
- `--top`: 表示件数（デフォルト: 5）
- テーブル名は `hostname` + プロジェクトディレクトリのベースネームから自動計算される
- クエリ embedding は `~/.config/cocoindex/config.toml` の `[embedding]` 設定（必要なら `EMBEDDING_DIMENSION`）でドキュメント側と揃える

#### Index: NOT FOUND → インデックス構築後に検索

cocoindex 1.0 の CLI（`cocoindex update`）で構築する。`INDEX_NAME` にはサニタイズ済みの `hostname_プロジェクト名` を指定する（特殊文字は `_` に置換）。

```bash
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")
INDEX_NAME=$(echo "${HOST_PREFIX}_${PROJECT_NAME}" | sed 's/[^a-zA-Z0-9]/_/g')
APP_NAME="CodeIndex_${INDEX_NAME}"

# インデックス構築（cocoindex 1.0）
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
- `EXCLUDE` — 追加除外 csv（プラグインの DEFAULT_EXCLUDES に重ねて適用）
- `NO_DEFAULT_EXCLUDES` — `1` でデフォルト除外（`.git`, `node_modules` 等）を無効化
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — RecursiveSplitter パラメータ（既定 800/200）
- `EMBEDDING_DIMENSION` — Matryoshka 対応モデルの出力次元（voyage-3-large は 256/512/1024/2048）

DB URL / API キー等は `~/.config/cocoindex/{config.toml,secrets.env}` で集中管理。

**主な CLI フラグ:**
- `--reset` — 既存セットアップを drop してから rebuild（互換性のないスキーマ変更時）
- `--full-reprocess` — キャッシュ無視で全再 embed
- `-L` / `--live` — LiveUpdater モード（差分監視を継続）
- テーブル名: `codeindex_<INDEX_NAME>__code_chunks`（実行ログに表示）

構築完了後、再度検索を実行する。

#### PostgreSQL接続NG → ユーザーに通知

DB起動はスキルの責務外。ユーザーに以下を案内する:

```text
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

**重要**: スクリプトは `uv run` 経由で実行すること。`python3` で直接実行すると依存パッケージが見つからずエラーになる。

## サブエージェント

メインコンテキストから実行する場合は、`cocoindex-runner` サブエージェントに必ず委任すること。サブエージェント経由で実行することでメインコンテキストのトークン消費を抑えられる。

## 出力

検索結果から関連ファイルのリストを構造化して報告する:
- 各ファイルのパスとスコア
- ファイルの概要（検索結果から読み取れる範囲で）
