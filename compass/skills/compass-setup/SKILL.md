---
name: compass-setup
description: compass プラグインの環境セットアップ手順。初回設定・DB 起動・設定ファイルの管理方法。
user-invocable: false
---

# compass セットアップ

## 共通情報

- **CocoIndex バージョン**: 1.0 系（async / `cocoindex update` CLI）
- **専用 DB**: `compass`（pgvector-stack の `cocoindex` コンテナ内）
- **テーブル命名**: `compassindex_<host>_<project>__chunks`
- **App 名**: `CompassIndex_<host>_<project>`
- **スクリプト**: `${CLAUDE_PLUGIN_ROOT}/scripts/`
- **設定ファイル fallback chain**:
  1. プロセス環境変数（最優先）
  2. `~/.config/compass/secrets.env` / `~/.config/compass/.env`（compass 専用）
  3. `~/.config/cocoindex/secrets.env`（cocoindex-setup プラグイン管理、共通 hub）

## 依存プラグイン

以下が未インストールならまずインストールする:

```text
/plugin install pgvector-stack@hidetsugu-miya
/plugin install cocoindex-setup@hidetsugu-miya
```

- **`pgvector-stack`**: PostgreSQL コンテナ（`cocoindex`）を提供。compass の DB 基盤
- **`cocoindex-setup`**: `~/.config/cocoindex/` の secrets/config hub。`VOYAGE_API_KEY` 等を共有

## 初回セットアップ

### 1. pgvector-stack コンテナ起動

```bash
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

### 2. cocoindex-setup の secrets 配置

```bash
bash ~/.claude/plugins/cache/hidetsugu-miya/cocoindex-setup/scripts/check_config.sh
# または手動:
# cp ~/.claude/plugins/cache/hidetsugu-miya/cocoindex-setup/templates/secrets.example.env ~/.config/cocoindex/secrets.env
```

`~/.config/cocoindex/secrets.env` の `VOYAGE_API_KEY` を設定する。

### 3. compass 専用 DB / 設定の作成

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup_db.sh
```

このスクリプトが冪等に以下を実行:
- `~/.config/compass/.env` / `secrets.env` の auto-provision（雛形コピー、既存は触らない）
- `compass` database の作成
- `compass` DB に `vector` extension を作成

### 4. 初回インデックス構築

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

## テーブル名の規則

インデックステーブル名は `hostname` プレフィックス付きで、ホストごとに衝突しない:

- `compassindex_<hostname>_<project>__chunks`
- 例: `compassindex_macbookpro_local_wonder_front__chunks`

`<hostname>` は `hostname` コマンド出力を `[^a-zA-Z0-9]` → `_` に置換して小文字化したもの。
`<project>` は `CLAUDE_PROJECT_DIR` のベース名を同じサニタイズ規則で変換したもの。

同一 DB を複数ホストで共有しても、プレフィックスで名前空間が分離される。

## インデックス更新・再構築

cocoindex 1.0 系では `cocoindex update` CLI を使う。同じ App を再実行すると差分更新（追跡テーブルで管理）。

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts
SOURCE_PATH=<src> INDEX_NAME=<name> PATTERNS="**/*.rb" \
  uv run cocoindex update -f main.py:<AppName>
```

主な CLI フラグ:
- `--reset` — 既存セットアップを drop してから rebuild
- `--full-reprocess` — キャッシュ無視で全再処理
- `-L`, `--live` — LiveUpdater モード（差分監視を継続）

## LiveUpdater

`hooks/session-start.sh` が SessionStart で `cocoindex update -L` をバックグラウンド起動し、`session-end.sh` が SessionEnd で停止する。既存インデックスがあるプロジェクトのみ起動するため、初回構築前は無動作。

ログ: `/tmp/compass-live-updater.log`
PID: `~/.claude/tmp/.pid_compass_<sanitized_index>`

## 注意事項

### halfvec + HNSW

埋め込み列は `halfvec(dim)` 型で保存し、ベクトルインデックスは `hnsw (embedding halfvec_cosine_ops)` を `declare_sql_command_attachment` で付与する。pgvector の `ivfflat` は 2000 dim 上限のため、Matryoshka 出力 dim=2048 を使う場合は HNSW 必須。

### chunk_tsv 生成列（ハイブリッド検索の余地）

`chunk_text` から `to_tsvector('simple', chunk_text)` の生成列 `chunk_tsv` と GIN index を `declare_sql_command_attachment` で付与している。現状の `search.py` は dense vector + voyage rerank のみだが、将来 BM25 RRF を組み込む際にこのインフラを活用できる。
