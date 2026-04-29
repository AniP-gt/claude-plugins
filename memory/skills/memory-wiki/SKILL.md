---
name: memory-wiki
description: エピソード記憶の Raw（memories/raw/）を統合した Wiki（memories/wiki/）を生成・更新するスキル。Raw 生成完了通知（ingest-queue.jsonl）を消化し、プロジェクト通史・索引を Codex で再構築する。mkdir 方式の排他制御で複数 Raw 同時生成にも整合性を保つ。「wikiを更新して」「memoriesのwiki再生成」「ingest queueを処理して」等で起動する。
argument-hint: [--memories-dir PATH] [--no-codex]
---

# Memory Wiki Skill

Raw（不変・追記専用の作業記録）を読み、プロジェクト通史・索引などの **二次資産（Wiki）** に統合・再生成するスキル。

## 目的

- Raw を「いつ・何をしたか」の素材として、Wiki を「プロジェクト単位の通史・概念・索引」として保持する
- 複数 Raw が同時生成されても、Wiki 側を破壊しないように整合性を制御する
- 検索結果のノイズを減らす（Raw は時系列・粒度小、Wiki は集約・粒度大）

## 制約

- **Raw は immutable**: Wiki 統合中も Raw は読み取りのみ。書き換えない
- **Wiki は mutable**: Codex が再生成・上書きする。バージョン管理は Wiki ファイル自体の `updated_at` フロントマターで追う
- **排他制御必須**: `mkdir .state/lock.d` で原子的にロックを取得した1プロセスだけが Wiki を更新する（macOS に flock がないため mkdir 方式）。ロックが取れなければ即終了（後発は降りる）。プロセス異常終了でロックが残った場合は次回起動時に PID 生存確認で自動奪取
- **キュー駆動**: 処理対象は `.state/ingest-queue.jsonl` の `status: pending` エントリのみ。処理済みは `ingest-archive.jsonl` に追い出す
- **Codex 上位モデル使用**: 概念抽出・既存 Wiki との統合判断が必要なため、`gpt-5.4`（既定）を使う。`CODEX_MEMORY_WIKI_MODEL` で上書き可
- **Raw リンクの相対パス**: Wiki ファイルは `wiki/projects/X.md` に配置されるため、Raw への相対リンクは `../../raw/YYYY-MM-DD/file.md`（2階層上る）形式を厳守する。テンプレート（`scripts/codex-instruction.md`）にこの形式が固定で記載されている

## 完了条件

- `.state/ingest-queue.jsonl` の `status: pending` エントリが0件、もしくは Codex 失敗による pending 残のみ
- 処理済みエントリは `ingest-archive.jsonl` に追加されている
- `wiki/index.md` が最新の projects 一覧で再生成されている

## 入力パラメータ

| 引数 | 既定 | 説明 |
|---|---|---|
| `--memories-dir PATH` | `/Volumes/memory` | memories ルート |
| `--no-codex` | (false) | Codex 呼び出しをスキップ（キュー処理の動作確認用） |

環境変数:

- `MEMORIES_DIR`: memories ルート
- `CODEX_MEMORY_WIKI_MODEL`: Codex モデル（既定 `gpt-5.4`）

## ファイル配置

```text
/Volumes/memory/                                  # MEMORIES_DIR の既定値（SMB / NFS など共有のマウントポイント、永続データ）
├── raw/YYYY-MM-DD/<HHMMSS>_<sid8>.md            # memory-record が生成（不変）
└── wiki/
    ├── index.md                                  # 自動再生成（projects 一覧）
    └── projects/<project>.md                     # Codex が統合・更新

/tmp/memories/                                    # ローカル揮発（OS 再起動で消える）
├── memory-record-hook.log                        # hook ログ
├── memory-record-runner.log                      # runner ログ
├── memory-wiki-runner.log                        # wiki-runner ログ
├── smb-mount.log                                 # SMB マウント結果ログ
└── state/
    ├── ingest-queue.jsonl                        # 未処理キュー（pending エントリ）
    ├── ingest-archive.jsonl                      # 処理済みアーカイブ
    └── lock.d/                                   # 排他ロック（mkdir 方式、中に pid ファイル）
```

## Step 1: Raw 生成側からのキュー追記

`memory-record` の runner.sh が Raw を書いた直後に、本スキルの `enqueue.py` を呼んでキューへ1行追記する。

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wiki/enqueue.py" "$REPORT_PATH"
```

JSONL への append-only 追記は POSIX 上で原子的なので、複数プロセス並行でも壊れない（ロック不要）。

## Step 2: Wiki 統合の起動

キュー追記直後に `wiki-runner.sh` を起動する。複数 Raw 同時生成時は、最初の1本だけが mkdir でロックを取れて処理を行い、後発は即終了する（後発の Raw は先行プロセスが queue から拾う）。

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/wiki/wiki-runner.sh"
```

`runner.sh` 側からは `bash -c '... &' disown` のような形で fire-and-forget で叩くのが望ましい（Raw 生成 Terminal の終了をブロックしない）。`codex` コマンドが PATH 上に無い環境では自動的に `--no-codex` モードへ降格し、キュー消化のみ行う。

### 動作内容

1. `mkdir .state/lock.d` で排他取得（取れなければ即終了。死んだプロセスのロックは PID 生存確認で奪取）
2. `ingest-queue.jsonl` の `status: pending` エントリを全件読む
3. 各 Raw について:
   - frontmatter から `project` を抽出
   - `wiki/projects/<project>.md` を統合先として Codex に渡す
   - Codex が既存 Wiki を読みつつ Raw を統合し、`<project>.md` を上書き保存
4. `wiki/index.md` を projects 配下の md 一覧で再生成
5. 処理済みエントリを `ingest-archive.jsonl` に移し、queue を空に

## Step 3: 手動実行（デバッグ・再構築）

任意のタイミングで全件再処理:

```bash
# キューを再構築（archive を queue に戻す）
mv /tmp/memories/state/ingest-archive.jsonl{,.bak}
python3 -c "
import json
from pathlib import Path
arc = Path('/tmp/memories/state/ingest-archive.jsonl.bak')
queue = Path('/tmp/memories/state/ingest-queue.jsonl')
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
- ロック残留（プロセス異常終了時）: 次回起動時に PID 生存確認で自動奪取される。即時に解除したい場合は `rm -rf /tmp/memories/state/lock.d`
- Codex 失敗で pending が残る: log を確認し、`--no-codex` でキューだけ消化するか、手動で archive に移す
- 同じ session_id が複数回統合される（重複）: codex-instruction.md の「重複排除」ルールが効いていない可能性。Wiki 側を一度削除して再構築する

## 関連スキル

- `memory-record` — Raw 生成（このスキルの入力源）
- `memory-search` — Raw + Wiki に対するベクトル検索
