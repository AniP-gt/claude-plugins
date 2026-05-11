# Wiki 統合パイプライン（運用ドキュメント）

`episodic-recording` skill が Raw を書いた直後に起動する **Wiki 統合パイプライン** の仕組み・配置・トラブルシューティング。普段は完全自動（fire-and-forget）で動くため、ユーザー・LLM が明示的に呼ぶ必要はない。本ドキュメントは **キュー再構築・ロック残留・debug** など運用事象が起きたときに参照する。

> 旧 `memory-wiki` skill の内容を移管したもの。skill としては提供せず、episodic-recording 配下のリファレンスとして保持する（v0.4.0 以降）。

## 目的

- Raw（不変・追記専用、kind: session / web / minutes）を、プロジェクト通史 + URL 参照索引 + 決定ログという **二次資産（Wiki）** に統合
- 複数 Raw 同時生成でも Wiki を破壊しない排他制御
- Raw（時系列・粒度小）と Wiki（集約・粒度大）の使い分けで検索ノイズを抑制

## kind 別の処理方針

| kind | 統合先 | Codex 呼び出し | instruction template |
|---|---|---|---|
| `session` | `wiki/projects/<project>.md`（project 単位通史） | あり | `scripts/wiki/codex-instruction.md` |
| `web` | `wiki/references.md`（テーマ別 + 時系列） | あり | `scripts/wiki/codex-instruction-web.md` |
| `minutes` | `wiki/minutes/YYYYMM.md`（月次集約、議事一覧 + 決定事項 + 残課題） | あり | `scripts/wiki/codex-instruction-minutes.md` |

3 種すべて Codex で統合する。`wiki/index.md` は機械生成で各統合先ファイルへの入口リンクと件数のみを保持する（再生成可、Codex は触らない）。

## 制約

- **Raw は immutable**: Wiki 統合中も Raw は読み取りのみ。書き換えない
- **Wiki は mutable**: Codex が再生成・上書きする。バージョン管理は Wiki ファイル自体の `updated_at` フロントマターで追う
- **排他制御必須**: `mkdir .state/lock.d` で原子的にロックを取得した1プロセスだけが queue を claim する（macOS に flock がないため mkdir 方式）。プロセス異常終了でロックが残った場合は次回起動時に PID 生存確認で自動奪取
- **target 別ロック**: runner 内部では Wiki target（`projects/<project>.md` / `references.md` / `minutes/<YYYYMM>.md`）単位で sub-lock を取り、別 target は並列処理する。同じ target への同時書き込みは sub-lock で直列化
- **batch 化**: 同一 target に複数 Raw が pending している場合、最大 `MEMORIES_WIKI_BATCH_SIZE` 件まで 1 回の Codex 呼び出しに束ねる（API 呼び出し回数削減）
- **キュー駆動**: 処理対象は `~/.local/share/episodic/state/ingest-queue.jsonl` の `status: pending` かつ `retry_after_epoch` を経過したエントリ。`status: processing` でも `MEMORIES_WIKI_PROCESSING_TIMEOUT_SECONDS`（既定 3600s）を超えたものは stuck 扱いで再処理対象に戻る
- **失敗時 retry / dead-letter**: Codex 失敗エントリは `status: pending` に戻して `attempt_count` 加算 + 指数 backoff（`MEMORIES_WIKI_RETRY_BASE_SECONDS` × 2^(n-1)、上限 86400s）の `retry_after_epoch` を付ける。`MEMORIES_WIKI_MAX_ATTEMPTS` 到達分は `ingest-deadletter.jsonl` に移送
- **debounce 起動**: enqueue 後の起動は `kick-runner.sh` 経由で `MEMORIES_WIKI_KICK_DEBOUNCE_SECONDS`（既定 5s）デバウンスし、同時複数 enqueue を 1 回の runner 起動に折り畳む。runner 実行中の追加 kick は完了待ちしてから再起動を判定する
- **state 永続化**: `~/.local/share/episodic/state/` 配下に置く（OS 再起動でも pending を保持）。旧 `/tmp/memories/state/` は wiki-runner.sh 起動時に自動マージ
- **kind 別 Codex モデル**: 統合難易度が kind ごとに異なるため、既定値を分離している:
    - `session`: `gpt-5.4`（project 通史統合は重複排除・通史化が必要で推論強度高め）
    - `web`: `gpt-5.4-mini`（要約・テーマ分類は軽量モデルで十分）
    - `minutes`: `gpt-5.4-mini`（議事録の構造保持はテンプレ寄り）
  - 環境変数で kind 別に上書き可能: `CODEX_MEMORY_WIKI_MODEL_SESSION` / `CODEX_MEMORY_WIKI_MODEL_WEB` / `CODEX_MEMORY_WIKI_MODEL_MINUTES`
  - 後方互換: `CODEX_MEMORY_WIKI_MODEL` を設定すれば全 kind の既定値を一括上書き
