---
name: cocoindex-setup
description: CocoIndexの環境セットアップ手順。初回設定・DB起動・設定ファイルの管理方法。
user-invocable: false
---

# CocoIndex セットアップ

## 共通情報

- **CocoIndex バージョン**: 1.0 系（async / `cocoindex update` CLI）
- **スクリプト**: `${CLAUDE_PLUGIN_ROOT}/scripts/`
- **ユーザー設定**:
  - `~/.config/cocoindex/config.toml` — 一般設定（DB URL / embedding / chunk）
  - `~/.config/cocoindex/secrets.env` — API キー（VOYAGE_API_KEY 等）
  - 旧 `~/.config/cocoindex/.env` も後方互換で読み込まれる
- **DB**: `cocoindex` コンテナ（pgvector 搭載 Postgres、ポート `15432`）
- **compose.yml**: `${CLAUDE_PLUGIN_ROOT}/templates/compose.yml` を `~/.config/cocoindex/` に配置して起動

## 初回セットアップ

### 1. 設定ファイルの配置

`~/.config/cocoindex/{secrets.env,config.toml}` は、セッション開始フック（`hooks/session-start.sh`）およびヘルスチェック（`scripts/check.sh`）の初回実行時にテンプレートから自動コピーされる（**既存ファイルは上書きしない**）。

手動セットアップする場合:

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/secrets.example.env ~/.config/cocoindex/secrets.env
cp ${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml ~/.config/cocoindex/config.toml
```

配置後、`~/.config/cocoindex/secrets.env` の `VOYAGE_API_KEY` を設定する。

`config.toml` で変更可能な主なキー:
- `[database].url` — Postgres 接続先
- `[embedding].provider` / `.model` / `.dimension` — voyage / openai / ollama
- `[chunk].size` / `.overlap` — RecursiveSplitter パラメータ
- `[live].update_interval_seconds` — LiveUpdater 更新間隔

優先順位: 環境変数 > `config.toml` > 既定値（`scripts/config.py` 内 `_MAPPINGS` 参照）。

### スキル単位の設定の切り分け

cocoindex を使う**他スキル**は、自前の TOML を持たせて切り分けられる。例:

```text
~/.config/
├── cocoindex/        # プラグイン共通（コード検索デフォルト）
│   ├── config.toml
│   └── secrets.env   # 全スキル共有の API キー
├── memory/
│   └── cocoindex.toml   # memory-record（agents repo）専用
└── <other-skill>/
    └── cocoindex.toml   # 別スキル用
```

memory-record は `templates/cocoindex.toml.example` を起動時に `~/.config/memory/cocoindex.toml` へ自動コピーし、独自の `MEMORIES_*` プレフィックス env で `main_memory.py` に渡す。

### 2. compose.yml の配置

DB 起動用の compose.yml はテンプレートから手動配置する:

```bash
cp ${CLAUDE_PLUGIN_ROOT}/templates/compose.yml ~/.config/cocoindex/compose.yml
```

## DB 起動

```bash
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

リモート VM（SSH 接続先など）で Postgres を運用し、Mac から `localhost:15432` にポート転送している構成でも動作する。その場合は Mac 側で `docker compose up` する必要はなく、VM 側での起動のみで充分。

## テーブル名の規則

インデックステーブル名は `hostname` プレフィックス付きで、ホストごとに衝突しない:

- `codeindex_<hostname>_<project>__code_chunks`
- 例: `codeindex_macbookpro_local_wonder_front__code_chunks`

`<hostname>` は `hostname` コマンド出力を `[^a-zA-Z0-9]` → `_` に置換して小文字化したもの。
`<project>` は `CLAUDE_PROJECT_DIR` のベース名（例: `/Users/miya/workspace/wonder/wonder-front` → `wonder_front`）を同じサニタイズ規則で変換したもの。

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

旧 `python main.py <src> --name <n> --live` は廃止。設定（chunk size 等）は `~/.config/cocoindex/config.toml` か起動時 env var で渡す。

### フロー名／テーブル名を変更したい場合

`INDEX_NAME` を変更すると新しい App・テーブルが生成される。旧テーブルとメタデータ行は自動削除されないため、手動でクリーンアップする:

```bash
OLD_FLOW=CodeIndex_<hostname>_<old_project>
docker exec cocoindex psql -U postgres -d postgres -c "
  DROP TABLE IF EXISTS ${OLD_FLOW}__code_chunks CASCADE;
  DROP TABLE IF EXISTS ${OLD_FLOW}__cocoindex_tracking CASCADE;
  DELETE FROM cocoindex_setup_metadata WHERE flow_name = '${OLD_FLOW}';
"
```

> Flow 名・テーブル名は全て小文字で保存される点に注意。

## 注意事項

### `INDEX_NAME` の扱い

`scripts/main.py` は `INDEX_NAME` 未指定時、`SOURCE_PATH` のベース名を使ってフロー名を生成する。`scripts/check.sh` / `scripts/search.py` / `hooks/session-start.sh` は `CLAUDE_PROJECT_DIR` または `--project-dir` のベース名から同じ規則でテーブル名を計算する。

通常は `SOURCE_PATH` に `CLAUDE_PROJECT_DIR` と同じパスを渡せばテーブル名が一致する。プロジェクトサブディレクトリを渡す場合（モノレポ一部のみインデックス等）は、`INDEX_NAME` で明示的にプロジェクト名を指定すること。

### halfvec + HNSW

埋め込み列は `halfvec(dim)` 型で保存し、ベクトルインデックスは `hnsw (embedding halfvec_cosine_ops)` を `declare_sql_command_attachment` で付与する。pgvector の `ivfflat` は 2000 dim 上限のため、Matryoshka 出力 dim=2048 を使う場合は HNSW 必須。
