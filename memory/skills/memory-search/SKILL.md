---
name: memory-search
description: エピソード記憶（memories/raw/{session,web,minutes} + memories/wiki）に対する全文ベクトル検索 skill。cocoindex バックエンドでセマンティック検索し、scope（session/web/minutes/wiki/all）と status（active のみ / superseded 含む）でフィルタする。Claude Code 内からも、Claude API 経由で外部アプリからも利用できる。「memoriesから○○を検索して」「過去のセッションで○○を扱ったものを探して」「web だけで○○を検索」等で起動する。
argument-hint: <query> [--top N] [--scope session|web|minutes|wiki|all] [--include-superseded] [--format json|markdown] [--no-dedupe] [--low-score-threshold N]
---

# Memory Search Skill

`memories/` 配下（Raw（kind: session / web / minutes）+ Wiki）に対する全文ベクトル検索を提供する薄い skill。cocoindex プラグインを内部で呼び出し、結果に scope/status フィルタを適用して返す。

## 目的

- エピソード記憶（過去セッション要約・URL アーカイブ・議事録 + Wiki ページ）を自然言語クエリで横断検索する
- 検索ロジックを skill として独立化し、Claude Code・Claude API（外部アプリ）両方から同じインターフェースで利用できるようにする
- `recording` skill から検索責務を切り離し、SRP（単一責任）を守る

## 制約

- **副作用なし**（読み取り専用）。memories 配下や DB を書き換えない
- **stdin/stdout 完結**: 入力＝CLI 引数、出力＝stdout（Markdown または JSON）
- **依存**: PostgreSQL（localhost:15432、cocoindex プラグインの compose.yml で立ち上がるコンテナを共用）が起動していること。memory プラグイン専用 venv（`memory/scripts/.venv`）と memory データベース（`postgres://...:15432/memory`）は `setup_db.sh` と初回 `cocoindex update` で自動構築される
- **インデックスは recording 側で管理**: SessionEnd hook 起動時に runner.sh がインデックスを更新する（kind: session 経路）。kind: web / minutes は保存後の cocoindex 自動再インデックスに任せる。本 skill はインデックス構築は行わない
- **scope フィルタは post-process**: cocoindex 自体に scope 概念はないため、結果取得後にパスでフィルタする
- **既定で deprecated/superseded を除外**: 古い記録のヒットを避ける。明示的に `--include-superseded` を指定したときのみ含める
- **既定で同一ファイル内の chunk dedupe**: cocoindex は chunk 単位で返すため、同一ファイル内の異なる chunk が top N を埋めて候補多様性が失われる。既定では filename ベースで dedupe し、最高スコアの chunk のみ採用する。`--no-dedupe` で旧挙動（chunk 単位）に戻せる
- **弱ヒット時の再クエリヒント**: トップヒットのスコアが `--low-score-threshold`（既定 0.3）未満なら stderr に再クエリ案を出す。stdout（検索結果）は汚染しない。`--low-score-threshold 0` で無効化できる

## 完了条件

- 指定クエリに対する検索結果（最大 `--top` 件）が指定 `--format` で stdout に出力されている
- ヒットなしの場合は「検索結果なし」を返す（エラーではない）

## 入力パラメータ

CLI 引数として受け取る（位置引数 1 + オプション引数）:

| 引数 | 必須 | 既定 | 説明 |
|---|---|---|---|
| `<query>` | ✓ | — | 自然言語クエリ |
| `--top N` | | 10 | 返す件数（ファイル単位、dedupe 後） |
| `--scope session\|web\|minutes\|wiki\|all` | | all | 検索対象を絞る |
| `--include-superseded` | | (false) | superseded/deprecated レポートも含める |
| `--format json\|markdown` | | markdown | 出力形式 |
| `--no-dedupe` | | (false) | 同一ファイル内の異なる chunk も全て返す（chunk 単位） |
| `--low-score-threshold N` | | 0.3 | トップスコアがこの値未満なら stderr に再クエリヒントを出す（0 以下で無効化） |

環境変数（任意）:

