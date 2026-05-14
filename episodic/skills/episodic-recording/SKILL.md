---
name: episodic-recording
description: "エピソード記憶（session/web/minutes）の保存・参照 skill。session は自動、web/minutes は本 skill 経由（Notion URL 可）。「webページを記録して」「議事録を残して」「過去セッションを探して」で起動。"
argument-hint: "session regenerate <sid> | session extract <sid> <subcmd> | web | minutes | minutes from-notion <URL>"
---

# episodic-recording Skill

エピソード記憶（時間軸つきの不変・追記専用記録）の **保存・参照・再調査** を担当する skill。kind は次の 3 種類で、すべて `<memories_dir>/raw/<kind>/YYYY-MM-DD/...md` に保存される。

| kind | 保存契機 | 用途 |
|---|---|---|
| `session` | Stop hook + debounce（自動） | Claude Code セッションの要約レポート |
| `web` | 本 skill 経由（手動） | 外部 URL の Markdown アーカイブ（Jina Reader 経由） |
| `minutes` | 本 skill 経由（手動） | 議事録・指示・合意の時系列ログ |

> プラットフォーム前提: 通知（osascript）・Terminal 起動・SMB マウント関連は macOS 専用。コマンドが見つからない環境では各処理が自動的にスキップされ、保存本体はログだけ残してバックグラウンドで進む。

## 記憶レイヤーの位置付け

本 skill は **エピソード記憶（過去の出来事の記録）** を担当する。auto memory（意味記憶）・`adr`（意思決定）・`retrospective`（教訓昇華）との責務境界、運用原則（status / supersedes の扱い）は `references/memory-layers.md` を参照する。

## 保存先と命名規則

設定 `<memories_dir>` 既定 `/Volumes/memory`、`~/.config/episodic/config.toml` で変更可。

```text
<memories_dir>/raw/
├── session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md      # kind: session
├── web/YYYY-MM-DD/HHMMSS_<slug>.md                   # kind: web
└── minutes/YYYY-MM-DD/HHMMSS_<slug>.md               # kind: minutes
```

session 共有が未マウント（外出時など）の場合は自動で `~/.local/share/episodic/raw-staging/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md` に退避し、次回セッション開始時に共有が見えていれば `sync-pending.sh` が `raw/session/` 配下へ自動移送する。web / minutes は手動経路で常に共有が見えている前提のため staging を使わない。

Codex 要約生成が失敗した場合のリトライキュー消化（5 回で dead letter、debounce バイパスでの即時再実行など）は `references/architecture.md` の「Codex 失敗時の自動リトライ」を参照する。

## 使い方

### 1. 過去記録の検索

検索は **`episodic-search` skill に委譲する**（Raw + Wiki 両方を対象に、scope/status フィルタ付きでベクトル検索する）。

```bash
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/search.sh" "<自然言語クエリ>" \
    --top 10 --scope all --format markdown

# scope は session / web / minutes / wiki / all から選べる
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/search.sh" "Jina" --scope web
```

詳細は `episodic-search` skill（同プラグイン同梱）を参照。Claude API（外部アプリ）からの利用は `${CLAUDE_PLUGIN_ROOT}/skills/episodic-search/references/api-usage.md`。

時系列で直近を見る場合:

```bash
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/recent.sh" --kind session --top 5
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/recent.sh" --kind web --top 10
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/recent.sh" --kind minutes --top 10
```

### 2. session の再調査（JSONL 部分抽出）

session レポートで足りず、過去セッションの特定箇所を掘り下げたいとき、`session/session-extract.py` を使う。**JSONL 全体を読まずに必要な情報だけを切り出せる**ため、コンテキスト溢れを回避しながら深掘りできる。

session レポートのフロントマター `source_jsonl` をそのまま引数に渡す:

```bash
JSONL="<session レポートの source_jsonl 値>"
SE="${CLAUDE_PLUGIN_ROOT}/session/session-extract.py"

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
# JSONL パスを特定して hook.py に流す（"source": "retry" 付きで debounce をバイパスして即起動）
printf '%s' '{"session_id":"<UUID>","cwd":"<CWD>","transcript_path":"<JSONL>","source":"retry"}' \
    | "${CLAUDE_PLUGIN_ROOT}/session/hook.py"
```

既存レポートは上書きされる。再生成時は Codex 側で旧版のフロントマター `status` を `superseded` に更新し、新レポートの `supersedes` に旧版へのパス（または旧 `updated_at`）を記録する。

### 4. web（URL アーカイブ）の記録

**Step 1（対話確認）**: 引数なしで起動された場合、ユーザーに以下を順に確認する:

1. 取得したい URL（必須、http/https）
2. タイトル（任意。省略時は Jina Reader が返す `Title:` 行を採用）
3. タグ（任意、カンマ区切り）

**Step 2（実行）**: 確認した内容で `fetch-jina.sh` を呼ぶ:

```bash
"${CLAUDE_PLUGIN_ROOT}/recording/web/fetch-jina.sh" \
    "<URL>" --title "<タイトル>" --tags "tag1,tag2"
```

スクリプトは `https://r.jina.ai/<URL>` から Markdown を取得し、`<memories_dir>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md` に frontmatter 付きで保存する。`JINA_API_KEY` が `~/.config/jina/secrets.env` または環境変数にあれば Bearer 付与。

保存成功直後に `wiki/enqueue.py --kind web` を実行し、`wiki/kick-runner.sh` を fire-and-forget で起動する（debounce 経由で `wiki-runner.sh` が駆動される）。Codex が `wiki/references.md` をテーマ別 + 時系列で更新する（詳細は `references/wiki.md`）。cocoindex は変更検知で自動再インデックス。

