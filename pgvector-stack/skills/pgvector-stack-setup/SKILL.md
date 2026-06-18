---
name: pgvector-stack-setup
description: pgvector 搭載 PostgreSQL コンテナの起動手順。compass / episodic などの下流プラグインで利用する共有 DB 基盤。
user-invocable: false
---

# pgvector-stack セットアップ

## 共通情報

- **コンテナ名**: `cocoindex`（compass の `setup_db.sh` および episodic の `setup_db.sh` が `docker exec -i cocoindex` で参照するハードコード）
- **公開ポート**: ホスト側 `15432` → コンテナ側 `5432`
- **イメージ**: `pgvector/pgvector:pg17`
- **配置先**: `~/.config/cocoindex/compose.yml`（複数プラグイン共通の設定 hub）
- **永続データ**: docker volume `pgdata`

## 初回セットアップ

### 1. compose.yml の配置

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/compose.yml ~/.config/cocoindex/compose.yml
```

### 2. コンテナ起動

```bash
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

### 3. 動作確認

```bash
# コンテナ起動確認
docker ps --format '{{.Names}}' | grep '^cocoindex$'

# pgvector 拡張は postgres DB に最初は未作成。下流プラグインの setup_db.sh が
# 専用 database に CREATE EXTENSION vector を冪等実行する。
docker exec cocoindex psql -U postgres -l
```

## 下流プラグインとの関係

`pgvector-stack` は DB 基盤のみを提供する。各プラグインは専用 database を分けて使用する:

- `compass` プラグイン: `compass` database（`compassindex_*__chunks` テーブル）
- `episodic` プラグイン: `memory` database（`memoryindex_*__chunks` テーブル）

各プラグインの `setup_db.sh` が `CREATE DATABASE`（冪等）と `CREATE EXTENSION vector`（冪等）を実行する。

## 停止・データ削除

```bash
# 停止のみ
docker compose -f ~/.config/cocoindex/compose.yml down

# データも削除（注意: 全 database が消える）
docker compose -f ~/.config/cocoindex/compose.yml down -v
```

## アンインストール

コンテナ `cocoindex`・ボリューム `pgdata`・`~/.config/cocoindex/compose.yml` を一括削除する:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/uninstall.sh            # 確認プロンプトあり
bash ${CLAUDE_PLUGIN_ROOT}/scripts/uninstall.sh --dry-run  # 削除予定の確認のみ
bash ${CLAUDE_PLUGIN_ROOT}/scripts/uninstall.sh --yes      # 確認なし（非対話シェルでは必須）
```

- **警告**: ボリューム削除で compass / episodic を含む全 database が消える。下流プラグインを使い続けるなら実行しない
- `secrets.env` / `config.toml`（cocoindex-setup 所有）には触れない。`~/.config/cocoindex/` は空になった場合のみ削除される
- プラグイン本体の削除は `/plugin uninstall pgvector-stack@hidetsugu-miya`