- `MEMORIES_DIR`: memories ディレクトリの絶対パス（既定: `/Volumes/memory`）
- `MEMORY_DATABASE_URL`: memory 専用 PostgreSQL 接続 URL（既定: `postgres://postgres:postgres@localhost:15432/memory`）。`~/.config/memory/.env` でも設定可能
- `MEMORIES_EMBEDDING_MODEL`: memories 検索用の埋め込みモデル（既定: `voyage-3-large`）。インデックス構築側（`recording` の `main_memory.py`）と同じ値である必要がある（モデル変更時はテーブル drop + 全件 re-embed が必要）
- `MEMORIES_EMBEDDING_PROVIDER`: 埋め込みプロバイダー（既定: `voyage`）
- `VOYAGE_API_KEY`: voyage embedding / rerank API キー。`~/.config/memory/secrets.env` で設定可能。未設定の場合は `~/.config/cocoindex/secrets.env` を fallback で読む

## 返却値

stdout に以下を出力する。

### Markdown 形式（既定）

```markdown
### 1. <title>  _(score: 0.823)_
- **path**: `/Volumes/memory/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md`
- **status**: active  **tags**: hook, recording
- **snippet**: <冒頭スニペット 200字>

### 2. ...
```

### JSON 形式

```json
[
  {
    "score": 0.823,
    "path": "/Volumes/memory/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md",
    "snippet": "...",
    "frontmatter": {
      "kind": "session",
      "title": "...",
      "status": "active",
      "tags": "...",
      "session_id": "...",
      "source_jsonl": "..."
    }
  }
]
```

## 使い方

### Claude Code 内から

```bash
# 標準的な検索（Markdown）
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "セッション要約の保存先"

# Wiki だけ、JSON、上位 5 件
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "コミット規約" \
    --scope wiki --top 5 --format json

# kind: web だけで絞る
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "Jina Reader 仕様" --scope web

# 過去版も含めて検索
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "recording" \
    --include-superseded

# 直近の作業を時系列で一覧（セマンティック検索ではない）
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind session --top 5
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind session --project agents --days 7
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind web --top 10 --format json
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind minutes --top 10
```

メインコンテキストから呼ぶ場合は `cocoindex:cocoindex-runner` サブエージェントへ委譲してトークンを節約してもよいが、本 skill は出力が小さいので直接呼びでも問題ない。

`recent.sh` はベクトル検索を使わず、`raw/<kind>/` 配下の日付ディレクトリ＋ファイル名タイムスタンプで時系列ソートする補助スクリプト。「直近の作業を見せて」「今日のセッション一覧」「最近アーカイブした URL」のような、意味検索ではなく時系列で取り出したい場面で使う。`--kind` 既定は `session`、`web` / `minutes` / `all` も指定可能。`--project` で絞り込み（kind=session で意味あり）、`--days` で期間制限、`--format paths` でパスのみ抽出も可能。

### Claude API（外部アプリ）から

`references/api-usage.md` に Tool Use 経由のサンプルあり。要点:

1. Bash MCP もしくは独自の shell 実行ツールで `${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh`（または絶対パス `~/.claude/plugins/cache/hidetsugu-miya/memory/<version>/scripts/search/search.sh`）を起動
2. `--format json` を指定して結果を JSON で受け取り、アプリ側で構造化処理する
3. memories ディレクトリを別ホストに置く場合は `MEMORIES_DIR` 環境変数で上書き

## 関連スキル

- `recording` — Raw 生成（kind: session は SessionEnd hook で自動、kind: web / minutes は手動）。Wiki 統合パイプラインも recording 経由で自動起動（詳細は `recording/references/wiki.md`）
- `cocoindex:cocoindex-code-search` — 一般的なコードベース検索（本 skill は memories 専用ラッパー）

## トラブルシューティング

- `connection refused: localhost:15432` → PostgreSQL 起動。`docker compose -f ~/.config/cocoindex/compose.yml up -d`
- `relation "memoryindex_..." does not exist` → 初回セットアップ未実施。`memory/scripts/setup_db.sh` を実行 → `cocoindex update -f memory/scripts/recording/main_memory.py:MemoryIndex_<host>_<name>` でインデックスを構築する
- インデックスが空 / 古い → SessionEnd hook が走っていない可能性。手動更新は `cocoindex:cocoindex-setup` 参照
- `--scope wiki` で常に空 → wiki 配下にまだファイルがない（wiki-runner 未稼働、または kind: session/web/minutes の Raw がない）
- `--scope web` / `--scope minutes` で常に空 → 該当 kind の記録がまだない（`recording` skill から手動保存する）
