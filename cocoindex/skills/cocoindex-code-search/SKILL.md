---
name: cocoindex-code-search
description: コードベースのベクトル検索を実行する。ヘルスチェックから検索・インデックス構築までを一貫して行う。
context: fork
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

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python search.py "$ARGUMENTS" --project-dir "${CLAUDE_PROJECT_DIR:-$PWD}"
```

**検索オプション:**
- `--project-dir`: プロジェクトディレクトリ（`$CLAUDE_PROJECT_DIR` を優先、未設定時は `$PWD` にフォールバック）
- `--top`: 表示件数（デフォルト: 10）
- テーブル名は `hostname` + プロジェクトディレクトリのベースネームから自動計算される

#### Index: NOT FOUND → インデックス構築後に検索

**重要**: `--name` には必ずサニタイズ済みの `hostname_プロジェクト名` を指定すること（特殊文字は `_` に置換）。

```bash
# ホスト名プレフィックス + プロジェクト名をサニタイズ
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
PROJECT_NAME=$(basename "${CLAUDE_PROJECT_DIR:-$PWD}")
INDEX_NAME=$(echo "${HOST_PREFIX}_${PROJECT_NAME}" | sed 's/[^a-zA-Z0-9]/_/g')

# インデックス構築
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run python main.py <source_path> --name "$INDEX_NAME" [--patterns "**/*.rb,**/*.py"] [--exclude "**/tmp/**"]
```

**構築オプション:**
- `source_path`: インデックス対象ディレクトリ（絶対パス）
- `--patterns`: 対象ファイルパターン（カンマ区切り、デフォルト: `**/*.rb`）
- `--exclude`: 除外パターン（カンマ区切り、デフォルト除外パターンに追加される）
- `--name`: **必須** — サニタイズ済みの `hostname_プロジェクト名`（例: `dev_wonder_api`, `macbookpro_local_wonder_front`）
- `--no-default-excludes`: デフォルト除外パターン（`.git`, `node_modules`, `.venv` 等）を無効化
- テーブル名: `codeindex_<name>__code_chunks`（実行後にも表示）

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
