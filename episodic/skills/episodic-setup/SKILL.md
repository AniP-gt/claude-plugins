---
name: episodic-setup
description: episodic プラグインの初期設定手順。インストール直後の前提確認・config.toml 作成・SMB 共有のマウント設定（任意）・cocoindex 連携の起動・初回 Raw 生成テストまでをガイドする。「episodic プラグインの初期設定」「episodic のセットアップ」「episodic プラグインを使い始めたい」等で起動する。
---

# Episodic Setup Skill

`episodic@hidetsugu-miya` プラグインを `/plugin install` した直後に通る初期設定手順。プラグイン自体はインストール時点で hook が登録されるため、最低限の前提を満たせば即動作する。本 skill は前提確認とつまずき箇所のチェックリスト。

## 0. このプラグインが想定する環境

- **macOS が一級サポート**（通知・Terminal 起動・SMB マウント）。Linux/Windows でも Raw 生成本体は動作するが、これらの mac 専用機能は自動的にスキップされる
- 永続保存先は SMB/NFS など共有マウント前提（複数マシンで Raw を共有する想定）。単一マシン・ローカルのみで使うなら `memories_dir = "~/memory"` などにできる

## 1. 必須コマンド

| コマンド | 用途 | 入手 |
|---|---|---|
| `codex` | Raw 要約・Wiki 統合（Codex CLI） | <https://github.com/openai/codex> |
| `python3` (>= 3.12) | episodic 専用 Python 環境の実行基盤 | macOS 同梱 / Homebrew |
| `uv` | episodic プラグイン専用 Python 環境（既定 `~/.cache/episodic/venv`）の管理と `cocoindex update` 実行 | `brew install uv` または `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `docker` | PostgreSQL（pgvector）コンテナの起動 | Docker Desktop / OrbStack |

`codex` 不在では Raw 生成本体が失敗する。`uv` / `docker` 不在では cocoindex 更新と検索だけがスキップされる。

## 2. 関連プラグインのインストール（PostgreSQL コンテナを共用する場合）

episodic プラグインは PostgreSQL コンテナ（pgvector）を `cocoindex` プラグインと**共用**する設計（同一インスタンス上で別 database を使い分け）。検索を有効化するには PostgreSQL が必要なので、未インストールなら以下を実行する:

```text
/plugin install cocoindex@hidetsugu-miya
```

`/cocoindex-setup` で PostgreSQL コンテナ起動・`~/.config/cocoindex/secrets.env` 初期化を済ませる。episodic プラグインは独立した Python 環境（既定 `~/.cache/episodic/venv`）と独立した database（`episodic`）を持つため、cocoindex プラグインのコード変更による影響は受けない。

すでに同等の PostgreSQL（localhost:15432）が立ち上がっていれば `cocoindex` プラグインを入れずに `~/.config/episodic/.env` の `EPISODIC_DATABASE_URL` を任意の URL に書き換えてもよい。

## 3. 設定ファイル（`~/.config/episodic/config.toml`）

### 雛形コピー

```bash
mkdir -p ~/.config/episodic
cp "${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml" ~/.config/episodic/config.toml
```

`${CLAUDE_PLUGIN_ROOT}` が展開されない環境（ターミナル直打ち等）は次のいずれか:

```bash
# 絶対パス（インストールキャッシュ）
cp ~/.claude/plugins/cache/hidetsugu-miya/episodic/templates/config.example.toml \
   ~/.config/episodic/config.toml
