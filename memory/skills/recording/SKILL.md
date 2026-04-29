---
name: recording
description: エピソード記憶（kind: session / web / minutes）の保存・参照・再調査を担当する skill。session（Claude Code セッション要約）は SessionEnd hook で自動生成される。web（外部 URL アーカイブ）と minutes（議事録）は本 skill から手動で保存する。「webページを記録して」「議事録を残して」「過去のセッション要約を探して」「このセッションの Bash 実行を全部見せて」などで起動する。
argument-hint: [session regenerate <sid> | session extract <sid> <subcmd> | web | minutes]
---

# Recording Skill

エピソード記憶（時間軸つきの不変・追記専用記録）の **保存・参照・再調査** を担当する skill。kind は次の 3 種類で、すべて `<memories_dir>/raw/<kind>/YYYY-MM-DD/...md` に保存される。

| kind | 保存契機 | 用途 |
|---|---|---|
| `session` | SessionEnd hook（自動） | Claude Code 1セッションの要約レポート |
| `web` | 本 skill 経由（手動） | 外部 URL の Markdown アーカイブ（Jina Reader 経由） |
| `minutes` | 本 skill 経由（手動） | 議事録・指示・合意の時系列ログ |

> プラットフォーム前提: 通知（osascript）・Terminal 起動・SMB マウント関連は macOS 専用。コマンドが見つからない環境では各処理が自動的にスキップされ、保存本体はログだけ残してバックグラウンドで進む。

## 記憶レイヤーの位置付け

エージェントの記憶は性質ごとに別レイヤーへ分離する。本 skill は **エピソード記憶（過去の出来事の記録）** を担当する。他レイヤーと混同しないこと。

| レイヤー | 担当 | 用途 |
|---|---|---|
| 意味記憶 / 手続き記憶 | auto memory（`memory/MEMORY.md` 配下） | ユーザー好み・コーディング規約・繰り返し参照する事実 |
| 意思決定記録 | `adr` skill | 技術選定・アーキテクチャ判断の永続化 |
| **エピソード記憶（kind: session）** | 本 skill（自動）+ `memories/raw/sessions/` | 過去セッションでの作業内容・判断・残課題 |
| **エピソード記憶（kind: web）** | 本 skill（手動）+ `memories/raw/web/` | 外部 URL のスナップショット |
| **エピソード記憶（kind: minutes）** | 本 skill（手動）+ `memories/raw/minutes/` | 議事録・指示・合意ログ |
| エピソード記憶（Wiki） | `memory-wiki` skill（自動連携、再生成可） | プロジェクト通史・参照索引・議事索引 |
| 教訓・改善 | `retrospective` skill | フェーズ完了後に skills/rules を更新 |

**運用原則**:

- 本 skill は「いつ・何をしたか／参照したか／決めたか」を保存する。普遍的なルール化が必要なら `retrospective` で意味/手続き記憶へ昇華する
- 記録は `kind` と `status` を必ず持つ。古い記録は `superseded` へ降格し、ないより悪い状態にしない
- session の再生成・上書きが起きたら、旧版との関係を `supersedes` フィールドで明示する

## 保存先と命名規則

設定 `<memories_dir>` 既定 `/Volumes/memory`、`~/.config/recording/config.toml` で変更可。

```text
<memories_dir>/raw/
├── sessions/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md     # kind: session
├── web/YYYY-MM-DD/HHMMSS_<slug>.md                   # kind: web
└── minutes/YYYY-MM-DD/HHMMSS_<slug>.md               # kind: minutes
```

session 共有が未マウント（外出時など）の場合は自動で `~/.local/share/recording/raw-staging/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md` に退避し、次回セッション開始時に共有が見えていれば `sync-pending.sh` が `raw/sessions/` 配下へ自動移送する。web / minutes は手動経路で常に共有が見えている前提のため staging を使わない。

## 使い方

### 1. 過去記録の検索

検索は **`memory-search` skill に委譲する**（Raw + Wiki 両方を対象に、scope/status フィルタ付きでベクトル検索する）。

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "<自然言語クエリ>" \
    --top 10 --scope all --format markdown

# scope は session / web / minutes / wiki / all から選べる
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "Jina" --scope web
```

詳細は `memory-search` skill（同プラグイン同梱）を参照。Claude API（外部アプリ）からの利用は `${CLAUDE_PLUGIN_ROOT}/skills/memory-search/references/api-usage.md`。

時系列で直近を見る場合:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind session --top 5
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind web --top 10
"${CLAUDE_PLUGIN_ROOT}/scripts/search/recent.sh" --kind minutes --top 10
```

### 2. session の再調査（JSONL 部分抽出）

session レポートで足りず、過去セッションの特定箇所を掘り下げたいとき、`scripts/recording/session-extract.py` を使う。**JSONL 全体を読まずに必要な情報だけを切り出せる**ため、コンテキスト溢れを回避しながら深掘りできる。

session レポートのフロントマター `source_jsonl` をそのまま引数に渡す:

