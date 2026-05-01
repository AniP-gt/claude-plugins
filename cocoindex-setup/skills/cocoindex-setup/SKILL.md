---
name: cocoindex-setup
description: CocoIndex 共通の secrets/config ディレクトリ（~/.config/cocoindex/）の auto-provision 手順。複数プラグインの secrets hub として機能し、compass / episodic が fallback で参照する。
user-invocable: false
---

# cocoindex-setup（共通 secrets hub）

## このプラグインの責務

`~/.config/cocoindex/` の以下 2 ファイルを所有・auto-provision する:

- `~/.config/cocoindex/secrets.env` — `VOYAGE_API_KEY` 等の API キー
- `~/.config/cocoindex/config.toml` — 共通既定値（DB URL / embedding / chunk / rerank 等）

**このディレクトリは複数プラグイン共通の secrets hub** として機能する。`compass` / `episodic` などの下流プラグインは、

1. `~/.config/<plugin>/secrets.env`（プラグイン専用、最優先）
2. `~/.config/cocoindex/secrets.env`（このプラグインが所有、fallback）

の順で読み込む。プラグイン専用 secrets.env を空にしておけば、本ファイルから自動 fallback される。

> compose.yml / DB 起動は別プラグイン `pgvector-stack` が担う。本プラグインはコンテナ管理を行わない。

## 依存関係

- **必須**: `pgvector-stack` プラグイン（PostgreSQL コンテナ提供）
  - 未インストールの場合: `/plugin install pgvector-stack@hidetsugu-miya`

## 初回セットアップ

### auto-provision（推奨）

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check_config.sh
```

不足ファイルだけテンプレートからコピーする（既存ファイルは上書きしない）。

### 手動セットアップ

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/secrets.example.env ~/.config/cocoindex/secrets.env
cp ${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml ~/.config/cocoindex/config.toml
chmod 700 ~/.config/cocoindex
chmod 600 ~/.config/cocoindex/{secrets.env,config.toml}
```

配置後、`~/.config/cocoindex/secrets.env` の `VOYAGE_API_KEY` を設定する。

## 設定値の優先順位

下流プラグイン（compass / episodic）から見た優先順位（強い順）:

1. プロセス環境変数
2. `~/.config/<plugin>/secrets.env` または `~/.config/<plugin>/.env`（プラグイン専用）
3. `~/.config/<plugin>/cocoindex.toml`（プラグイン専用、ある場合）
4. **`~/.config/cocoindex/secrets.env`（このプラグイン所有）**
5. **`~/.config/cocoindex/config.toml`（このプラグイン所有）**
6. ハードコード既定値

## config.toml の主要キー

- `[database].url` — Postgres 接続先（プラグインが専用 DB URL を持たない場合の fallback）
- `[embedding].provider` / `.model` / `.dimension` — voyage / openai / ollama
- `[chunk].size` / `.overlap` — RecursiveSplitter パラメータ
- `[rerank].enabled` / `.model` / `.candidates` — voyage rerank 設定
- `[live].update_interval_seconds` — LiveUpdater 更新間隔
- `[embed].prefix_filepath` — 埋め込みにファイルパス prefix を付与

詳細は `templates/config.example.toml` を参照。

## トラブルシュート

- `VOYAGE_API_KEY` 未設定 → `compass` / `episodic` の embedding 実行が 401 で失敗する。`~/.config/cocoindex/secrets.env` に設定する
- 設定変更後も古い値が参照される → 各プラグインの `~/.config/<plugin>/secrets.env` で override されていないか確認する