```

### 主要オプション

| キー | 既定値 | 推奨上書き |
|---|---|---|
| `memories_dir` | `/Volumes/memory` | 単一マシン運用なら `~/memory` 等 |
| `fallback_dir` | `~/.local/share/episodic/raw-staging` | そのままで可 |
| `auto_remount` | `true` | SMB を使わないなら `false` |
| `remount_script` | プラグイン同梱の `mount-memory-share.sh` | 自前のマウントスクリプトに差し替え可能 |
| `mount_canary_filename` | `.mount-canary` | `memories_dir` 直下に置く判定ファイル名 |
| `hostname_hash_length` | `8` | 複数マシン共有の衝突確率調整 |
| `stop_debounce_seconds` | `60` | Stop hook 連投から Codex 起動までの debounce 秒数（0-600） |
| `session_codex_timeout_seconds` | `300` | session 要約 Codex の wall-clock timeout 秒数（0 で無効） |
| `wiki_codex_timeout_seconds` | `1200` | wiki 統合 Codex の wall-clock timeout 秒数（0 で無効） |

### 環境変数による上書き

config.toml より env が優先される。一時的な切り替えに便利:

| 環境変数 | 上書き対象 |
|---|---|
| `MEMORIES_DIR` | `memories_dir` |
| `MEMORIES_FALLBACK_DIR` | `fallback_dir` |
| `MEMORIES_AUTO_REMOUNT` | `auto_remount`（`1`/`true`/`yes`/`on`） |
| `MEMORIES_REMOUNT_SCRIPT` | `remount_script` |
| `MEMORIES_MOUNT_CANARY` | `mount_canary_filename` |
| `MEMORIES_HOSTNAME_HASH_LENGTH` | `hostname_hash_length` |
| `MEMORIES_STOP_DEBOUNCE_SECONDS` | `stop_debounce_seconds`（Stop hook 起動から Codex 要約までの debounce 秒数。範囲 0-600） |
| `MEMORIES_SESSION_CODEX_TIMEOUT_SECONDS` | `session_codex_timeout_seconds` |
| `MEMORIES_WIKI_CODEX_TIMEOUT_SECONDS` | `wiki_codex_timeout_seconds` |
| `CODEX_RECORDING_MODEL` | Raw 要約モデル（既定 `gpt-5.4-mini`） |
| `CODEX_MEMORY_WIKI_MODEL_SESSION` / `_WEB` / `_MINUTES` | Wiki 統合モデル（既定 `gpt-5.4` / `gpt-5.4-mini` / `gpt-5.4-mini`） |
| `MEMORIES_EMBEDDING_MODEL` | 検索用 embedding（既定 `voyage-3-large`） |
| `EPISODIC_DATABASE_URL` | episodic 専用 PostgreSQL 接続 URL。`setup_db.sh` が `scripts/templates/episodic.env.example` を `~/.config/episodic/.env` にコピーして供給する（雛形に local-dev 用の URL が記載されている） |

## 4. マウントポイントの準備

### A. SMB 共有を使う場合（マルチマシン共有・推奨）

1. マウントポイントを空ディレクトリとして永続化（初回のみ sudo 必要）:

   ```bash
   sudo install -d -o "$(id -un)" -g staff -m 0755 /Volumes/memory
   ```

   `mount-memory-share.sh` は `mount_smbfs` を直接呼び出す設計で、事前に空ディレクトリが存在する前提でオーバーレイマウントする。旧実装の AppleScript `mount volume` 経由では、目的マウントポイントに既存ディレクトリ＋中身があると衝突回避で `-1` サフィックス付きパス（例: `/Volumes/memory-1`）へ黙ってずらすため、残骸ディレクトリが残ると別パスにマウントされて気付かない事故が起きていた。空ディレクトリで永続化することでこれを回避する。

2. SMB サーバ側でマウント検証用 canary を配置:

   ```bash
   # サーバ側 / マウント済みクライアントで一度だけ
   touch /path/to/share/.mount-canary
   ```

3. クライアント（macOS）でキーチェーンに資格情報を保存:

   ```bash
   # 一度 Finder からマウントして「キーチェーンに保存」を選ぶか、
   # 以下を手動実行してパスワード保存ダイアログに従う
   /sbin/mount_smbfs //user@host/share /Volumes/memory
   /sbin/umount /Volumes/memory   # 保存目的のため直後に umount
   ```

   以降 `mount-memory-share.sh` は `-N`（対話なし）でキーチェーン認証のみ使う。

4. プラグイン同梱の `mount-memory-share.sh` を使う場合、共有 URL は config.toml に、user 名は secrets.env に書く:

   ```toml
   # ~/.config/episodic/config.toml
   smb_share = "//192.168.11.5/memory"        # 形式: //[user@]host/share
   # smb_ping_host = "192.168.11.5"           # 省略時は smb_share から自動抽出
   ```

   ```bash
   # ~/.config/episodic/secrets.env （chmod 600 必須）
   MEMORIES_SMB_USER=admin
   ```

   ```bash
   # 権限設定（必須。0600 でないとスクリプトが読み込みを拒否する）
   chmod 600 ~/.config/episodic/secrets.env
   ```

   優先順位は環境変数 > secrets.env > config.toml > プレースホルダ既定（fail）。
   一時的な上書きをしたい場合は `MEMORIES_SMB_SHARE` / `MEMORIES_SMB_USER` / `MEMORIES_SMB_PING_HOST` を export する。

   config.toml の `remount_script` を自前のラッパーに差し替えることも可能:

   ```toml
   remount_script = "~/bin/my-mount-memory.sh"
   ```

5. 自動再マウント（任意）。LaunchAgent などから `mount-memory-share.sh` を起動するか、`auto_remount = true`（既定）で Stop hook が未確立検出時に呼ぶ。

### B. SMB を使わずローカルのみで使う場合

```toml
memories_dir = "~/memory"
auto_remount = false
```

```bash
mkdir -p ~/memory/raw
touch ~/memory/.mount-canary   # canary 判定を常に成立させる
```

### C. Linux/Windows などで SMB を使う場合

`mount.cifs` / `net use` などを叩く自前ラッパーを書き、config.toml の `remount_script` で差し替える。

## 5. episodic database のセットアップ（検索が必要なら）

episodic プラグイン専用 database（`episodic`）と pgvector 拡張を冪等作成する:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/setup_db.sh"
```

