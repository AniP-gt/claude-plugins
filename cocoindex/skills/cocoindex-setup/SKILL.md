---
name: cocoindex-setup
description: CocoIndexの環境セットアップ手順。初回設定・DB起動・設定ファイルの管理方法。
user-invocable: false
---

# CocoIndex セットアップ

## 共通情報

- **スクリプト**: `${CLAUDE_PLUGIN_ROOT}/scripts/`
- **ユーザー設定**: `~/.config/cocoindex/.env`
- **DB**: `cocoindex` コンテナ（pgvector 搭載 Postgres、ポート `15432`）
- **compose.yml**: `${CLAUDE_PLUGIN_ROOT}/templates/compose.yml` を `~/.config/cocoindex/` に配置して起動する

## 初回セットアップ

### 1. 設定ファイル（.env）の配置

`~/.config/cocoindex/.env` は、セッション開始フック（`hooks/session-start.sh`）およびヘルスチェック（`scripts/check.sh`）の初回実行時にテンプレートから自動コピーされる。

手動セットアップする場合:

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/.env.example ~/.config/cocoindex/.env
```

配置後、`~/.config/cocoindex/.env` の `VOYAGE_API_KEY` を設定する。

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

同じ構築コマンドを再実行すると差分更新される（cocoindex の FlowLiveUpdater が追跡テーブルで差分管理）。

### フロー名／テーブル名を変更したい場合

`--name` を変更すると新しいフロー・テーブルが生成される。旧フローのテーブルとメタデータ行は自動削除されないため、手動でクリーンアップする:

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

### `--name` の扱い

`scripts/main.py` は `--name` 未指定時、`source_path` のベース名を使ってフロー名を生成する。`scripts/check.sh` / `scripts/search.py` / `hooks/session-start.sh` は `CLAUDE_PROJECT_DIR` または `--project-dir` のベース名から同じ規則でテーブル名を計算する。

通常は `main.py` の引数に `CLAUDE_PROJECT_DIR` と同じパスを渡せばテーブル名が一致する。プロジェクトサブディレクトリを渡す場合（例: モノレポの一部だけインデックス）は、`--name` で明示的にプロジェクト名を指定すること。