- **kind 別リンク相対パス**:
    - `wiki/projects/<project>.md` → session へは `../../raw/session/YYYY-MM-DD/file.md`（2 階層上る）
    - `wiki/references.md` → web へは `../raw/web/YYYY-MM-DD/file.md`（1 階層上る）
    - `wiki/minutes/<YYYYMM>.md` → minutes へは `../../raw/minutes/YYYY-MM-DD/file.md`（2 階層上る、projects/ と統一）
- **書き込み制限**: Codex は kind 別の単一統合先ファイルにのみ書き込む。CWD を統合先親ディレクトリに固定して workspace-write を限定する

## 完了条件

- `ingest-queue.jsonl` の `status: pending` かつ `retry_after_epoch` 到達済みのエントリが 0 件、もしくは Codex 連続失敗で backoff 中のエントリのみ
- 処理成功エントリは queue から削除されている（永続的な archive は保持しない）。`MEMORIES_WIKI_MAX_ATTEMPTS` 超過分は `ingest-deadletter.jsonl` に移送されている
- `wiki/index.md` が最新の章立て（Sessions Timeline / References Library / Minutes）で再生成されている
- 該当 kind の統合先（`wiki/projects/<project>.md` / `wiki/references.md` / `wiki/minutes/<YYYYMM>.md`）が Codex により更新されている

## 入力パラメータ（wiki-runner.sh）

| 引数 | 既定 | 説明 |
|---|---|---|
| `--memories-dir PATH` | `/Volumes/memory` | memories ルート |
| `--no-codex` | (false) | Codex 呼び出しをスキップ（キュー処理の動作確認用） |

環境変数:

- `MEMORIES_DIR`: memories ルート
- `CODEX_MEMORY_WIKI_MODEL_SESSION`: session 統合用 Codex モデル（既定 `gpt-5.4`）
- `CODEX_MEMORY_WIKI_MODEL_WEB`: web 統合用 Codex モデル（既定 `gpt-5.4-mini`）
- `CODEX_MEMORY_WIKI_MODEL_MINUTES`: minutes 統合用 Codex モデル（既定 `gpt-5.4-mini`）
- `CODEX_MEMORY_WIKI_MODEL`: 後方互換。設定すると全 kind の既定値を上書き
- `MEMORIES_TRASHBOX_RETAIN_DAYS`: `<MEMORIES_DIR>/trashbox/` 配下の保持日数（既定 30、0 で無効化）
- `MEMORIES_TRASHBOX_DRY_RUN`: `1` で trashbox 削除をログのみ（実削除しない）
- `MEMORIES_LOG_ROTATE_BYTES`: `/tmp/episodic/*.log` ローテーション閾値（既定 5242880）
- `MEMORIES_LOG_ROTATE_KEEP`: 同上の保持世代数（既定 3）
- `MEMORIES_WIKI_BATCH_SIZE`: 同一 target に束ねる Raw 件数の上限（既定 8）
- `MEMORIES_WIKI_PARALLELISM`: 別 target の同時処理数（既定 2）
- `MEMORIES_WIKI_MAX_ATTEMPTS`: 失敗時の最大試行回数（既定 5、超過で dead-letter）
- `MEMORIES_WIKI_RETRY_BASE_SECONDS`: 指数 backoff の初期秒数（既定 300、上限 86400）
- `MEMORIES_WIKI_PROCESSING_TIMEOUT_SECONDS`: `status: processing` を stuck と判定する経過秒数（既定 3600）
- `MEMORIES_WIKI_TARGET_LOCK_TIMEOUT_SECONDS`: target lock 取得待ちの最大秒数（既定 7200）
- `MEMORIES_WIKI_KICK_DEBOUNCE_SECONDS`: `kick-runner.sh` のデバウンス秒数（既定 5）

