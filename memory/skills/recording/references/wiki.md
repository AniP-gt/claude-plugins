# Wiki 統合パイプライン（運用ドキュメント）

`recording` skill が Raw を書いた直後に起動する **Wiki 統合パイプライン** の仕組み・配置・トラブルシューティング。普段は完全自動（fire-and-forget）で動くため、ユーザー・LLM が明示的に呼ぶ必要はない。本ドキュメントは **キュー再構築・ロック残留・debug** など運用事象が起きたときに参照する。

> 旧 `memory-wiki` skill の内容を移管したもの。skill としては提供せず、recording 配下のリファレンスとして保持する（v0.4.0 以降）。

## 目的

- Raw（不変・追記専用、kind: session / web / minutes）を、プロジェクト通史 + URL 参照索引 + 決定ログという **二次資産（Wiki）** に統合
- 複数 Raw 同時生成でも Wiki を破壊しない排他制御
- Raw（時系列・粒度小）と Wiki（集約・粒度大）の使い分けで検索ノイズを抑制

## kind 別の処理方針

| kind | 統合先 | Codex 呼び出し | instruction template |
|---|---|---|---|
| `session` | `wiki/projects/<project>.md`（project 単位通史） | あり | `scripts/wiki/codex-instruction.md` |
| `web` | `wiki/references.md`（テーマ別 + 時系列） | あり | `scripts/wiki/codex-instruction-web.md` |
| `minutes` | `wiki/decisions.md`（意思決定 + 議事 + アクション） | あり | `scripts/wiki/codex-instruction-minutes.md` |

3 種すべて Codex で統合する。`wiki/index.md` は機械生成で各統合先ファイルへの入口リンクと件数のみを保持する（再生成可、Codex は触らない）。

## 制約

- **Raw は immutable**: Wiki 統合中も Raw は読み取りのみ。書き換えない
- **Wiki は mutable**: Codex が再生成・上書きする。バージョン管理は Wiki ファイル自体の `updated_at` フロントマターで追う
- **排他制御必須**: `mkdir .state/lock.d` で原子的にロックを取得した1プロセスだけが Wiki を更新する（macOS に flock がないため mkdir 方式）。ロックが取れなければ即終了（後発は降りる）。プロセス異常終了でロックが残った場合は次回起動時に PID 生存確認で自動奪取
- **キュー駆動**: 処理対象は `~/.local/share/recording/state/ingest-queue.jsonl` の `status: pending` エントリのみ。処理済みは `ingest-archive.jsonl` に追い出す
- **state 永続化**: `~/.local/share/recording/state/` 配下に置く（OS 再起動でも pending を保持）。旧 `/tmp/memories/state/` は wiki-runner.sh 起動時に自動マージ
- **Codex 上位モデル使用**: 概念抽出・既存 Wiki との統合判断が必要なため、`gpt-5.4`（既定）を使う。`CODEX_MEMORY_WIKI_MODEL` で上書き可
- **kind 別リンク相対パス**:
    - `wiki/projects/<project>.md` → session へは `../../raw/session/YYYY-MM-DD/file.md`（2 階層上る）
    - `wiki/references.md` → web へは `../raw/web/YYYY-MM-DD/file.md`（1 階層上る）
    - `wiki/decisions.md` → minutes へは `../raw/minutes/YYYY-MM-DD/file.md`（1 階層上る）
- **書き込み制限**: Codex は kind 別の単一統合先ファイルにのみ書き込む。CWD を統合先親ディレクトリに固定して workspace-write を限定する

## 完了条件

- `ingest-queue.jsonl` の `status: pending` エントリが 0 件、もしくは Codex 失敗による pending 残のみ
- 処理済みエントリは `ingest-archive.jsonl` に追加されている
- `wiki/index.md` が最新の章立て（Sessions Timeline / References Library / Decisions Log）で再生成されている
- 該当 kind の統合先（`wiki/projects/<project>.md` / `wiki/references.md` / `wiki/decisions.md`）が Codex により更新されている

## 入力パラメータ（wiki-runner.sh）

| 引数 | 既定 | 説明 |
|---|---|---|
| `--memories-dir PATH` | `/Volumes/memory` | memories ルート |
| `--no-codex` | (false) | Codex 呼び出しをスキップ（キュー処理の動作確認用） |

環境変数:

- `MEMORIES_DIR`: memories ルート
- `CODEX_MEMORY_WIKI_MODEL`: Codex モデル（既定 `gpt-5.4`）

## ファイル配置