Codex の `SessionStart` hook から staging 同期を使う場合は、同梱 template を `~/.config/episodic/codex-hook-runtime/` に展開する:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/install-bin.sh"
```

コピー元は plugin source ツリー直下の `bin/` / `lib/` / `session/` / `recording/` / `wiki/` / `scripts/` / `pyproject.toml` / `uv.lock` / `templates/cocoindex.toml.example`。Codex hook の command は `~/.config/episodic/codex-hook-runtime/bin/session-start.sh` を指す。

このスクリプトが行うこと（既存は触らない）:

1. `~/.config/episodic/.env`（接続 URL の雛形）を生成
2. `~/.config/episodic/secrets.env`（雛形）を生成
3. PostgreSQL コンテナ `cocoindex` 上に `episodic` database を `CREATE DATABASE`
4. episodic database に `CREATE EXTENSION vector`

`~/.config/episodic/secrets.env` で `VOYAGE_API_KEY` を未設定にした場合は、`~/.config/cocoindex/secrets.env` の値が fallback で使われる。

episodic プラグイン固有の embedding/chunk/exclude 設定は `~/.config/episodic/cocoindex.toml` で管理する（`main_episodic.py` 起動時に雛形が自動コピーされる）。

### 初回インデックス構築

```bash
cd ~/.config/episodic/codex-hook-runtime
SOURCE_PATH=/Volumes/memory \
  INDEX_NAME=episodic \
  PATTERNS="**/*.md" \
  UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$HOME/.cache/episodic/venv}" \
  uv run cocoindex update -f recording/main_episodic.py:EpisodicIndex_$(hostname | tr -c '[:alnum:]' '_' | tr A-Z a-z)_episodic
```

実 Stop hook 経由でも `session/runner.sh` から自動的に上記が呼ばれる。手動実行は初回確認用。

## 6. 動作確認

### A. hook が有効か

```bash
# プラグイン有効化（インストール時に自動有効化されない場合）
/plugin enable episodic@hidetsugu-miya
```

### B. 初回 Raw 生成

新規セッションで何度か応答するか、Claude Code を強制終了すると `Stop` hook の debounce タイマー満了後に Terminal が立ち上がって codex が要約する。完了後:

```bash
ls "$(cat ~/.config/episodic/config.toml | grep memories_dir | head -1 | cut -d'"' -f2)/raw" 2>/dev/null \
  || ls /Volumes/memory/raw 2>/dev/null
