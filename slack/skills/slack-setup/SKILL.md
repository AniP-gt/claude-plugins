---
name: slack-setup
description: Slack MCP CLI の初期セットアップ skill。`~/.config/slack/bin/slack-mcp` wrapper を作成し、Codex / Claude / terminal から `CLAUDE_PLUGIN_ROOT` なしで Slack MCP を使えるようにする。「Slack MCP をセットアップ」「slack-mcp コマンドを作成」等で起動する。
argument-hint: [--plugin-root <path>]
---

# Slack Setup

Slack MCP CLI の実行入口を `~/.config/slack/bin/slack-mcp` に作成する。Codex では `CLAUDE_PLUGIN_ROOT` が存在しない場合があるため、skill はこの wrapper を標準コマンドとして使う。
あわせて `~/.codex/skills/slack-*` に symlink を作成し、Codex から Slack skill を直接検出できるようにする。

## 目的

- `~/.config/slack/bin/slack-mcp` を作成する
- wrapper から本 plugin の `scripts/slack_cli.py` を実行できるようにする
- `~/.codex/skills/slack-core` / `slack-connect` / `slack-bridge` / `slack-setup` を symlink として登録する
- 既存の token 保存先 `~/.config/slack/<workspace_key>/` と同じ管理単位に CLI 入口を置く

## 制約

- token、`tokens.json`、Authorization header を表示しない
- wrapper は絶対パスで `slack_cli.py` を参照する
- 既存 wrapper がある場合は内容を確認し、別パスを指していれば上書き前に差分を報告する
- 既存 Codex skill symlink がある場合は link 先を確認し、別パスを指していれば上書き前に差分を報告する
- `~/.config/slack/bin` は `0700`、wrapper は `0755` とする

## 完了条件

- `~/.config/slack/bin/slack-mcp --help` が成功する
- `~/.config/slack/bin/slack-mcp workspaces` が実行できる
- `slack-core` / `slack-connect` / `slack-bridge` が wrapper 経由の実行を前提にできる
- `~/.codex/skills/slack-*` の symlink が本 plugin の skill を指している

---

## Phase 1: plugin root の特定

### 目的

wrapper が参照する `slack_cli.py` の絶対パスを決定する。

### 制約

- `CLAUDE_PLUGIN_ROOT` があっても、それだけに依存しない
- このリポジトリ内の標準位置を優先する

### 完了条件

- 実在する `scripts/slack_cli.py` の絶対パスが確定している

#### Step 1: 候補パス確認

次の順で `scripts/slack_cli.py` を探す。

1. `--plugin-root <path>` が指定されていれば `<path>/scripts/slack_cli.py`
2. `${CLAUDE_PLUGIN_ROOT}/scripts/slack_cli.py`
3. `/Users/miya/workspace/mysis/claude-plugins/slack/scripts/slack_cli.py`
4. 現在の作業ディレクトリ配下の `slack/scripts/slack_cli.py`

#### Step 2: 実行確認

```bash
python3 <slack_cli.py> --help
```

---

## Phase 2: wrapper 作成

### 目的

`~/.config/slack/bin/slack-mcp` を作成し、実行権限を付与する。

### 制約

- wrapper は shell 依存を最小化する
- path に空白が入っても動くように引用する

### 完了条件

- wrapper が存在し、実行可能である

#### Step 1: ディレクトリ作成

```bash
mkdir -p ~/.config/slack/bin
chmod 700 ~/.config/slack ~/.config/slack/bin
```

#### Step 2: wrapper 作成

```bash
#!/usr/bin/env bash
set -euo pipefail
exec python3 "/absolute/path/to/slack/scripts/slack_cli.py" "$@"
```

#### Step 3: 権限設定

```bash
chmod 755 ~/.config/slack/bin/slack-mcp
```

---

## Phase 3: Codex skill 登録

### 目的

Codex の skill 検出パスへ Slack skill を登録する。

### 制約

- skill 本体は plugin 側を正とし、`~/.codex/skills` には symlink だけを置く
- 既存 symlink が異なるパスを指している場合は、上書き前に報告する

### 完了条件

- `~/.codex/skills/slack-core`
- `~/.codex/skills/slack-connect`
- `~/.codex/skills/slack-bridge`
- `~/.codex/skills/slack-setup`

上記がそれぞれ plugin 側の skill ディレクトリを指している。

#### Step 1: symlink 作成

```bash
ln -s /Users/miya/workspace/mysis/claude-plugins/slack/skills/slack-core ~/.codex/skills/slack-core
ln -s /Users/miya/workspace/mysis/claude-plugins/slack/skills/slack-connect ~/.codex/skills/slack-connect
ln -s /Users/miya/workspace/mysis/claude-plugins/slack/skills/slack-bridge ~/.codex/skills/slack-bridge
ln -s /Users/miya/workspace/mysis/claude-plugins/slack/skills/slack-setup ~/.codex/skills/slack-setup
```

---

## Phase 4: 動作確認

### 目的

Codex から `CLAUDE_PLUGIN_ROOT` なしで Slack MCP CLI を呼べることを確認する。

### 制約

- login はユーザーのブラウザ認証を伴うため、setup の確認では実行しない

### 完了条件

- `--help` と `workspaces` の実行結果を確認している

#### Step 1: help 確認

```bash
~/.config/slack/bin/slack-mcp --help
```

#### Step 2: workspace 確認

```bash
~/.config/slack/bin/slack-mcp workspaces
```

#### Step 3: Codex skill symlink 確認

```bash
find ~/.codex/skills -maxdepth 1 -type l -name 'slack-*' -ls
```