```text
/Volumes/memory/                                          # MEMORIES_DIR の既定値（SMB / NFS など共有のマウントポイント、永続データ）
├── raw/
│   ├── session/YYYY-MM-DD/HHMMSS_<host8>_<sid8>.md      # kind: session（recording が自動生成）
│   ├── web/YYYY-MM-DD/HHMMSS_<slug>.md                   # kind: web（recording 手動）
│   └── minutes/YYYY-MM-DD/HHMMSS_<slug>.md               # kind: minutes（recording 手動）
└── wiki/
    ├── index.md                                           # 自動再生成（Sessions Timeline / References Library / Decisions Log への入口）
    ├── projects/<project>.md                              # Codex が統合・更新（kind: session）
    ├── references.md                                      # Codex が統合・更新（kind: web）
    └── decisions.md                                       # Codex が統合・更新（kind: minutes）

~/.local/share/recording/state/                            # 永続 state（OS 再起動でも保持）
├── ingest-queue.jsonl                                     # 未処理キュー（pending エントリ、kind 含む）
├── ingest-archive.jsonl                                   # 処理済みアーカイブ
└── lock.d/                                                # 排他ロック（mkdir 方式、中に pid ファイル）

/tmp/memories/                                             # ローカル揮発（OS 再起動で消える）
├── recording-hook.log                                     # hook ログ
├── recording-runner.log                                   # runner ログ
├── memory-wiki-runner.log                                 # wiki-runner ログ
└── smb-mount.log                                          # SMB マウント結果ログ
```

## 自動起動の流れ

`recording` の `runner.sh`（kind: session）/ `fetch-jina.sh`（kind: web）/ `save.sh`（kind: minutes）が Raw を書いた直後に、以下を fire-and-forget で実行する:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wiki/enqueue.py" "$RAW_PATH" --kind <kind>
( nohup "${CLAUDE_PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh" >> /tmp/memories/memory-wiki-runner.log 2>&1 & )
```

JSONL への append-only 追記は POSIX 上で原子的なので、複数プロセス並行でも壊れない（ロック不要）。`wiki-runner.sh` は mkdir ロックで排他制御されるため、複数 Raw 同時生成でも安全。`codex` コマンドが PATH 上に無い環境では自動的に `--no-codex` モードへ降格し、キュー消化のみ行う。

### wiki-runner.sh 動作内容

1. `mkdir .state/lock.d` で排他取得（取れなければ即終了。死んだプロセスのロックは PID 生存確認で奪取）
2. 旧 `/tmp/memories/state/ingest-queue.jsonl` に残りがあれば新 state へマージ（互換移行）
3. `ingest-queue.jsonl` の `status: pending` エントリを全件読む（`raw_path`, `kind` の TSV へ整形）
4. 各エントリについて kind 別に Codex で統合:
   - `kind: session`: frontmatter から `project` 抽出 → `wiki/projects/<project>.md`（`codex-instruction.md`）
   - `kind: web`: → `wiki/references.md`（`codex-instruction-web.md`）
   - `kind: minutes`: → `wiki/decisions.md`（`codex-instruction-minutes.md`）
5. `wiki/index.md` を 3 章立て（**Sessions Timeline** / **References Library** / **Decisions Log**）で機械再生成。AppleDouble（`._*`）と隠しファイルは除外
6. 処理済みエントリを `ingest-archive.jsonl` に移し、queue を空に
7. `PROCESSED_COUNT > 0` なら **`scripts/lib/cocoindex_trigger.sh` 経由で cocoindex update を 1 回だけ非同期キック**（statistical 統合先 raw/wiki 双方を `MEMORIES_DIR` 配下で再インデックス）。runner.sh / sync-pending.sh / fetch-jina.sh / save.sh からは直接呼ばず、wiki-runner.sh への集約で **2 重起動を排除**

## 手動実行（デバッグ・再構築）

任意のタイミングで全件再処理:

```bash
# キューを再構築（archive を queue に戻す）
STATE_DIR="$HOME/.local/share/recording/state"
mv "$STATE_DIR/ingest-archive.jsonl"{,.bak}
python3 -c "
import json, os
from pathlib import Path
state = Path(os.environ['STATE_DIR'])
arc = state / 'ingest-archive.jsonl.bak'
queue = state / 'ingest-queue.jsonl'
with queue.open('a') as f:
    for line in arc.read_text().splitlines():
        d = json.loads(line)
        d['status'] = 'pending'
        f.write(json.dumps(d, ensure_ascii=False) + '\n')
"

# 実行
"${CLAUDE_PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh"
```

## ログ・トラブルシューティング

- 実行ログ: `/tmp/memories/memory-wiki-runner.log`
- ロック残留（プロセス異常終了時）: 次回起動時に PID 生存確認で自動奪取される。即時に解除したい場合は `rm -rf ~/.local/share/recording/state/lock.d`
- Codex 失敗で pending が残る: log を確認し、`--no-codex` でキューだけ消化するか、手動で archive に移す
- 同じ Raw が複数回統合される（重複）: 各 codex-instruction の「重複排除」ルールが効いていない可能性。該当 Wiki ファイル（`projects/<p>.md` / `references.md` / `decisions.md`）を一度削除して再構築する
- `references.md` / `decisions.md` が生成されない: `raw/web/` / `raw/minutes/` 配下にまだファイルがない（`recording` skill から手動保存する）。または codex 呼び出しが失敗（log を参照）
- index.md に AppleDouble (`._*`) が混入: 解消済（v0.4.0 以降）。古い index.md が残っている場合は wiki-runner.sh 再実行で上書きされる
