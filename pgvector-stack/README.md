# pgvector-stack

pgvector 搭載 PostgreSQL コンテナを提供する最小プラグイン。`compass` / `memory` など下流プラグインの DB 基盤として共有する。

## インストール

```text
/plugin install pgvector-stack@hidetsugu-miya
```

## セットアップ

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/compose.yml ~/.config/cocoindex/compose.yml
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

## 構成

- コンテナ名: `cocoindex`（下流プラグインが `docker exec -i cocoindex` で参照するため固定）
- ポート: `15432:5432`
- イメージ: `pgvector/pgvector:pg17`
- 永続データ: docker volume `pgdata`

詳細は `skills/pgvector-stack-setup/SKILL.md` を参照。