## ファイル配置

```text
/Volumes/memory/                                          # MEMORIES_DIR の既定値（SMB / NFS など共有のマウントポイント、永続データ）
├── raw/
│   ├── session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md      # kind: session（recording が自動生成）
│   ├── web/YYYY-MM-DD/HHMMSS_<slug>.md                   # kind: web（recording 手動）
│   └── minutes/YYYY-MM-DD/HHMMSS_<slug>.md               # kind: minutes（recording 手動）
└── wiki/
    ├── index.md                                           # 自動再生成（Sessions Timeline / References Library / Minutes への入口）
    ├── projects/<project>.md                              # Codex が統合・更新（kind: session）
    ├── references.md                                      # Codex が統合・更新（kind: web）
    └── minutes/<YYYYMM>.md                                # Codex が統合・更新（kind: minutes、月次集約）

~/.local/share/episodic/state/                            # 永続 state（OS 再起動でも保持）
├── ingest-queue.jsonl                                     # 未処理キュー（pending / processing、kind / attempt_count / retry_after_epoch を含む）
├── ingest-deadletter.jsonl                                # MAX_ATTEMPTS 超過の dead-letter（手動復旧用）
├── lock.d/                                                # runner 全体ロック（mkdir 方式、中に pid ファイル）
├── wiki-runner-kick.lock.d/                               # kick-runner デバウンスロック
└── wiki-target-locks/<sha256>.lock.d/                     # Wiki target 別 sub-lock（並列処理時の直列化）

/tmp/episodic/                                             # ローカル揮発（OS 再起動で消える）
├── session-hook.log                                       # Stop hook ログ
├── session-runner.log                                     # runner ログ
├── wiki-runner.log                                        # wiki-runner ログ
├── cocoindex-update.log                                   # cocoindex update ログ
└── smb-mount.log                                          # SMB マウント結果ログ
```

## 自動起動の流れ

`recording` の `runner.sh`（kind: session）/ `fetch-jina.sh`（kind: web）/ `save.sh`（kind: minutes）が Raw を書いた直後に、以下を fire-and-forget で実行する:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wiki/enqueue.py" "$RAW_PATH" --kind <kind>
( nohup "${CLAUDE_PLUGIN_ROOT}/scripts/wiki/kick-runner.sh" >> /tmp/episodic/wiki-runner.log 2>&1 & )
```

JSONL への append-only 追記は POSIX 上で原子的なので、複数プロセス並行でも壊れない（ロック不要）。`kick-runner.sh` は debounce ロックで束ね、`wiki-runner.sh` 自体は mkdir ロックで排他制御されるため、複数 Raw 同時生成でも安全。`codex` コマンドが PATH 上に無い環境では自動的に `--no-codex` モードへ降格し、キュー消化のみ行う。

### kick-runner.sh 動作内容

1. `wiki-runner-kick.lock.d` を mkdir で取得（取れなければ debounce 中なので即降りる、10 分以上残っていれば stale として奪取）
2. バックグラウンドで `MEMORIES_WIKI_KICK_DEBOUNCE_SECONDS` 待機 → 既存 runner が動いていれば終わるまで wait
3. kick lock を解放したうえで、queue に ready な entry（`status: pending` で `retry_after_epoch` 到達済み、または `status: processing` で 1h 超過）が残っていれば `wiki-runner.sh` を nohup で起動。残っていなければ何もしない

### wiki-runner.sh 動作内容

1. `mkdir .state/lock.d` で排他取得（取れなければ即終了。死んだプロセスのロックは PID 生存確認で奪取）
2. 旧 `/tmp/memories/state/ingest-queue.jsonl` に残りがあれば新 state へマージ（互換移行）
3. `ingest-queue.jsonl` から ready entry を抽出（`status: pending` で `retry_after_epoch` 到達済み、または `status: processing` で `MEMORIES_WIKI_PROCESSING_TIMEOUT_SECONDS` 超過の stuck）
4. 抽出した entry を `status: processing` に書き戻して claim（`processing_started_epoch` / `runner_pid` を付与、flock で排他更新）
5. (kind, wiki_target, instruction, model) で group 化し、各 group を `MEMORIES_WIKI_BATCH_SIZE` 件ごとの batch に分割
6. batch ごとに `wiki-target-locks/<sha256>.lock.d` を取り、`MEMORIES_WIKI_PARALLELISM` 並列で Codex 呼び出し:
   - `kind: session`: frontmatter から `project` 抽出 → `wiki/projects/<project>.md`（`codex-instruction.md`）
   - `kind: web`: → `wiki/references.md`（`codex-instruction-web.md`）
   - `kind: minutes`: frontmatter の `date` から `YYYYMM` 抽出 → `wiki/minutes/<YYYYMM>.md`（`codex-instruction-minutes.md`、月次集約）
7. 結果反映: 成功は queue から削除、失敗は `attempt_count` 加算 + 指数 backoff の `retry_after_epoch` を付けて `status: pending` に戻す。`MEMORIES_WIKI_MAX_ATTEMPTS` 到達分は `ingest-deadletter.jsonl` に append
8. self-poll で次イテレーションへ（pending hash が変化しなければ break、上限は `MEMORIES_WIKI_MAX_SELF_POLL`）
9. `wiki/index.md` を 3 章立て（**Sessions Timeline** / **References Library** / **Minutes**）で機械再生成。AppleDouble（`._*`）と隠しファイルは除外
10. `PROCESSED_COUNT > 0` なら **`scripts/lib/cocoindex_trigger.sh` 経由で cocoindex update を 1 回だけ非同期キック**（statistical 統合先 raw/wiki 双方を `MEMORIES_DIR` 配下で再インデックス）。runner.sh / sync-pending.sh / fetch-jina.sh / save.sh からは直接呼ばず、wiki-runner.sh への集約で **2 重起動を排除**

## 手動実行（デバッグ・再構築）

任意のタイミングで全件再処理する場合、`raw/{session,web,minutes}` 配下のファイルを直接 enqueue する:

```bash
MEMORIES_DIR="${MEMORIES_DIR:-/Volumes/memory}"
ENQUEUE="${CLAUDE_PLUGIN_ROOT}/scripts/wiki/enqueue.py"

