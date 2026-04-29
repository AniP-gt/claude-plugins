---
name: memory-setup
description: memory プラグインの初期設定手順。インストール直後の前提確認・config.toml 作成・SMB 共有のマウント設定（任意）・cocoindex 連携の起動・初回 Raw 生成テストまでをガイドする。「memory プラグインの初期設定」「memory のセットアップ」「memory プラグインを使い始めたい」等で起動する。
---

# Memory Setup Skill

`memory@hidetsugu-miya` プラグインを `/plugin install` した直後に通る初期設定手順。プラグイン自体はインストール時点で hook が登録されるため、最低限の前提を満たせば即動作する。本 skill は前提確認とつまずき箇所のチェックリスト。

## 0. このプラグインが想定する環境

- **macOS が一級サポート**（通知・Terminal 起動・SMB マウント）。Linux/Windows でも Raw 生成本体は動作するが、これらの mac 専用機能は自動的にスキップされる
- 永続保存先は SMB/NFS など共有マウント前提（複数マシンで Raw を共有する想定）。単一マシン・ローカルのみで使うなら `memories_dir = "~/memory"` などにできる

## 1. 必須コマンド

| コマンド | 用途 | 入手 |
|---|---|---|
| `codex` | Raw 要約・Wiki 統合（Codex CLI） | <https://github.com/openai/codex> |
| `python3` (>= 3.10) | hook / lib 実装 | macOS 同梱 / Homebrew |
| `uv` | cocoindex プラグイン venv 経由の実行 | `brew install uv` または `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

`codex` 不在では Raw 生成本体が失敗する。`uv` 不在では cocoindex 更新だけがスキップされる。

## 2. 関連プラグインのインストール（検索を使うなら必須）

```text
/plugin install cocoindex@hidetsugu-miya
```

`cocoindex` プラグインは Python venv（`scripts/.venv`）と PostgreSQL（pgvector）を提供する。本プラグインの `scripts/lib/cocoindex_path.py` がインストール済みバージョンを semver で動的解決するため、cocoindex 側のバージョンが上がっても追従する。

`/cocoindex-setup` で PostgreSQL コンテナ起動・`secrets.env` 初期化を済ませること。

## 3. 設定ファイル（`~/.config/recording/config.toml`）

### 雛形コピー

```bash
mkdir -p ~/.config/recording
cp "${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml" ~/.config/recording/config.toml
```

`${CLAUDE_PLUGIN_ROOT}` が展開されない環境（ターミナル直打ち等）は次のいずれか:

```bash
# 絶対パス（インストールキャッシュ）
cp ~/.claude/plugins/cache/hidetsugu-miya/memory/templates/config.example.toml \
   ~/.config/recording/config.toml