```bash
JSONL="<session レポートの source_jsonl 値>"
SE="${CLAUDE_PLUGIN_ROOT}/scripts/recording/session-extract.py"

# セッションメタ情報（まずこれで全体像を把握）
$SE "$JSONL" meta

# 読み込んだファイル一覧 / 編集したファイル一覧
$SE "$JSONL" list-reads
$SE "$JSONL" list-edits

# Bash 実行一覧
$SE "$JSONL" list-bash

# ユーザー指示・AskUserQuestion・git commit の時系列
$SE "$JSONL" list-decisions

# キーワード周辺を圧縮 Markdown で抽出（AI に渡しやすい形）
$SE "$JSONL" grep "REQ-002" --context 3 --compress

# 特定ツールの全呼び出しを本文付きで抽出
$SE "$JSONL" tool Edit --with-result --compress

# 時刻範囲で抽出
$SE "$JSONL" range --from 10:00 --to 10:30 --compress

# 指定メッセージ UUID 周辺
$SE "$JSONL" around <message_uuid> --window 10 --compress
```

`--compress` を付けると `jsonl-to-markdown.py` 同等の圧縮（tool_result/tool_use 削減）を適用する。AI に渡す場合は `--compress` 推奨、人間が詳細確認する場合は無しが良い。

### 3. session の手動再生成

特定セッションを再要約したい場合:

```bash
# JSONL パスを特定して hook.py に流す
printf '%s' '{"session_id":"<UUID>","cwd":"<CWD>","transcript_path":"<JSONL>"}' \
    | "${CLAUDE_PLUGIN_ROOT}/scripts/recording/hook.py"
```

既存レポートは上書きされる。再生成時は Codex 側で旧版のフロントマター `status` を `superseded` に更新し、新レポートの `supersedes` に旧版へのパス（または旧 `updated_at`）を記録する。

### 4. web（URL アーカイブ）の記録

**Step 1（対話確認）**: 引数なしで起動された場合、ユーザーに以下を順に確認する:

1. 取得したい URL（必須、http/https）
2. タイトル（任意。省略時は Jina Reader が返す `Title:` 行を採用）
3. タグ（任意、カンマ区切り）

**Step 2（実行）**: 確認した内容で `fetch-jina.sh` を呼ぶ:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/recording/web/fetch-jina.sh" \
    "<URL>" --title "<タイトル>" --tags "tag1,tag2"
```

スクリプトは `https://r.jina.ai/<URL>` から Markdown を取得し、`<memories_dir>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md` に frontmatter 付きで保存する。`JINA_API_KEY` が `~/.config/jina/secrets.env` または環境変数にあれば Bearer 付与。

成功時、保存パスを stdout に返す。cocoindex は変更検知で自動再インデックスするため、追加操作は不要。

> 既知の制限（MVP）: 同一 URL の再取得時に旧版を `superseded` に降格する機構は未実装。毎回新規ファイルとして記録される。フィルタが必要になれば `frontmatter source_url` で重複検出する後処理を追加する。

### 5. minutes（議事録）の記録

**Step 1（対話確認）**: 引数なしで起動された場合、ユーザーに以下を順に確認する:

1. タイトル（必須）
2. 本文（必須。箇条書き／会話ログ／決定事項などをそのまま渡す）
3. 関連 session_id（任意。直近セッションで議論した内容を残す場合）
4. 参加者（任意）
5. タグ（任意、カンマ区切り）

**Step 2（実行）**: 確認した内容で `save.sh` を呼ぶ:

```bash
# stdin で本文を渡す（ヒアドキュメント）
"${CLAUDE_PLUGIN_ROOT}/scripts/recording/minutes/save.sh" \
    --title "<タイトル>" \
    --tags "tag1,tag2" \
    --participants "miya,claude" \
    --related-session "<UUID>" <<'EOF'
- 議題: ...
- 決定: ...
- アクション: ...
EOF

# またはファイルから
"${CLAUDE_PLUGIN_ROOT}/scripts/recording/minutes/save.sh" \
    --title "<タイトル>" --from-file /tmp/minutes.md
```

スクリプトは `<memories_dir>/raw/minutes/YYYY-MM-DD/HHMMSS_<slug>.md` に frontmatter 付きで保存する。要約・整形は行わず、渡された本文をそのまま保存する（議事録の生情報を保持する設計）。

成功時、保存パスを stdout に返す。

## 自動化パイプライン（kind: session のみ）

`memory` プラグインの `SessionEnd` hook が `${CLAUDE_PLUGIN_ROOT}/hooks/session-end.sh` を起動し、最終的に `scripts/recording/hook.py` → `runner.sh` → Codex 要約 → `<memories_dir>/raw/sessions/...` に書き出す。詳細は `references/architecture.md`。

## 初期設定

インストール直後の前提確認・config.toml 作成・マウントポイント準備・cocoindex 連携起動・初回 session 生成テストの手順は `memory-setup` skill にまとめてある。最初は `memory-setup` を参照すること。

## 関連スキル

- `memory-setup` — プラグイン初期設定の手順
- `memory-search` — Raw（session/web/minutes）+ Wiki に対するベクトル検索（Claude API からも利用可）
- `memory-wiki` — Raw を統合した Wiki 生成（ingest-queue 経由で自動連携。kind: session のみ codex 統合、web/minutes は index 列挙）
- `adr` — 意思決定記録（不可逆な判断の永続化レイヤー）
- `retrospective` — フェーズ完了振り返り（エピソードから skills/rules への昇華）
