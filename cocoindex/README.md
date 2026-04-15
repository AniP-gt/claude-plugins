# cocoindex

コードベースのベクトルインデックス構築・検索プラグイン。自然言語クエリで関連コードのエントリーポイントを発見する。

## 概要

- PostgreSQL + pgvector にコードチャンクの埋め込みを保存
- 自然言語クエリでコードベースをベクトル検索
- 埋め込みモデルは Ollama（ローカル）/ OpenAI / Voyage AI から選択可能

## セットアップ

### 1. 依存サービスの起動

PostgreSQL（pgvector付き）が必要。OrbStack VM 環境では:

```bash
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

### 2. 埋め込みモデルの選択

`~/.config/cocoindex/.env` で設定する。初回起動時にテンプレートから自動生成される。

#### Ollama（ローカル・推奨）

データが外部に送信されないため業務コードに安全。

```bash
brew install --cask ollama
ollama pull nomic-embed-text
```

```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_ADDRESS=http://localhost:11434
```

Ollama はインデックス構築・検索時に自動起動/停止されるため、常駐不要。

**モデル選択の目安:**

| メモリ | モデル | サイズ | 特徴 |
|--------|--------|--------|------|
| 8GB | `nomic-embed-text` | 274MB | 軽量・バランス型 |
| 16GB以上 | `manutic/nomic-embed-code` | 7.5GB | コード検索特化、精度高 |
| 16GB以上 | `qwen3-embedding:8b` | ~5GB | 汎用 MTEB 最高スコア |

> 精度を優先する場合は英語クエリの方が結果が良くなりやすい。

#### OpenAI

APIデータはデフォルトでモデル学習に使われない。

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

#### Voyage AI

デフォルトでは学習に使用される。ダッシュボードからオプトアウト可能（支払い登録が必要）。

```env
EMBEDDING_PROVIDER=voyage
VOYAGE_API_KEY=...
EMBEDDING_MODEL=voyage-code-3
```

### 3. インデックス構築

```bash
HOST_PREFIX=$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')

# Ruby on Rails プロジェクトの例
cd ~/.claude/plugins/cocoindex/scripts && uv run python main.py /path/to/project \
  --name "${HOST_PREFIX}_project_name" \
  --patterns "**/*.rb,**/*.erb" \
  --exclude "**/tmp/**,**/log/**,**/vendor/**"

# React Native / TypeScript プロジェクトの例
cd ~/.claude/plugins/cocoindex/scripts && uv run python main.py /path/to/project \
  --name "${HOST_PREFIX}_project_name" \
  --patterns "**/*.ts,**/*.tsx,**/*.js" \
  --exclude "**/node_modules/**,**/coverage/**,**/__mocks__/**"
```

**オプション:**

| オプション | 説明 |
|-----------|------|
| `--name` | テーブル名に使うプロジェクト識別子（必須、`hostname_プロジェクト名` 形式） |
| `--patterns` | 対象ファイルパターン（カンマ区切り、デフォルト: `**/*.rb`） |
| `--exclude` | 追加除外パターン（カンマ区切り） |
| `--no-default-excludes` | `.git`, `node_modules`, `.venv` 等のデフォルト除外を無効化 |

同じコマンドを再実行するとインデックスが更新される。

## 使い方

Claude Code のセッション中に自然言語で検索を依頼する:

```
cocoindex を使って「ユーザー登録処理」を調べて
cocoindex で "authentication login" を検索して
```

内部では `cocoindex-runner` サブエージェントが以下を自動実行する:

1. Ollama 起動（`EMBEDDING_PROVIDER=ollama` のときのみ）
2. PostgreSQL 接続・インデックス確認
3. インデックス未構築なら自動構築
4. ベクトル検索を実行して結果を返す
5. Ollama 停止（このセッションが起動した場合のみ）

## ヘルスチェック

```bash
CLAUDE_PROJECT_DIR=/path/to/project \
  bash ~/.claude/plugins/cocoindex/scripts/check.sh
```

PostgreSQL 接続状態とインデックスのチャンク数を確認できる。

## テーブル命名規則

テーブル名にはホスト名プレフィックスが付く:

```
codeindex_{hostname}_{project}__code_chunks
```

例: `codeindex_tk_local_every_pharumo_com__code_chunks`

同一の PostgreSQL を複数マシンで共有しても競合しない。