```

### 主要オプション

| キー | 既定値 | 推奨上書き |
|---|---|---|
| `memories_dir` | `/Volumes/memory` | 単一マシン運用なら `~/memory` 等 |
| `fallback_dir` | `~/.local/share/recording/raw-staging` | そのままで可 |
| `auto_remount` | `true` | SMB を使わないなら `false` |
| `remount_script` | プラグイン同梱の `mount-memory-share.sh` | 自前のマウントスクリプトに差し替え可能 |
| `mount_canary_filename` | `.mount-canary` | `memories_dir` 直下に置く判定ファイル名 |
| `hostname_hash_length` | `8` | 複数マシン共有の衝突確率調整 |

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
| `CODEX_RECORDING_MODEL` | Raw 要約モデル（既定 `gpt-5.4-mini`） |
| `CODEX_MEMORY_WIKI_MODEL` | Wiki 統合モデル（既定 `gpt-5.4`） |
| `MEMORIES_EMBEDDING_MODEL` | 検索用 embedding（既定 `voyage-3-large`） |
| `MEMORIES_SEARCH_BACKEND` | 検索バックエンド（`dense` 既定 / `hybrid`） |

## 4. マウントポイントの準備

### A. SMB 共有を使う場合（マルチマシン共有・推奨）

1. SMB サーバ側でマウント検証用 canary を配置:

   ```bash
   # サーバ側 / マウント済みクライアントで一度だけ
   touch /path/to/share/.mount-canary
   ```

2. クライアント（macOS）でキーチェーンに資格情報を保存:

   ```bash
   # 一度 Finder からマウントして「キーチェーンに保存」を選ぶか、
   # security コマンドで保存する
   /sbin/mount_smbfs //user@host/share /Volumes/memory
   ```

3. プラグイン同梱の `mount-memory-share.sh` を使う場合、SHARE/PING_HOST を環境変数で上書き:

   ```bash
   # 例: ~/.zshrc などに記載
   export MEMORIES_SMB_SHARE="//user@server.local/memory"
   export MEMORIES_SMB_PING_HOST="server.local"   # 省略時は SHARE から自動抽出
   ```

   または config.toml の `remount_script` を自前のラッパーに差し替える:

   ```toml
   remount_script = "~/bin/my-mount-memory.sh"
   ```

4. 自動再マウント（任意）。LaunchAgent などから `mount-memory-share.sh` を起動するか、`auto_remount = true`（既定）で SessionEnd hook が未確立検出時に呼ぶ。

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

## 5. cocoindex 側の準備（検索が必要なら）

```bash
# cocoindex プラグインの初回セットアップ（PostgreSQL 起動・secrets.env 雛形）
/cocoindex-setup
```

`~/.config/cocoindex/secrets.env` に embedding API キー（既定では Voyage AI の `VOYAGE_API_KEY`）を設定する。

memory プラグイン専用設定 `~/.config/memory/cocoindex.toml` は `main_memory.py` 起動時に自動コピーされる（既存ファイルは上書きしない）。

## 6. 動作確認

### A. hook が有効か

```bash
# プラグイン有効化（インストール時に自動有効化されない場合）
/plugin enable memory@hidetsugu-miya
```

### B. 初回 Raw 生成

任意のセッションを終了すると `SessionEnd` hook が走り、Terminal が立ち上がって codex が要約する。完了後:

```bash
ls "$(cat ~/.config/recording/config.toml | grep memories_dir | head -1 | cut -d'"' -f2)/raw" 2>/dev/null \
  || ls /Volumes/memory/raw 2>/dev/null
```

うまくいかない場合は `/tmp/memories/recording-{hook,runner,sync}.log` を確認。

### C. 検索の動作確認

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/search/search.sh" "テスト" --top 3
```

cocoindex 側のインデックスが空なら結果ゼロが返る（エラーではない）。SessionEnd hook が走るたびに自動でインデックスが更新される。

## 7. アンインストール

```text
/plugin uninstall memory@hidetsugu-miya
```

`~/.config/recording/config.toml` と `<memories_dir>/` 配下のデータは保持される。完全削除する場合は手動で:

```bash
rm -rf ~/.config/recording ~/.config/memory
rm -rf /tmp/memories
# 永続データは自己責任で
# rm -rf <memories_dir>
```

## トラブルシューティング

| 症状 | 確認先 |
|---|---|
| Raw が生成されない | `/tmp/memories/recording-runner.log`、`codex` コマンド存在 |
| hook が呼ばれない | `/tmp/memories/recording-hook.log`、`/plugin status memory` |
| Terminal が起動しない（macOS 以外） | これは仕様。launcher が直接バックグラウンド実行されログ集約 |
| マウント検出が失敗する | `<memories_dir>/.mount-canary` の実在を確認 |
| 検索結果が空 | cocoindex 側の起動・テーブル存在・SessionEnd hook の実行履歴を確認 |
| `cocoindex update skipped: ... uv not found` | `brew install uv` |

## 関連

- 詳細アーキテクチャ: `${CLAUDE_PLUGIN_ROOT}/skills/recording/references/architecture.md`
- 検索の仕様: `${CLAUDE_PLUGIN_ROOT}/skills/memory-search/SKILL.md`
- Wiki 統合の仕様: `${CLAUDE_PLUGIN_ROOT}/skills/recording/references/wiki.md`
