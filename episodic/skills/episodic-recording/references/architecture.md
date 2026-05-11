# episodic-recording 仕組み・配置

SKILL.md からは外出ししたアーキテクチャ詳細。挙動を変更・調査するときに参照する。

`episodic-recording` skill は kind 別に保存経路が異なる。本ドキュメントは **kind: session の自動生成パイプライン** を主に解説する（web / minutes は手動経路で `fetch-jina.sh` / `save.sh` を直接呼ぶシンプル構造）。

## 自動生成の仕組み（kind: session）

`episodic` プラグイン（`hooks/hooks.json`）の `Stop` フックが `${CLAUDE_PLUGIN_ROOT}/scripts/session-stop.sh` を起動する。`session-stop.sh` は同梱の `scripts/session/hook.py` を exec する薄いブートストラップで、stdin の JSON ペイロードをそのまま Python hook へパススルーする。`UserPromptSubmit` フックは `${CLAUDE_PLUGIN_ROOT}/scripts/session-user-prompt-submit.sh` 経由で同じ `hook.py` を起動し、ユーザーが続きの入力を送った時点で pending debounce をキャンセルする。

Stop hook は **Claude Code の応答ごと** に発火するため、本フックは debounce タイマーを噛ませて「最後の Stop から `stop_debounce_seconds`（既定 30 秒）静寂が続いたら 1 度だけ Codex を起動する」設計をとる。debounce 満了前に `UserPromptSubmit` が発火した場合は `.debounce.pid` のプロセスグループを SIGTERM で停止して pid ファイルを削除するため、会話継続中の古い Stop からは Codex 要約が起動しない。Claude Code を強制終了したり wrapper 経由で終了させた場合でも、最後に走った Stop の transcript をもとに Codex 要約が走る。

1. stdin の JSON (`session_id` / `cwd` / `transcript_path` / `stop_hook_active` 等) を取得
2. `stop_hook_active=true` の場合は無限ループ防止のため early return（Anthropic 公式パターン）
3. 対応する Claude Code JSONL 履歴を特定
4. ユーザープロンプトが1件も存在しないセッションはスキップ
5. `scripts/session/jsonl-to-markdown.py` で会話履歴を Markdown 化して `/tmp/<session_id>/<ts>.md` に保存
6. Codex 向けの命令プロンプト＋セッションメタデータ（`generated_at` 含む）を先頭に埋め込み、`/tmp/<session_id>/<ts>.codex.md` として同梱ファイルを生成
7. **保存先解決**: `scripts/lib/config.py` がマウント検証（`MEMORIES_DIR/.mount-canary` の実在）を行い、未確立なら `auto_remount=true` で1回だけ remount を試行。最終的に `scripts/lib/path_resolver.py` が `(report_path, is_staged)` を返す
   - マウント成立: `<MEMORIES_DIR>/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md`
   - 未成立     : `<fallback_dir>/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md`
