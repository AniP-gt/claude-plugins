---
name: setup
description: LLM Wiki の初期設定。今いるリポジトリと wiki フォルダ（Obsidian Vault 内など）の対応を ~/.config/llm-wiki/projects.json に登録し、必要なら wiki の雛形を作る。「wiki を設定」「llm-wiki setup」で使う。
---

# LLM Wiki セットアップ

リポジトリと wiki の対応は各ユーザーのローカル設定に保存する。プラグインや対象リポジトリには書き込まない。

- 設定ファイル: `$LLM_WIKI_CONFIG`、未設定なら `~/.config/llm-wiki/projects.json`
- CLI: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py <subcommand>`
- 設定例: `${CLAUDE_PLUGIN_ROOT}/templates/projects.example.json`

## 手順

1. **現状確認**: `llm_wiki.py resolve` を実行する。登録済みならその内容を見せ、変更したいか確認する。
2. **聞く**（まとめて 1 回で聞く）:
   - wiki フォルダのパス（例: `~/Obsidian/MyVault/Projects/MyApp`）
   - プロジェクト名（既定: リポジトリのディレクトリ名）
   - 対象リポジトリ（既定: 今いるリポジトリの本体ルート。worktree 内なら本体を使う）
   複数リポジトリで 1 つの wiki を共有してよい。その場合はリポジトリごとに登録する。
3. **登録**: `llm_wiki.py add --name <名前> --repo <repo> --wiki <wiki>`
4. **雛形**: wiki フォルダに `index.md` が無ければ、作ってよいか確認してから `llm_wiki.py init-wiki --wiki <wiki>` を実行する。既存ファイルは上書きされない。
5. **確認**: `llm_wiki.py resolve` と `llm_wiki.py list` の結果を見せる。
6. **案内**: 次の Claude Code セッションから、SessionStart hook が wiki の場所を自動で伝えることを伝える。続けて `/llm-wiki:ingest` で最初の資料を取り込むよう提案する。

## 注意

- wiki がリポジトリの外（Vault など）にあるとき、サンドボックスで書き込みが拒否されることがある。その場合はユーザーに `/sandbox` で許可するか確認する。
- 登録の削除は `llm_wiki.py remove --name <名前>`。
