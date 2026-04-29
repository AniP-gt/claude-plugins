# recording 仕組み・配置

SKILL.md からは外出ししたアーキテクチャ詳細。挙動を変更・調査するときに参照する。

`recording` skill は kind 別に保存経路が異なる。本ドキュメントは **kind: session の自動生成パイプライン** を主に解説する（web / minutes は手動経路で `fetch-jina.sh` / `save.sh` を直接呼ぶシンプル構造）。

## 自動生成の仕組み（kind: session）

`memory` プラグイン（`hooks/hooks.json`）の `SessionEnd` フックが `${CLAUDE_PLUGIN_ROOT}/hooks/session-end.sh` を起動する。`session-end.sh` は同梱の `scripts/recording/hook.py` を `exec` するだけの薄いブートストラップで、以下が走る:

1. stdin の JSON (`session_id` / `cwd` / `transcript_path`) を取得
2. 対応するJSONL履歴を特定
3. ユーザープロンプトが1件も存在しないセッションはスキップ
4. `scripts/recording/jsonl-to-markdown.py` で会話履歴をMarkdown化して `/tmp/<session_id>.md` に保存
5. Codex向けの命令プロンプト＋セッションメタデータ（`generated_at` 含む）を先頭に埋め込み、`/tmp/<session_id>.codex.md` として同梱ファイル生成
6. **保存先解決**: `scripts/lib/config.py` がマウント検証（`MEMORIES_DIR/.mount-canary` の実在）を行い、未確立なら `auto_remount=true` で1回だけ remount を試行。最終的に `scripts/lib/path_resolver.py` が `(report_path, is_staged)` を返す
   - マウント成立: `<MEMORIES_DIR>/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md`
   - 未成立     : `<fallback_dir>/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md`
7. `/tmp/<session_id>.runner.command` ランチャーを生成し、macOS では `open -g -a Terminal` で Terminal.app に渡す。`osascript` / `open` が見つからない環境では Terminal を開かず、launcher を直接バックグラウンドで起動する
   - mac 経路のランチャーは `scripts/recording/runner.sh <combined_md> <report_path> <staged|normal>` を実行後、`osascript` で自ウィンドウを `tty` 特定して自動クローズ
8. Codex (`gpt-5.4-mini`) が同梱Markdownを解析し、`kind: session` フロントマター付きレポートを上記 `report_path` に直接書き出す
9. 後処理:
   - **normal**（マウント成立）: `scripts/wiki/enqueue.py` で wiki キューへ追加（kind 自動推定） → `scripts/wiki/wiki-runner.sh` 起動 → cocoindex update キック
   - **staged**（fallback_dir 保存）: 後処理を抑止。次回 SessionStart hook で `scripts/recording/sync-pending.sh` が走り、canary 検出後に staging→`raw/session/` 配下へ移送し、wiki/cocoindex も後追いで起動
10. 完了時に macOS 通知で結果を知らせる（`osascript` 不在時はログ追記のみ。ログ集約先は `/tmp/memories/`）

## 手動保存の仕組み（kind: web / kind: minutes）

両者ともマウント前提（staging なし）。保存後に cocoindex 自動再インデックスへ任せる。

- **web**: `scripts/recording/web/fetch-jina.sh <URL> [--title T] [--tags ...]` が `r.jina.ai/<URL>` から Markdown を取得し、`<MEMORIES_DIR>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md` に書き出す。`JINA_API_KEY`（環境変数または `~/.config/jina/secrets.env`）があれば Bearer 付与
- **minutes**: `scripts/recording/minutes/save.sh --title T [--from-file PATH | stdin]` が本文を frontmatter 付きで `<MEMORIES_DIR>/raw/minutes/YYYY-MM-DD/HHMMSS_<slug>.md` に書き出す。要約・整形は行わない

### ファイル名衝突防止

`HHMMSS_<host8>_<sid8>` 命名規則により、同一マシン同セッション同秒の重複や、複数マシンが同じ `MEMORIES_DIR` を共有した場合の衝突を実質ゼロにしている:

- `host8`: hostname の SHA-1 hex 先頭 8 文字（`config.toml` の `hostname_hash_length` で調整可）
- `sid8`: Claude Code session_id 先頭 8 文字
- staging 側のみ末尾に `__staged` サフィックスを付け、`sync-pending.sh` が移送時に外して正規名に戻す

## ファイル配置

### スクリプト（プラグイン同梱）

実行スクリプトは `${CLAUDE_PLUGIN_ROOT}/scripts/` 配下にまとまっており、skill ごとに参照する。