8. `/tmp/<session_id>/<ts>.codex.meta.json` に runner 引数（`report_path` / `is_staged` / `session_id` / `cwd` / `transcript_path` / `first_ts`）を sidecar として書き出す（実行はまだしない）
9. **debounce タイマーを (再)起動**: `nohup sleep N && python3 hook.py --finalize <session_id>` を背景プロセスで起動し、pid を `/tmp/<session_id>/.debounce.pid` に保存。Stop が来るたびに既存 sleep を SIGTERM で kill して reset する（最後の Stop だけが finalize に到達する）
10. **ユーザー入力によるキャンセル**: debounce 満了前に `UserPromptSubmit` が来た場合、`hook.py` が `/tmp/<session_id>/.debounce.pid` のプロセスグループを停止して pid ファイルを削除する
11. debounce 満了で `--finalize` モードが起動し、`/tmp/<session_id>/` 内の最新 `*.codex.meta.json` を選んで処理中ロック（`/tmp/<session_id>/.lock/`）を取得する。Terminal.app は使わず、`subprocess.Popen` で `runner.sh` を直接バックグラウンド起動する（`stdin=DEVNULL`、`stdout/stderr=/tmp/episodic/session-runner.log`、`start_new_session=True`、`close_fds=True` で hook プロセスから完全分離）
12. runner.sh は meta sidecar から `report_path` / `is_staged` を読み出し、対応する `<ts>.codex.md` を入力として `codex exec` を実行する
13. runner.sh は起動直後に `/tmp/<session_id>/` の最新 timestamp を再選択する（Popen 起動から走り出すまでの遅延中に新 Stop が来た場合の救済）。内部の `codex exec` は `--disable hooks` と `EPISODIC_RECORDING_ACTIVE=1` で Stop hook 再入を抑止する。`codex` の戻り値は `${PIPESTATUS[0]}` で取得する（pipefail 下で `tee` の失敗が混ざらない）
14. Codex (`gpt-5.4-mini`) が同梱 Markdown を解析し、`kind: session` フロントマター付きレポートを上記 `report_path` に直接書き出す
15. runner.sh の `trap EXIT` で `/tmp/<session_id>/` をディレクトリごと削除する。ただし処理に使った `<ts>` より新しい `*.codex.md` が見つかった場合は `--finalize` を再 spawn し、SESSION_DIR は新 finalize の trap EXIT に掃除を委譲する
16. 後処理:
    - **normal**（マウント成立）: `scripts/wiki/enqueue.py` で wiki キューへ追加（kind 自動推定） → `scripts/wiki/kick-runner.sh` を fire-and-forget 起動（debounce 経由で `wiki-runner.sh` を駆動）。wiki-runner が処理完了時に **`scripts/lib/cocoindex_trigger.sh` 経由で cocoindex update を 1 回だけキック**する統一経路（runner.sh からの直接トリガーは廃止）
    - **staged**（fallback_dir 保存）: 後処理を抑止。次回 SessionStart hook で `scripts/sync-pending.sh` が走り、canary 検出後に staging→`raw/session/` 配下へ移送し、enqueue → kick-runner（→ wiki-runner → cocoindex）も後追いで起動
17. 完了時に macOS 通知で結果を知らせる（`display notification` のみ。`display alert` / dialog は使わずバックグラウンド実行でブロッキングしない。`osascript` 不在時はログ追記のみ。ログ集約先は `/tmp/episodic/`）

### Stop 中の処理競合

- 処理中（runner.sh 実行中）に新たな Stop が来ると、debounce reset → `--finalize` 起動までは成功するが `/tmp/<session_id>/.lock/` 取得失敗で skip される
- 取り残し検出は runner.sh の `trap EXIT` が担う。処理に使った `<ts>` より新しい `*.codex.md` が SESSION_DIR に残っていれば `nohup hook.py --finalize` を再起動し、現 runner.sh が `.lock` を解放した直後に新 finalize がロックを取得して Codex を再実行する

## 手動保存の仕組み（kind: web / kind: minutes）

両者ともマウント前提（staging なし）。保存後に **`scripts/wiki/enqueue.py --kind <kind>` で wiki キューへ追加 → `scripts/wiki/kick-runner.sh` を fire-and-forget 起動**（debounce 経由で `wiki-runner.sh` を駆動）する。Codex が kind 別に統合先（`wiki/references.md` / `wiki/minutes/<YYYYMM>.md`）を更新し、wiki-runner 完了時に cocoindex update が 1 回キックされる（統一経路）。

- **web**: `scripts/recording/web/fetch-jina.sh <URL> [--title T] [--tags ...]` が `r.jina.ai/<URL>` から Markdown を取得し、`<MEMORIES_DIR>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md` に書き出す。`JINA_API_KEY`（環境変数または `~/.config/jina/secrets.env`）があれば Bearer 付与。保存直後に enqueue + kick-runner 起動
- **minutes**: `scripts/recording/minutes/save.sh --title T [--from-file PATH | stdin]` が本文を frontmatter 付きで `<MEMORIES_DIR>/raw/minutes/YYYY-MM-DD/HHMMSS_<slug>.md` に書き出す。要約・整形は行わない。保存直後に enqueue + kick-runner 起動

### ファイル名衝突防止

`HHMMSS_<host8>_<sid8>` 命名規則により、同一マシン同セッション同秒の重複や、複数マシンが同じ `MEMORIES_DIR` を共有した場合の衝突を実質ゼロにしている:

