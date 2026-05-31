# claude-plugins

Custom Claude Code plugins by miya.

## Quick Start

マーケットプレイスを登録:

```text
/plugin marketplace add hidetsugu-miya/claude-plugins
```

使いたいプラグインをインストール:

```text
/plugin install pgvector-stack@hidetsugu-miya
/plugin install cocoindex-setup@hidetsugu-miya
/plugin install compass@hidetsugu-miya
/plugin install circleci@hidetsugu-miya
/plugin install devin@hidetsugu-miya
/plugin install mermaid@hidetsugu-miya
/plugin install episodic@hidetsugu-miya
/plugin install slack@hidetsugu-miya
```

インストール後、Claude Codeを再起動してください。

## Plugins

### pgvector-stack

pgvector 搭載 PostgreSQL コンテナを提供する最小プラグイン。`compass` / `episodic` 等の下流プラグインの DB 基盤として共有する。

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/compose.yml ~/.config/cocoindex/compose.yml
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

詳細は `pgvector-stack/skills/pgvector-stack-setup/SKILL.md` を参照。

### cocoindex-setup

`~/.config/cocoindex/` の `secrets.env` / `config.toml` を所有・auto-provision する共通基盤プラグイン。`compass` / `episodic` は本プラグインが提供する secrets/config を fallback として参照する。

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check_config.sh
```

その後 `~/.config/cocoindex/secrets.env` の `VOYAGE_API_KEY` を設定する。詳細は `cocoindex-setup/skills/cocoindex-setup/SKILL.md`。

### compass

コードベースのセマンティック検索プラグイン。pgvector + voyage embedding + voyage rerank で自然言語クエリから関連コードのエントリーポイントを発見する。専用 DB `compass`、テーブル `compassindex_*__chunks`、cocoindex 1.0 LiveUpdater 対応。

前提: `pgvector-stack` と `cocoindex-setup` のインストール・初期設定。詳細は `compass/skills/compass-setup/SKILL.md` / `compass/skills/compass-search/SKILL.md` を参照。

### circleci

CircleCI調査・ワークフロー監視プラグイン。@circleci/mcp-server-circleciをstdioで起動して調査ツール群（failures / tests / status / flaky / rerun / config 等）を提供しつつ、`circleci-watch` skill で目的状態到達まで CircleCI REST API を直接ポーリングして監視する。

環境変数 `CIRCLECI_TOKEN`（Personal API Token）を **Claude Code 起動前の shell に export** してください（`~/.zshrc` / `~/.bashrc` 等に `export CIRCLECI_TOKEN=...`）。`~/.claude/settings.json` の `env` ブロック経由では MCP サーバーへ伝播しません。Token は <https://app.circleci.com/settings/user/tokens> から取得してください。セルフホスト環境では `CIRCLECI_BASE_URL` も同じ要領で shell に export します。MCPツールは deferred tools として on-demand ロードされる。

### devin

Devin MCP経由でGitHubリポジトリ（プライベート含む）のドキュメント取得・質問応答（DeepWiki）を行い、Devin Session API CLI でタスク委任・状態確認・メッセージ送信を行うプラグイン。MCPは `https://mcp.devin.ai/mcp` に Bearer 認証で接続。

環境変数 `DEVIN_API_KEY` の設定が必要です（Personal API Key `apk_user_` プレフィックス）。`pip3 install requests` が必要です。MCPツール（DeepWiki）は deferred tools として on-demand ロード、Session API は `/devin-session` skill から実行できる。

### mermaid

Mermaid.jsダイアグラム画像出力プラグイン。@mermaid-js/mermaid-cliを使ってMermaid構文からPNG/SVG画像を生成する。

Node.js 20以上が必要です。使い方は `/mermaid-render` を実行してください。

### episodic

Claude Code セッションのエピソード記憶（Raw + Wiki）を管理するプラグイン。`SessionEnd` で会話履歴を Codex で要約して `<memories_dir>/raw/session/YYYY-MM-DD/` へ保存し、`SessionStart` で staging を正規パスへ移送する。`episodic-recording` skill から URL アーカイブ（kind: web）と議事録（kind: minutes）も手動保存でき、保存直後に Codex が `wiki/projects/<p>.md` / `wiki/references.md` / `wiki/decisions.md` を自動更新する。議事録は Notion URL を入力すると Notion MCP（`claude mcp add` で個別登録）経由でページ Markdown を取得して取り込める。minutes / diary からは人物 Wiki（`wiki/people/<slug>.md`、人名 slug・本人は `is_self` で 1 ページに集約）と組織 Wiki（`wiki/orgs/<slug>.md`、kind: org・web 裏取り付き）を Codex が自動抽出し、既存の人物・組織レジストリを注入してジョブ横断で名寄せする。重複検出・統合は `lib/wiki_reconcile.py`、組織の web 裏取り保守は `wiki/org_web_verify.py` の保守 CLI で行える。`episodic-setup` / `episodic-recording` / `episodic-search` の 3 skill を同梱し、cocoindex プラグイン（同マーケットプレイス）と連携してベクトル検索を提供する。

前提条件:

- `codex` CLI（Raw / Wiki 統合の双方で使用）。インストールされていない場合 Raw 生成は失敗、Wiki 統合はスキップされる
- cocoindex プラグイン（`/plugin install cocoindex@hidetsugu-miya`）と PostgreSQL（既定 localhost:15432）。検索・インデックス更新に使用
- macOS の場合、通知・Terminal 起動・SMB マウントが利用可能。それ以外の OS では該当コマンドが無いと自動スキップされ、Raw 生成本体はバックグラウンドで動作する
- 設定ファイル `~/.config/recording/config.toml`（任意。ひな形は `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml`）

インストール直後は `episodic-setup` skill（`episodic/skills/episodic-setup/SKILL.md`）の初期設定手順に従ってください。詳細アーキテクチャは `episodic/skills/episodic-recording/SKILL.md` および `episodic/skills/episodic-recording/references/architecture.md`、Wiki 統合パイプラインは `episodic/skills/episodic-recording/references/wiki.md` を参照。

### slack

Slack 公式 MCP サーバー（`https://mcp.slack.com/mcp`）に、公式 MCP Python SDK で OAuth 2.0 PKCE 接続する CLI とスキル群。Slack は Dynamic Client Registration 非対応のため、固定 CLIENT_ID を pre-populate して認証する。ワークスペース単位で `~/.config/slack/<workspace_key>/` に token を保存し、検索・チャンネル履歴取得・スレッド取得・メッセージ送信を MCP tool 経由で実行する。

前提条件:

- Python 3.10 以上
- `pip3 install -U 'mcp>=1.13' httpx`
- ブラウザ認証可能なデスクトップ環境（OrbStack ゲストはホスト macOS のブラウザを呼び出し可能）

インストール直後は `slack-setup` skill で `~/.config/slack/bin/slack-mcp` wrapper と `~/.codex/skills/slack-*` の symlink を作成し、`slack-connect` skill で `slack-mcp login` を実行する。実行系は `slack-bridge` skill から `slack-mcp call` で MCP tool を呼ぶ。詳細は `slack/skills/slack-core/SKILL.md`。