# kind 別に raw を再投入（隠しファイル・AppleDouble は除外）
for kind in session web minutes; do
    find "$MEMORIES_DIR/raw/$kind" -type f -name '*.md' ! -name '.*' ! -name '._*' -print0 \
        | xargs -0 -I{} python3 "$ENQUEUE" "{}" --kind "$kind"
done

# 実行
"${CLAUDE_PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh"
```

特定 1 ファイルのみの再処理:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wiki/enqueue.py" \
    "/Volumes/memory/raw/web/2026-04-29/HHMMSS_xxx.md" --kind web
"${CLAUDE_PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh"
```

## ログ・トラブルシューティング

- 実行ログ: `/tmp/episodic/wiki-runner.log`（kick-runner.sh も同じファイルに append する）
- ロック残留（プロセス異常終了時）: 次回起動時に PID 生存確認で自動奪取される。即時に解除したい場合は `rm -rf ~/.local/share/episodic/state/lock.d ~/.local/share/episodic/state/wiki-runner-kick.lock.d ~/.local/share/episodic/state/wiki-target-locks`
- Codex 失敗で pending が残る: 失敗エントリは指数 backoff で `retry_after_epoch` を付けて待機する。即時再試行したい場合は queue から該当エントリの `retry_after_epoch` を 0 にするか、`--no-codex` でキューだけ消化する
- dead-letter に積まれた: `ingest-deadletter.jsonl` の `raw_path` を確認し、根本原因を解消したうえで再 enqueue する（`enqueue.py` でキュー末尾に追加すれば再処理される）
- 同じ Raw が複数回統合される（重複）: 各 codex-instruction の「重複排除」ルールが効いていない可能性。該当 Wiki ファイル（`projects/<p>.md` / `references.md` / `minutes/<YYYYMM>.md`）を一度削除して再構築する
- `references.md` / `minutes/<YYYYMM>.md` が生成されない: `raw/web/` / `raw/minutes/` 配下にまだファイルがない（`episodic-recording` skill から手動保存する）。または codex 呼び出しが失敗（log を参照）
- index.md に AppleDouble (`._*`) が混入: 解消済（v0.4.0 以降）。古い index.md が残っている場合は wiki-runner.sh 再実行で上書きされる