- `host8`: hostname の SHA-1 hex 先頭 8 文字（`config.toml` の `hostname_hash_length` で調整可）
- `sid8`: Claude Code session_id 先頭 8 文字
- staging 側のみ末尾に `__staged` サフィックスを付け、`sync-pending.sh` が移送時に外して正規名に戻す

## project 名の決定ロジック（kind: session）

session レポートの frontmatter `project` フィールドは、`wiki-runner.sh` が `wiki/projects/<project>.md` への振り分けに使う。決定ロジックは以下の通り:

### `project` フィールド生成（`scripts/session/hook.py`）

`hook.py:project_name(cwd)` が実装:

1. Claude Code から渡された `cwd` の basename を取り出す
2. 先頭の `.`（ドット）を `lstrip('.')` で除去（隠しディレクトリ化を防ぐため）
3. 結果が空文字なら `'unknown'` にフォールバック

例:

| `cwd` | `project` |
|---|---|
| `/Users/miya/workspace/mysis/claude-plugins` | `claude-plugins` |
| `/Users/miya/.config` | `config`（先頭ドット除去） |
| `/` | `unknown`（basename が空） |

この時点では英数字以外も含まれうる（日本語ディレクトリ名、`.`、空白等）。

### `project` フィールドの再 sanitize（`scripts/wiki/wiki-runner.sh`）

`wiki-runner.sh` は session レポートの frontmatter から `project` を読み取る際にもう一度サニタイズする（SMB 上の Raw は untrusted のためパストラバーサル対策）:

1. `tr -cd 'a-zA-Z0-9_-'` で英数字・アンダースコア・ハイフン以外を除去
2. `head -c 64` で 64 文字に切り詰め
3. 結果が空文字なら `'unknown'` にフォールバック
4. 元の値とサニタイズ後で差異があれば log に warning を残す

最終的に `wiki/projects/<sanitized-project>.md` に統合される。

### 手動 override する方法

session レポートは Codex が再生成する前提のため、生成済みファイルの frontmatter を手動編集して `project` を別名に変えるだけでは反映されない（Codex に再投入する経路が必要）。意図的に固定名にしたい場合の選択肢:

- **ディレクトリ名で制御**: 作業前に `cwd` を意図する project 名のディレクトリに揃える（最も簡単）
- **再生成時に手動上書き**: 過去 session を再要約する際、`hook.py` を手動起動する前に対象セッション JSONL の `cwd` を一時的に書き換える
- **wiki/projects/ の手動マージ**: 既存 `wiki/projects/<old>.md` を `wiki/projects/<new>.md` にリネームし、以降の Raw を新名で生成させる（旧名の Raw が再投入されると別ファイルが生成されるので注意）

### `wiki/projects/<project>.md` の命名規則

- ファイル名: `<sanitize 済み project>.md`（英数字 / `_` / `-` のみ、64 文字以内）
- `wiki-runner.sh` の AppleDouble (`._*`) と隠しファイル除外フィルタにより、`._unknown.md` のようなゴミファイルが index に混入しない
- index.md（自動再生成）は `wiki/projects/*.md` を sorted で列挙する

## ファイル配置

### スクリプト（プラグイン同梱）

実行スクリプトは `${CLAUDE_PLUGIN_ROOT}/scripts/` 配下にまとまっており、skill ごとに参照する。

