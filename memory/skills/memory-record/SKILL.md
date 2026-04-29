---
name: memory-record
description: Claude Codeのセッション終了時に会話履歴をCodexで要約し、エピソード記憶（時間軸つきの作業記録Markdown）として蓄積するスキル。過去セッションの記録検索・手動再生成・JSONL部分抽出（再調査）も行う。「作業記録を見せて」「このセッションの記録を作って」「過去のセッション要約を探して」「このセッションのBash実行を全部見せて」などで起動する。
argument-hint: [search-keyword | regenerate <session-id> | extract <session-id> <subcommand>]
---

# Memory Record Skill

Claude Code の各セッション終了時に、会話履歴を要約して**エピソード記憶（時間軸つきの作業記録 Markdown）**として蓄積するスキル。`memory` プラグインが提供する `SessionEnd` hook から自動起動し、生成物は `<memories_dir>/raw/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md`（既定 `/Volumes/memory`、`~/.config/memory-record/config.toml` で変更可）に保存される。

共有が未マウント（外出時など）の場合は自動で `~/.local/share/memory-record/raw-staging/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md` に退避し、次回セッション開始時に共有が見えていれば `sync-pending.sh` が正規パスへ自動移送する。Codex は意識せず、解決済みパスにそのまま書き込む。

仕組み・自動生成パイプライン・ファイル配置・レポート構造・トラブルシューティングは `references/architecture.md` を参照。設定例は `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml`。

> プラットフォーム前提: 通知（osascript）・Terminal 起動・SMB マウント関連は macOS 専用。コマンドが見つからない環境では各処理が自動的にスキップされ、Raw 生成本体（codex 要約）はログだけ残してバックグラウンドで進む。

## このスキルの位置付け（記憶レイヤー）

エージェントの記憶は性質ごとに別レイヤーへ分離する。本スキルは **エピソード記憶（過去の出来事の記録）** を担当する。他レイヤーと混同しないこと。

| レイヤー | 種別 | 担当 | 用途 |
|---|---|---|---|
| 意味記憶 / 手続き記憶 | 長期有効な事実・ルール | auto memory（`memory/MEMORY.md` 配下） | ユーザー好み・コーディング規約・繰り返し参照する事実 |
| 意思決定記録 | 不可逆な判断の根拠 | `adr` skill | 技術選定・アーキテクチャ判断の永続化 |
| エピソード記憶（Raw） | 時間軸つきの出来事 | **本スキル**（memories/raw/YYYY-MM-DD/） | 過去セッションでの作業内容・判断・残課題（不変・追記専用） |
| エピソード記憶（Wiki） | Raw を統合した二次資産 | `memory-wiki` skill（memories/wiki/） | プロジェクト通史・概念・索引（再生成可） |
| 教訓・改善 | エピソードからの抽出 | `retrospective` skill | フェーズ完了後に skills/rules を更新 |

**運用原則**:

- 本スキルは「いつ・何をしたか」を保存する。普遍的なルール化が必要なら `retrospective` で意味/手続き記憶へ昇華する
- 記録は出典（`source_jsonl`）と状態（`status`）を必ず持つ。古い記録は `superseded` へ降格し、ないより悪い状態にしない
- 再生成や上書きが起きたら、旧版との関係を `supersedes` フィールドで明示する

## 使い方

### 過去記録の検索

検索は **`memory-search` skill に委譲する**（Raw + Wiki 両方を対象に、scope/status フィルタ付きでベクトル検索する）。

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "<自然言語クエリ>" \
    --top 10 --scope all --format markdown