- `${CLAUDE_PLUGIN_ROOT}/skills/recording/SKILL.md` — エントリ（使い方中心）
- `${CLAUDE_PLUGIN_ROOT}/skills/recording/references/architecture.md` — 本ファイル（仕組み・配置・出力構造）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/hook.py` — SessionEnd hook 実体（Python）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/jsonl-to-markdown.py` — JSONL→Markdown変換
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/runner.sh` — Codex 実行ランナー
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/sync-pending.sh` — staging→正規パス移送（SessionStart hook で起動）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/session-extract.py` — JSONL部分抽出CLI（再調査用）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/main_memory.py` — cocoindex 用エントリポイント（プラグインキャッシュの venv を借りて実行）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/mount-memory-share.sh` — SMB 再マウントヘルパー（macOS 専用）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/web/fetch-jina.sh` — Jina Reader 経由で URL を Markdown 化して保存（kind: web）
- `${CLAUDE_PLUGIN_ROOT}/scripts/recording/minutes/save.sh` — 議事録を frontmatter 付きで保存（kind: minutes）
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/config.py` — 設定ローダー＋マウント判定
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/path_resolver.py` — 保存先パス解決
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/plugin_root.py` — プラグインルート解決ヘルパー
- `${CLAUDE_PLUGIN_ROOT}/scripts/lib/cocoindex_path.py` — cocoindex プラグインキャッシュの動的解決
- `${CLAUDE_PLUGIN_ROOT}/scripts/templates/cocoindex.toml.example` — `~/.config/memory/cocoindex.toml` のひな形
- `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml` — `~/.config/recording/config.toml` のひな形

### 生成物

- **session（正規・永続）**: `<memories_dir>/raw/session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md`
- **session（staging・永続）**: `<fallback_dir>/YYYY-MM-DD/HHMMSS_<host8>_<sid8>__staged.md` — マウント未確立時のみ。次回 mount 成功時に sync-pending.sh が `raw/session/` 配下へ移送
- **web（永続）**: `<memories_dir>/raw/web/YYYY-MM-DD/HHMMSS_<slug>.md`
- **minutes（永続）**: `<memories_dir>/raw/minutes/YYYY-MM-DD/HHMMSS_<slug>.md`
- **一時Markdown（揮発）**: `/tmp/<session_id>.md` / `/tmp/<session_id>.codex.md` / `/tmp/<session_id>.runner.command`（OS再起動で消える）
- **hookログ**: `/tmp/memories/recording-hook.log`
- **runnerログ**: `/tmp/memories/recording-runner.log`
- **syncログ**: `/tmp/memories/recording-sync.log`
- **SMB マウントログ**: `/tmp/memories/smb-mount.log`

## 設定（config.toml）

設定ファイルを `~/.config/recording/config.toml` に置くと `memories_dir` / `fallback_dir` / `auto_remount` などを変更できる。テンプレは `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml`。環境変数（`MEMORIES_DIR` 等）が設定されている場合はそちらが優先される。

`remount_script` の既定値はプラグインルート基準で動的解決される（`${CLAUDE_PLUGIN_ROOT}/scripts/recording/mount-memory-share.sh`）。Linux など macOS 以外で SMB を扱いたい場合は、自前のマウントスクリプトに差し替えること。

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

`scripts/recording/hook.py` の CODEX_INSTRUCTION_TEMPLATE「除外対象」セクションが正規定義。要点:

- シークレット・APIキー・トークン・パスワード（マスクではなく丸ごと省く）
- 不要な個人情報（メール・電話・氏名等）
- 一時的な推測（検証されていない仮説）
- 重複情報・冗長な引用
- ユーザーの感情的表現・暴言・罵倒・苛立ち

## トラブルシューティング

- レポートが生成されない → `/tmp/memories/recording-runner.log` で codex の失敗原因を確認
- hookが呼ばれていない → `/tmp/memories/recording-hook.log` を確認、プラグインの `hooks/hooks.json` が有効化されているか確認（`/plugin enable memory@hidetsugu-miya`）
- SKIP判定された → 会話にユーザープロンプトがない、または作業実体がないと判定されている
- モデル変更 → 環境変数 `CODEX_RECORDING_MODEL` で上書き可能（既定: `gpt-5.4-mini`）
- macOS 以外で動かしている → 通知・Terminal 起動・SMB マウントは自動スキップされる。Raw 生成本体は動作するが、結果のフィードバック手段はログのみ
- ログ集約先は `/tmp/memories/` 配下（揮発、OS再起動で消える）

## cocoindex 連携と埋め込みモデル

`runner.sh` の `trigger_cocoindex_update()` が Raw 生成成功時に memories 専用エントリポイント `scripts/recording/main_memory.py` を経由して cocoindex を更新する（best effort・非同期）。プラグイン本体（汎用 `main.py`）は使用しない。

cocoindex プラグインのキャッシュは `~/.claude/plugins/cache/hidetsugu-miya/cocoindex/<version>/scripts/` に展開されるが、バージョンは plugin update のたびに変わる。本プラグインは `scripts/lib/cocoindex_path.py` の `resolve_cocoindex_scripts()` で **`.venv` を持つ最新バージョンを semver 順で動的解決**する。venv が見つからない / `uv` がインストールされていない環境では cocoindex 更新は自動的にスキップされる。

- **インデックス名**: cocoindex 内部のテーブル名は `codeindex_<host>_<basename(MEMORIES_DIR)>__code_chunks` 形式（`<host>` は `socket.gethostname()` を `[^a-zA-Z0-9]` を `_` に置換した小文字。例: `MEMORIES_DIR=/Volumes/memory` の場合 `codeindex_<host>_memory__code_chunks`）。`runner.sh` は `--name "$(basename "$memories_dir")"` 相当の `INDEX_NAME` を渡し、`scripts/search/search.py` の `get_table_name()` 算出と一致させる
- **対象**: `MEMORIES_DIR` 配下の `**/*.md`（Raw（session/web/minutes）+ Wiki 全方）
- **除外**: `trashbox/**`（古い下書き等のノイズ源）、`**/_*.md`（アンダースコア始まりの下書き慣習）、`.git/**`
- **埋め込みモデル**: `voyage-3-large`（環境変数 `MEMORIES_EMBEDDING_MODEL` で上書き可）
- **棲み分けの理由**: cocoindex の他用途（コードベース検索）は `voyage-code-3` を `~/.config/cocoindex/.env` で既定としている。memories は日本語含む自然文書中心のため多言語汎用モデルが優位。共通 `.env` を変更するとコード検索側に副作用が出るため、本スキル呼び出し時のみ呼び出し側で `EMBEDDING_MODEL` を export する方式（`load_dotenv` は既存 env を上書きしない仕様）を採る
- **モデル変更時**: 次元・ベクトル空間が変わるため、PostgreSQL のテーブル + メタデータを drop してから全件 re-embed が必要

### frontmatter prepend / strip（精度向上）

`main_memory.py` のフローは frontmatter（`title` / `tags` / `keywords`）を embedding 入力に prepend する。検索結果のスニペット表示が綺麗になるよう、DB 格納用 `chunk_text` には素の本文だけを格納する（embed/store 分離）:

- **本文先頭の `---` ブロックを抽出**: `_extract_fm_prefix` が `title:` / `tags:` / `keywords:` の各行だけを 1 行に整形して返す。frontmatter が無いファイルは空文字
- **本文から frontmatter を除去**: `_strip_frontmatter` が先頭 `---` 〜 `\n---` を取り除いた本文を返す。これを RecursiveSplitter に渡す（最初のチャンクが「2 重 frontmatter」になる問題を回避）
- **chunk 単位で prepend**: `_process_chunk` が `{prefix}\n\n{text}` を生成して embedder に渡す。prefix が空文字なら素通し
- **chunk_size = 1200 / overlap = 300**: prepend する prefix（約 100 字）を補償しつつ、要約レポート系で MRR が最良だった値

これにより `tags: [lefthook, ...]` のようにタグ語彙でしか触れていないトピックでも Hit@1 がヒットしやすくなる。

### plugin update 耐性

cocoindex プラグインのキャッシュは plugin update で消失するが、本プラグイン scripts/ は memory プラグインのインストール先に独立して同梱され、`uv` の独立 venv（`scripts/.venv`）を持つため plugin update に対して頑健。

```bash
# memory 関連テーブル + cocoindex_setup_metadata の該当行を drop
HOSTPREFIX="codeindex_$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr A-Z a-z)_memory"
docker exec cocoindex psql -U postgres -d postgres -c "
  DROP TABLE IF EXISTS ${HOSTPREFIX}__code_chunks CASCADE;
  DROP TABLE IF EXISTS ${HOSTPREFIX}__cocoindex_tracking CASCADE;
  DELETE FROM cocoindex_setup_metadata WHERE flow_name ILIKE '%${HOSTPREFIX#codeindex_}%';
"

# 全件再構築（呼び出し側で env 上書き、cocoindex CLI 形式）
cd "$(python3 -c "
import sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}/scripts')
from lib.cocoindex_path import resolve_cocoindex_scripts
print(resolve_cocoindex_scripts())
")" \
  && SOURCE_PATH=/Volumes/memory \
     INDEX_NAME=memory \
     PATTERNS="**/*.md" \
     EMBEDDING_MODEL=voyage-3-large EMBEDDING_PROVIDER=voyage \
     uv run cocoindex update -f "${CLAUDE_PLUGIN_ROOT}/scripts/recording/main_memory.py:CodeIndex_<host>_memory"
```