- `${CLAUDE_PLUGIN_ROOT}/skills/episodic-recording/SKILL.md` — エントリ（使い方中心）
- `${CLAUDE_PLUGIN_ROOT}/skills/episodic-recording/references/architecture.md` — 本ファイル（仕組み・配置・出力構造）
- `${CLAUDE_PLUGIN_ROOT}/scripts/session/hook.py` — Stop hook 実体（Python、debounce / `--finalize` モード搭載）
- `${CLAUDE_PLUGIN_ROOT}/scripts/session/jsonl-to-markdown.py` — JSONL→Markdown変換
- `${CLAUDE_PLUGIN_ROOT}/scripts/session/runner.sh` — Codex 実行ランナー
- `${CLAUDE_PLUGIN_ROOT}/scripts/session/retry-pending.sh` — Codex 失敗リトライ消化（SessionStart hook で起動）
- `${CLAUDE_PLUGIN_ROOT}/scripts/session/retry_queue.py` — リトライキュー操作 CLI
- `${CLAUDE_PLUGIN_ROOT}/scripts/sync-pending.sh` — staging→正規パス移送（SessionStart hook で起動）
- `${CLAUDE_PLUGIN_ROOT}/scripts/session/session-extract.py` — JSONL部分抽出CLI（再調査用）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/main_episodic.py` — episodic 専用 cocoindex エントリポイント（episodic プラグイン自身の venv（`episodic/scripts/.venv`）で実行）
- `${CLAUDE_PLUGIN_ROOT}/scripts/mount-memory-share.sh` — SMB 再マウントヘルパー（macOS 専用）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/web/fetch-jina.sh` — Jina Reader 経由で URL を Markdown 化して保存（kind: web）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/minutes/save.sh` — 議事録を frontmatter 付きで保存（kind: minutes）
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/config.py` — 設定ローダー＋マウント判定
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/path_resolver.py` — 保存先パス解決
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/plugin_root.py` — プラグインルート解決ヘルパー
- `${CLAUDE_PLUGIN_ROOT}/scripts/setup_db.sh` — episodic 専用 PostgreSQL database の冪等セットアップ
- `${CLAUDE_PLUGIN_ROOT}/scripts/templates/cocoindex.toml.example` — `~/.config/episodic/cocoindex.toml` のひな形
- `${CLAUDE_PLUGIN_ROOT}/scripts/templates/episodic.env.example` — `~/.config/episodic/.env` のひな形（`EPISODIC_DATABASE_URL`）
- `${CLAUDE_PLUGIN_ROOT}/scripts/templates/episodic_secrets.env.example` — `~/.config/episodic/secrets.env` のひな形（`VOYAGE_API_KEY`）
- `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml` — `~/.config/episodic/config.toml` のひな形

### 生成物

- **session（正規・永続）**: `<memories_dir>/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md`
- **session（staging・永続）**: `<fallback_dir>/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md` — マウント未確立時のみ。次回 mount 成功時に sync-pending.sh が `raw/session/` 配下へ移送
- **web（永続）**: `<memories_dir>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md`
- **minutes（永続）**: `<memories_dir>/raw/minutes/YYYY-MM-DD/HHMMSS_<slug>.md`
- **一時Markdown（揮発）**: `/tmp/<session_id>/<ts>.md` / `/tmp/<session_id>/<ts>.codex.md` / `/tmp/<session_id>/<ts>.codex.meta.json`（runner.sh の trap EXIT がディレクトリごと削除する）
- **hookログ**: `/tmp/episodic/session-hook.log`
- **runnerログ**: `/tmp/episodic/session-runner.log`
- **syncログ**: `/tmp/episodic/session-sync.log`
- **retryログ**: `/tmp/episodic/session-retry.log`
- **wiki-runnerログ**: `/tmp/episodic/wiki-runner.log`
- **cocoindex updateログ**: `/tmp/episodic/cocoindex-update.log`
- **SMB マウントログ**: `/tmp/episodic/smb-mount.log`

## 設定（config.toml）

設定ファイルを `~/.config/episodic/config.toml` に置くと `memories_dir` / `fallback_dir` / `auto_remount` などを変更できる。テンプレは `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml`。環境変数（`MEMORIES_DIR` 等）が設定されている場合はそちらが優先される。

`remount_script` の既定値は実行配置に応じて動的解決される（repo 内では `${CLAUDE_PLUGIN_ROOT}/scripts/mount-memory-share.sh`、Codex hook runtime では `~/.config/episodic/codex-hook-runtime/bin/mount-memory-share.sh`）。Linux など macOS 以外で SMB を扱いたい場合は、自前のマウントスクリプトに差し替えること。

マウント検証は `<memories_dir>/.mount-canary` ファイルの実在で行う。共有側（SMB サーバ等）に1度だけ `touch /Volumes/memory/.mount-canary` しておけば以後は変更不要。canary が見えない場合はマウント未確立と判断し、`fallback_dir` へ staging として書き込む。

