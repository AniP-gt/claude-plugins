---
name: episodic-search
description: 過去の記録（セッション・Web・議事録・日記・Wiki）を検索したいときに使用する。ベクトル検索で関連エピソードを発見する。「過去の記録を検索して」「memoriesから○○を探して」「過去のセッションで○○を探して」等で起動する
argument-hint: <query> [--top N] [--scope session|web|minutes|diary|wiki|all] [--include-superseded] [--format json|markdown] [--no-dedupe] [--low-score-threshold N]
context: fork
effort: low
---

# Episodic Search

過去の記録（`memories/raw/{session,web,minutes,diary}` + `memories/wiki`）をベクトル検索する skill。cocoindex バックエンドで dense + BM25 RRF → voyage rerank のハイブリッド検索を実行する。`/Volumes/memory` への Grep/Glob 直接走査は禁止（chunk 単位の dense/BM25/rerank を再現できないため）。

## 入力

$ARGUMENTS

## ワークフロー

### Step 1: search.sh でベクトル検索

```bash
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/search.sh" "<query>"
```

- 既定: `--top 10 --scope all --format markdown`、status=active のみ
- 対象が明確なら `--scope session|web|minutes|diary|wiki` で絞る
- 構造化処理が必要なら `--format json`

### Step 2: 結果の評価

- 各ヒットの `score` / `snippet` / `path` を確認する
- トップスコアが 0.3 未満なら stderr に再クエリヒントが出る → Step 4 へ
- 期待 kind と異なる結果ばかりなら `--scope` を絞って Step 1 を再実行する

### Step 3: 必要な実ファイルを Read

- 精査が必要なヒットの `path` のみ `Read` で開く
- snippet で十分な質問には Read しない（コンテキスト節約）
- `/Volumes/memory` 配下を Grep/Glob で走査しない

### Step 4: 再クエリ判断

ヒットなし / 弱ヒット時の打ち手:

- 固有名詞 → 一般語へ置き換え（例: `feature-dev effort` → `スキル 設定値 妥当性`）
- 動詞化（例: `effort 設定` → `effort を変更する議論`）
- 古い記録も含めたい場合は `--include-superseded`
- 意味検索でなく時系列で取り出したい場合は `recent.sh --kind session|web|minutes|diary|all` を併用

```bash
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/recent.sh" --kind session --top 5
```

## 出力

- ヒットした path + score + snippet を要約して報告する
- Read した内容を引用する場合は `path:行番号` 形式でリンクする
- ヒットなしの場合は「検索結果なし」と再クエリ案を提示する

## 補足

### 入力パラメータ

| 引数 | 必須 | 既定 | 説明 |
|---|---|---|---|
| `<query>` | ✓ | — | 自然言語クエリ |
| `--top N` | | 10 | 返す件数（dedupe 後、ファイル単位） |
| `--scope session\|web\|minutes\|diary\|wiki\|all` | | all | 検索対象 kind |
| `--include-superseded` | | false | superseded/deprecated も含める |
| `--format json\|markdown` | | markdown | 出力形式 |
| `--no-dedupe` | | false | 同一ファイル内 chunk も全て返す |
| `--low-score-threshold N` | | 0.3 | 低スコア時の stderr ヒント閾値（0 以下で無効） |

環境変数（任意）:

- `MEMORIES_DIR`: memories ルート（既定 `/Volumes/memory`）
- `EPISODIC_DATABASE_URL`: episodic DB 接続 URL（`setup_db.sh` が `~/.config/episodic/.env` を生成）
- `MEMORIES_EMBEDDING_MODEL` / `MEMORIES_EMBEDDING_PROVIDER`: インデックス側と同一値必須（既定 `voyage-3-large` / `voyage`）
- `VOYAGE_API_KEY`: `~/.config/episodic/secrets.env` で設定（fallback: `~/.config/cocoindex/secrets.env`）
- `UV_PROJECT_ENVIRONMENT`: uv venv 配置先（既定 `~/.cache/episodic/venv`）

### 返却値（JSON 形式時）

```json
[
  {
    "score": 0.823,
    "path": "/Volumes/memory/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md",
    "snippet": "...",
    "frontmatter": { "kind": "session", "title": "...", "status": "active", "tags": "...", "session_id": "...", "source_jsonl": "..." }
  }
]
```

### 制約

- 副作用なし（読み取り専用）
- インデックス構築は本 skill の責務外（`episodic-recording` の Stop hook 経路 / cocoindex 自動再インデックスに任せる）
- scope フィルタは post-process（cocoindex 側に scope 概念なし）
- 既定で同一ファイル内 chunk dedupe（`--no-dedupe` で無効化）

### Claude API（外部アプリ）から

`references/api-usage.md` 参照。要点: Bash MCP で `search.sh --format json` を起動し、JSON を構造化処理する。`MEMORIES_DIR` で別ホストにも対応。

### トラブルシューティング

- `connection refused: localhost:15432` → `docker compose -f ~/.config/cocoindex/compose.yml up -d`
- `relation "episodicindex_..." does not exist` → 初回未セットアップ。`episodic/scripts/setup_db.sh` 実行 → `cocoindex update -f episodic/recording/main_episodic.py:EpisodicIndex_<host>_episodic`
- インデックスが空 / 古い → Stop hook が走っていない可能性。手動更新は `cocoindex:cocoindex-setup` 参照
- `--scope wiki` で常に空 → wiki 配下に未生成（Raw 蓄積待ち）
- `--scope web|minutes|diary` で常に空 → 該当 kind の Raw 未保存（`episodic-recording` から手動保存）

### 関連 skill

- `episodic-recording` — Raw 生成（session は Stop hook 自動、web/minutes/diary は手動）。Wiki 統合も連動