成功時、保存パスを stdout に返す。

> 既知の制限（MVP）: 同一 URL の再取得時に Raw 側で旧版を `superseded` に降格する機構は未実装（Wiki 側の `references.md` では codex-instruction-web.md の「重複排除」ルールにより同 source_url の旧版エントリは置換される）。Raw のフィルタが必要になれば `frontmatter source_url` で重複検出する後処理を追加する。

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
"${CLAUDE_PLUGIN_ROOT}/recording/minutes/save.sh" \
    --title "<タイトル>" \
    --tags "tag1,tag2" \
    --participants "miya,claude" \
    --related-session "<UUID>" <<'EOF'
- 議題: ...
- 決定: ...
- アクション: ...
EOF

# またはファイルから
"${CLAUDE_PLUGIN_ROOT}/recording/minutes/save.sh" \
    --title "<タイトル>" --from-file /tmp/minutes.md
```

スクリプトは `<memories_dir>/raw/minutes/YYYY-MM-DD/HHMMSS_<slug>.md` に frontmatter 付きで保存する。要約・整形は行わず、渡された本文をそのまま保存する（議事録の生情報を保持する設計）。

保存成功直後に `wiki/enqueue.py --kind minutes` を実行し、`wiki/kick-runner.sh` を fire-and-forget で起動する（debounce 経由で `wiki-runner.sh` が駆動される）。Codex が議事録の `date` から `YYYYMM` を抽出して `wiki/minutes/<YYYYMM>.md` を月次集約フォーマットで更新する（詳細は `references/wiki.md`）。

成功時、保存パスを stdout に返す。

### 5b. Notion URL から議事録を作成

Notion 上の議事録ページ URL（`https://www.notion.so/...` 等）を入力に与えられた場合、本文を Notion MCP 経由で取得して minutes として保存する。前提として Notion MCP が `claude mcp add` で登録済みであること。OAuth 認証は Notion MCP の初回呼び出し時に Claude Code が自動処理する。

**Step 1（前提チェック）**: Notion MCP のツール（`notion-fetch` 等）が利用可能か確認する。利用不可の場合は、ユーザーに `claude mcp add --transport http --scope user notion https://mcp.notion.com/mcp` の実行を案内し、本フローを中断する。

**Step 2（本文取得）**: Notion MCP の `notion-fetch`（または同等のページ取得ツール）を直接呼び出し、ページ本文の Markdown を取得する。引数は `id=<URL>` を渡し、ページ内の関連 URL は省略せずそのまま保持する。初回呼び出し時はブラウザで OAuth 認証が走る。

**Step 3（メタ情報の確認）**: 取得した本文から候補値を抽出した上で、ユーザーに以下を確認する（既知のものは候補として提示し、空回答なら採用）:

1. タイトル（必須。Notion ページの先頭 H1 を候補にする）
2. 関連 session_id（任意）
3. 参加者（任意。本文中の参加者欄から候補抽出）
4. タグ（任意、カンマ区切り）

**Step 4（保存）**: section 5 と同じ `save.sh` を呼ぶ。本文 Markdown は stdin で渡し、frontmatter には `source_url`（Notion URL）を含めるため `--tags` に `notion,source:<URL>` 等は **入れず**、本文先頭に出典を 1 行付与する:

```bash
SRC_URL="<Notion URL>"
{
  printf '> 出典: %s\n\n' "$SRC_URL"
  printf '%s\n' "<取得した Markdown 本文>"
} | "${CLAUDE_PLUGIN_ROOT}/recording/minutes/save.sh" \
    --title "<確認したタイトル>" \
    --tags "notion,minutes" \
    --participants "<確認した参加者>" \
    --related-session "<UUID または空>"
```

> 設計メモ: `save.sh` は frontmatter に任意キーを追加する API を持たないため、出典 URL は本文冒頭の引用ブロックで残す。Wiki 統合（Codex）はこの引用を見出し近傍の典拠として扱う。

成功時、保存パスを stdout に返す。Wiki 連携は通常の minutes と同じく `enqueue.py --kind minutes` → `kick-runner.sh`（→ `wiki-runner.sh`）が走る。

## 自動化パイプライン（kind: session のみ）

`episodic` プラグインの `Stop` hook が `${CLAUDE_PLUGIN_ROOT}/bin/session-stop.sh` を起動し、`session/hook.py` が debounce タイマーを噛ませて最後の応答が落ち着いてから 1 度だけ `runner.sh` → Codex 要約 → `<memories_dir>/raw/session/...` に書き出す。`UserPromptSubmit` hook はユーザーが続きの入力を送った時点で pending debounce をキャンセルする。詳細は `references/architecture.md`。

## 初期設定

インストール直後の前提確認・config.toml 作成・マウントポイント準備・cocoindex 連携起動・初回 session 生成テストの手順は `episodic-setup` skill にまとめてある。最初は `episodic-setup` を参照すること。

## 関連スキル

- `episodic-setup` — プラグイン初期設定の手順
- `episodic-search` — Raw（session/web/minutes）+ Wiki に対するベクトル検索（Claude API からも利用可）
- `references/wiki.md`（本 skill 同梱） — Raw を統合した Wiki 生成パイプラインの運用ドキュメント。3 種すべて Codex で統合（session→projects/<p>.md、web→references.md、minutes→minutes/<YYYYMM>.md）
- `adr` — 意思決定記録（不可逆な判断の永続化レイヤー）
- `retrospective` — フェーズ完了振り返り（エピソードから skills/rules への昇華）