## レポートの構造

各レポートはフロントマター＋本文構成。すべての kind に共通して `kind`（`session` / `web` / `minutes`）と `status` を持つ。テンプレートは `${CLAUDE_PLUGIN_ROOT}/templates/{session,web,minutes}.md` 参照。

### kind: session のフロントマター

基本フィールド:

- `kind: session`
- `session_id` / `title` / `project` / `cwd` / `git_branch`
- `started_at` / `ended_at` / `duration_minutes`（ISO 8601）
- `message_count` / `model`
- `tags`（英小文字スラグ、最大5個）
- `keywords`(日本語自然語、最大10個)
- `source_jsonl`

エピソード記憶層としての拡張フィールド:

- `status`: レポートの状態。`active` / `deprecated` / `superseded` / `unknown`
  - 新規生成は `active`
  - 再生成で旧版が置き換わる場合、旧版を `superseded` に書き換える
  - 内容が誤っていたと判明した場合、手動で `deprecated` に変更
- `updated_at`: 最終更新時刻（ISO 8601）。`generated_at` と同値
- `confidence`: 要約の信頼度（0.0〜1.0）。Codex が会話履歴の明確性に基づいて自己評価
- `supersedes`: 通常 `null`。再生成時のみ旧版の絶対パスを文字列で記す

### kind: web のフロントマター

- `kind: web` / `title` / `source_url`
- `fetched_at` / `fetched_via: jina-reader` / `http_status`
- `created_at` / `updated_at` / `status` / `supersedes` / `tags`

### kind: minutes のフロントマター

- `kind: minutes` / `title`
- `created_at` / `updated_at` / `status` / `supersedes`
- `related_session`（任意・session_id）
- `participants`（任意・配列）/ `tags`

### 本文セクション

- 概要（2〜3文）
- やったこと（時系列箇条書き）
- 判断・決定事項（理由と根拠付き）
- 残課題・次アクション（単純リスト）
- 変更・参照した主なファイル
- 備考

### 記録に含めない内容

`scripts/session/hook.py` の CODEX_INSTRUCTION_TEMPLATE「除外対象」セクションが正規定義。要点:

- シークレット・APIキー・トークン・パスワード（マスクではなく丸ごと省く）
- 不要な個人情報（メール・電話・氏名等）
- 一時的な推測（検証されていない仮説）
- 重複情報・冗長な引用
- ユーザーの感情的表現・暴言・罵倒・苛立ち

## トラブルシューティング

- レポートが生成されない → `/tmp/episodic/session-runner.log` で codex の失敗原因を確認
- hookが呼ばれていない → `/tmp/episodic/session-hook.log` を確認、プラグインの `hooks/hooks.json` が有効化されているか確認（`/plugin enable episodic@hidetsugu-miya`）
- SKIP判定された → 会話にユーザープロンプトがない、または作業実体がないと判定されている
- debounce で Codex がいつまでも走らない → `stop_debounce_seconds` を短くするか、環境変数 `MEMORIES_STOP_DEBOUNCE_SECONDS=2` で短縮して挙動確認
- 取り残し再 finalize の確認 → `/tmp/episodic/session-runner.log` の `respawn finalize for newer timestamp:` を grep
- モデル変更 → 環境変数 `CODEX_RECORDING_MODEL` で上書き可能（既定: `gpt-5.4-mini`）
- macOS 以外で動かしている → 通知・Terminal 起動・SMB マウントは自動スキップされる。Raw 生成本体は動作するが、結果のフィードバック手段はログのみ
- ログ集約先は `/tmp/episodic/` 配下（揮発、OS再起動で消える）

## cocoindex 連携と埋め込みモデル

`scripts/lib/cocoindex_trigger.sh` の `trigger_cocoindex_update()` が Raw 生成成功時に episodic 専用エントリポイント `scripts/recording/main_episodic.py` を経由して cocoindex を更新する（best effort・非同期）。

episodic プラグインは **専用 venv（`episodic/scripts/.venv`）と専用 database（`episodic`）** を持ち、cocoindex プラグインから完全に独立している。`uv` がインストールされていない環境では cocoindex 更新は自動的にスキップされる。