```

うまくいかない場合は `~/.local/state/episodic/logs/session-{hook,runner,sync,retry}.log` を確認。

### C. 検索の動作確認

```bash
"${EPISODIC_RUNTIME_ROOT:-$HOME/.config/episodic/codex-hook-runtime}/scripts/search/search.sh" "テスト" --top 3
```

cocoindex 側のインデックスが空なら結果ゼロが返る（エラーではない）。Stop hook の debounce 経由で要約が完了するたびに自動でインデックスが更新される。

## 7. アンインストール

```text
/plugin uninstall episodic@hidetsugu-miya
```

`~/.config/episodic/config.toml` と `<memories_dir>/` 配下のデータは保持される。完全削除する場合は手動で:

```bash
rm -rf ~/.config/episodic
rm -rf ~/.local/state/episodic     # logs と pending
rm -rf ~/.local/share/episodic     # state（ingest-queue 等）
# 永続データは自己責任で
# rm -rf <memories_dir>
```

## トラブルシューティング

| 症状 | 確認先 |
|---|---|
| Raw が生成されない | `~/.local/state/episodic/logs/session-runner.log`、`codex` コマンド存在 |
| Codex の usage limit / API エラーで Raw 失敗 | `~/.local/share/episodic/state/session-retry-queue.jsonl` に自動記録され、次回 SessionStart で `retry-pending.sh` が再生成を試みる。手動再試行は `${CLAUDE_PLUGIN_ROOT}/session/retry-pending.sh` |
| 5 回失敗で dead_letter に降格 | `~/.local/share/episodic/state/session-retry-deadletter.jsonl` を確認。手動回復は `hook.py` に session_id / cwd / transcript_path / `"source": "retry"` を JSON で渡して再投入 |
| hook が呼ばれない | `~/.local/state/episodic/logs/session-hook.log`、`/plugin status episodic` |
| Terminal が起動しない（macOS 以外） | これは仕様。launcher が直接バックグラウンド実行されログ集約 |
| マウント検出が失敗する | `<memories_dir>/.mount-canary` の実在を確認 |
| 保存が staging に溜まり続ける | `~/.local/state/episodic/logs/smb-mount.log` を確認。`abort: stale local stub` ならログ内案内通り `sudo mv` で残骸を退避し、`sudo install -d -o "$(id -un)" -g staff -m 0755 <memories_dir>` で空ディレクトリを再作成。`abort: mount point does not exist` なら同じ `install -d` で初回作成 |
| `mount failed: rc=...` | キーチェーンに資格情報が無いか期限切れ。`/sbin/mount_smbfs //user@host/share <memories_dir>` を手動実行して「キーチェーンに保存」を済ませる |
| 検索結果が空 | cocoindex 側の起動・テーブル存在・Stop hook の実行履歴を確認 |
| `cocoindex update skipped: ... uv not found` | `brew install uv` |
| `DuplicateTableError: relation "..." already exists` | cocoindex プラグインの schema migration 不整合。下記「DuplicateTableError 復旧手順」を参照 |
| `--scope web` / `--scope minutes` で常に空 | cocoindex update が一度も成功していない可能性。`~/.local/state/episodic/logs/cocoindex-update.log` を確認 |

### memory テーブルの再構築手順

スキーマ衝突などで再構築が必要な場合:

```bash
# 1. 既存テーブルを drop（embedding は再生成される）
HOST_PREFIX="$(hostname | sed 's/[^a-zA-Z0-9]/_/g' | tr '[:upper:]' '[:lower:]')"
docker exec cocoindex psql -U postgres -d episodic \
    -c "DROP TABLE IF EXISTS public.episodicindex_${HOST_PREFIX}_episodic__chunks CASCADE;"

# 2. 手動で update を流して再構築
PLUGIN_ROOT=~/.config/episodic/codex-hook-runtime \
LOG_DIR_LOCAL=~/.local/state/episodic/logs \
MEMORIES_DIR=/Volumes/memory \
bash -c 'source "$PLUGIN_ROOT/lib/cocoindex_trigger.sh" && trigger_cocoindex_update'

# 3. ログで成功確認
tail -f ~/.local/state/episodic/logs/cocoindex-update.log
```

## 関連

- 詳細アーキテクチャ: `${CLAUDE_PLUGIN_ROOT}/skills/episodic-recording/references/architecture.md`
- 検索の仕様: `${CLAUDE_PLUGIN_ROOT}/skills/episodic-search/SKILL.md`
- Wiki 統合の仕様: `${CLAUDE_PLUGIN_ROOT}/skills/episodic-recording/references/wiki.md`