```

詳細は `memory-search` skill（同プラグイン同梱）を参照。Claude API（外部アプリ）からの利用は `${CLAUDE_PLUGIN_ROOT}/skills/memory-search/references/api-usage.md`。

**完全一致トークン（session_id / 固有名詞 / フロントマター tag 等）で厳密に絞り込みたい場合のフォールバック**として grep を使う:

```bash
grep -rl "<keyword>" /Volumes/memory/ | head
```

検索ヒット時は該当ファイルの frontmatter を提示し、ユーザーの意図に合えば本文を読み込む。**`status: deprecated` または `status: superseded` のレポートは原則提示しない**（明示的に「過去版を見たい」と言われた場合のみ。`memory-search --include-superseded` で含められる）。

### 再調査（JSONL部分抽出）

レポートから得られる情報で足りず、過去セッションの特定箇所を掘り下げたいとき、`scripts/session-extract.py` を使う。**JSONL全体を読まずに必要な情報だけを切り出せる**ため、コンテキスト溢れを回避しながら深掘りできる。

レポートのフロントマター `source_jsonl` をそのまま引数に渡す:

```bash
JSONL="<report の source_jsonl 値>"
SE="${CLAUDE_PLUGIN_ROOT}/scripts/record/session-extract.py"

# セッションメタ情報（まずこれで全体像を把握）
$SE "$JSONL" meta

# 読み込んだファイル一覧（何を参照したか）
$SE "$JSONL" list-reads

# 編集したファイル一覧（何を変更したか）
$SE "$JSONL" list-edits

# Bash 実行一覧
$SE "$JSONL" list-bash

# ユーザー指示・AskUserQuestion・git commit の時系列
$SE "$JSONL" list-decisions

# キーワード周辺を圧縮Markdownで抽出（AIに渡しやすい形）
$SE "$JSONL" grep "REQ-002" --context 3 --compress

# 特定ツールの全呼び出しを本文付きで抽出
$SE "$JSONL" tool Edit --with-result --compress

# 時刻範囲で抽出
$SE "$JSONL" range --from 10:00 --to 10:30 --compress

# 指定メッセージUUID周辺
$SE "$JSONL" around <message_uuid> --window 10 --compress
```

サブコマンド一覧:

- `meta` — セッションメタ情報とツール呼び出し数ランキング
- `list-reads` / `list-edits` / `list-bash` — 各ツールの呼び出し CSV
- `list-tools [--name N]` — 全 tool_use 一覧
- `list-decisions` — 決定系イベント（ユーザー指示・AskUser・commit）
- `grep <keyword> [--context N]` — キーワード周辺抽出
- `tool <name> [--with-result]` — 特定ツール抽出
- `range --from HH:MM --to HH:MM` — 時刻範囲抽出
- `around <uuid> [--window N]` — 指定メッセージ周辺抽出

`--compress` を付けると `jsonl-to-markdown.py` 同等の圧縮（tool_result/tool_use 削減）を適用する。AIに渡す場合は `--compress` 推奨、人間が詳細確認する場合は無しが良い。

#### 再調査のワークフロー例

```bash
# 1. まず meta で全体把握
$SE "$JSONL" meta

# 2. 決定履歴から流れをつかむ
$SE "$JSONL" list-decisions

# 3. 気になるキーワード周辺を掘る
$SE "$JSONL" grep "REQ-002" --context 5 --compress

# 4. 必要に応じて時刻範囲で全文を確認
$SE "$JSONL" range --from 08:05 --to 08:15 --compress
```

### 手動再生成

特定セッションを再要約したい場合:

```bash
# JSONLパスを特定してhook.pyに流す
printf '%s' '{"session_id":"<UUID>","cwd":"<CWD>","transcript_path":"<JSONL>"}' \
    | "${CLAUDE_PLUGIN_ROOT}/scripts/record/hook.py"
```

既存レポートは上書きされる。再生成時は Codex 側で旧版のフロントマター `status` を `superseded` に更新し、新レポートの `supersedes` に旧版へのパス（または旧 `updated_at`）を記録する。

## 初期設定

インストール直後の前提確認・config.toml 作成・マウントポイント準備・cocoindex 連携起動・初回 Raw 生成テストの手順は `memory-setup` skill にまとめてある。最初は `memory-setup` を参照すること。

## 関連スキル

- `memory-setup` — プラグイン初期設定の手順
- `memory-search` — Raw + Wiki に対するベクトル検索（Claude API からも利用可）
- `memory-wiki` — Raw を統合した Wiki 生成（ingest-queue 経由で自動連携）
- `adr` — 意思決定記録（不可逆な判断の永続化レイヤー）
- `retrospective` — フェーズ完了振り返り（エピソードから skills/rules への昇華）
