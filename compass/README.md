# compass

コードベースのセマンティック検索プラグイン。pgvector + voyage embedding + voyage rerank で関連コードを発見する。専用 DB `compass`、テーブル `compassindex_*__chunks`。cocoindex 1.0 LiveUpdater 対応。

## インストール

```text
/plugin install pgvector-stack@hidetsugu-miya
/plugin install cocoindex-setup@hidetsugu-miya
/plugin install compass@hidetsugu-miya
```

## セットアップ

```bash
# 1. PostgreSQL コンテナ起動（pgvector-stack）
docker compose -f ~/.config/cocoindex/compose.yml up -d

# 2. 共通 secrets hub の auto-provision（cocoindex-setup）
bash ~/.claude/plugins/cache/hidetsugu-miya/cocoindex-setup/scripts/check_config.sh
# その後 ~/.config/cocoindex/secrets.env の VOYAGE_API_KEY を設定

# 3. compass 専用 DB / 設定の作成
bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup_db.sh

# 4. 初回インデックス構築
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')
PROJECT_NAME=$(basename "$PWD")
INDEX_NAME=$(echo "${HOST_PREFIX}_${PROJECT_NAME}" | sed 's/[^a-zA-Z0-9]/_/g')
cd ${CLAUDE_PLUGIN_ROOT}/scripts \
  && SOURCE_PATH="$PWD" \
     PATTERNS="**/*.py,**/*.rb,**/*.ts" \
     uv run cocoindex update -f "main.py:CompassIndex_${INDEX_NAME}"

# 5. 検索
bash ${CLAUDE_PLUGIN_ROOT}/scripts/search.sh "認証ロジック"
```

詳細は `skills/compass-setup/SKILL.md` / `skills/compass-search/SKILL.md` を参照。

## 構成

- 専用 DB: `compass`（pgvector-stack の `cocoindex` コンテナ内）
- テーブル: `compassindex_<host>_<project>__chunks`
- App: `CompassIndex_<host>_<project>`
- 埋め込み列: `halfvec(1024)` + HNSW index（halfvec_cosine_ops）
- 全文検索インデックス: `chunk_tsv` 生成列 + GIN index（ハイブリッド検索の余地）
- LiveUpdater: SessionStart hook で `cocoindex update -L` 起動、SessionEnd hook で停止