- **インデックス名**: テーブル名は `episodicindex_<host>_episodic__chunks` 形式（`<host>` は `socket.gethostname()` を `[^a-zA-Z0-9]` を `_` に置換した小文字）。`INDEX_NAME` は固定値 `episodic`、`scripts/search/search.py` の `get_table_name()` も同一規約で算出する
- **App 名**: `EpisodicIndex_<host>_episodic`
- **データベース**: `EPISODIC_DATABASE_URL`（既定 `postgres://postgres:postgres@localhost:15432/episodic`）。cocoindex プラグインの `cocoindex` database とは別空間
- **対象**: `MEMORIES_DIR` 配下の `**/*.md`（Raw（session/web/minutes）+ Wiki 全方）
- **除外**: `trashbox/**`（古い下書き等のノイズ源）、`**/_*.md`（アンダースコア始まりの下書き慣習）、`.git/**`
- **埋め込みモデル**: `voyage-3-large`（環境変数 `MEMORIES_EMBEDDING_MODEL` で上書き可）
- **モデル変更時**: 次元・ベクトル空間が変わるため、`episodic` database 内のテーブル + メタデータを drop してから全件 re-embed が必要

### ハイブリッド検索のためのスキーマ拡張

`main_episodic.py` の `_app_main` は HNSW 以外に以下を `declare_sql_command_attachment` で追加する:

- `chunk_tsv` 列: `to_tsvector('simple', chunk_text)` の `GENERATED ALWAYS AS ... STORED` 列
- GIN index `<table>__chunk_tsv_gin`: BM25 ランキング用

`search.py` は dense（halfvec cosine）と BM25（`ts_rank`）を RRF で融合し、voyage rerank-2 で top-k を再ランキングする。

### frontmatter prepend / strip（精度向上）

`main_episodic.py` のフローは frontmatter（`title` / `tags` / `keywords`）を embedding 入力に prepend する。検索結果のスニペット表示が綺麗になるよう、DB 格納用 `chunk_text` には素の本文だけを格納する（embed/store 分離）:

- **本文先頭の `---` ブロックを抽出**: `_extract_fm_prefix` が `title:` / `tags:` / `keywords:` の各行だけを 1 行に整形して返す。frontmatter が無いファイルは空文字
- **本文から frontmatter を除去**: `_strip_frontmatter` が先頭 `---` 〜 `\n---` を取り除いた本文を返す。これを RecursiveSplitter に渡す（最初のチャンクが「2 重 frontmatter」になる問題を回避）
- **chunk 単位で prepend**: `_process_chunk` が `{prefix}\n\n{text}` を生成して embedder に渡す。prefix が空文字なら素通し
- **chunk_size = 1200 / overlap = 300**: prepend する prefix（約 100 字）を補償しつつ、要約レポート系で MRR が最良だった値

これにより `tags: [lefthook, ...]` のようにタグ語彙でしか触れていないトピックでも Hit@1 がヒットしやすくなる。

### plugin update 耐性

episodic プラグインの `scripts/` は `uv` の独立 venv（`scripts/.venv`）と独立 database（`episodic`）を持つため、cocoindex プラグインのバージョン変更や再インストールに対して頑健。

```bash
# episodic テーブルを drop して再構築する手順（cocoindex_setup_metadata は episodic DB 内にあるため一括 drop で消える）
HOSTPREFIX="episodicindex_$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr A-Z a-z)_episodic"
docker exec cocoindex psql -U postgres -d episodic -c "
  DROP TABLE IF EXISTS ${HOSTPREFIX}__chunks CASCADE;
  DELETE FROM cocoindex_setup_metadata WHERE flow_name ILIKE '%episodic%';
"

# 全件再構築（episodic プラグイン専用 venv で実行）
cd "${CLAUDE_PLUGIN_ROOT}/scripts" \
  && SOURCE_PATH=/Volumes/memory \
     INDEX_NAME=episodic \
     PATTERNS="**/*.md" \
     uv run cocoindex update -f recording/main_episodic.py:EpisodicIndex_$(hostname | tr -c '[:alnum:]' '_' | tr A-Z a-z)_episodic
```
