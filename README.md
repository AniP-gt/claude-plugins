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
/plugin install context7@hidetsugu-miya
/plugin install rollbar@hidetsugu-miya
/plugin install sentry@hidetsugu-miya
/plugin install circleci@hidetsugu-miya
/plugin install figma@hidetsugu-miya
/plugin install playwright@hidetsugu-miya
/plugin install claude-mem@hidetsugu-miya
/plugin install devin@hidetsugu-miya
/plugin install chrome-devtools@hidetsugu-miya
/plugin install slack@hidetsugu-miya
/plugin install todoist@hidetsugu-miya
/plugin install atlassian@hidetsugu-miya
/plugin install drawio@hidetsugu-miya
/plugin install mermaid@hidetsugu-miya
/plugin install jina@hidetsugu-miya
/plugin install memory@hidetsugu-miya
```

インストール後、Claude Codeを再起動してください。

## Plugins

### pgvector-stack

pgvector 搭載 PostgreSQL コンテナを提供する最小プラグイン。`compass` / `memory` 等の下流プラグインの DB 基盤として共有する。

```bash
mkdir -p ~/.config/cocoindex
cp ${CLAUDE_PLUGIN_ROOT}/templates/compose.yml ~/.config/cocoindex/compose.yml
docker compose -f ~/.config/cocoindex/compose.yml up -d
```

詳細は `pgvector-stack/skills/pgvector-stack-setup/SKILL.md` を参照。

### cocoindex-setup

`~/.config/cocoindex/` の `secrets.env` / `config.toml` を所有・auto-provision する共通基盤プラグイン。`compass` / `memory` は本プラグインが提供する secrets/config を fallback として参照する。

```bash
bash ${CLAUDE_PLUGIN_ROOT}/scripts/check_config.sh
```

その後 `~/.config/cocoindex/secrets.env` の `VOYAGE_API_KEY` を設定する。詳細は `cocoindex-setup/skills/cocoindex-setup/SKILL.md`。

### compass

コードベースのセマンティック検索プラグイン。pgvector + voyage embedding + voyage rerank で自然言語クエリから関連コードのエントリーポイントを発見する。専用 DB `compass`、テーブル `compassindex_*__chunks`、cocoindex 1.0 LiveUpdater 対応。

前提: `pgvector-stack` と `cocoindex-setup` のインストール・初期設定。詳細は `compass/skills/compass-setup/SKILL.md` / `compass/skills/compass-search/SKILL.md` を参照。

### context7

ライブラリの最新ドキュメントを取得するプラグイン。Context7 MCPサーバーを使ってパッケージ名からIDを解決し、バージョン固有のドキュメントを参照する。

使い方は `/context7` を実行してください。

### rollbar

Rollbarのエラートラッキングデータを取得・管理するプラグイン。@rollbar/mcp-serverを使ってアイテム詳細、デプロイ情報、トップエラーの確認・更新を行う。

環境変数 `ROLLBAR_ACCESS_TOKEN` の設定が必要です。使い方は `/rollbar` を実行してください。

### sentry

Sentryのエラートラッキングデータを取得・管理するプラグイン。@sentry/mcp-serverを使ってイシュー詳細、プロジェクト情報、エラー分析を行う。

環境変数 `SENTRY_ACCESS_TOKEN` の設定が必要です。使い方は `/sentry` を実行してください。

### circleci

CircleCIのビルド失敗ログ・テスト結果・パイプライン状態を取得・操作するプラグイン。@circleci/mcp-server-circleciを使ってビルド失敗解析、flakyテスト検出、ワークフロー再実行、config検証などを行う。

環境変数 `CIRCLECI_TOKEN`（Personal API Token）の設定が必要です。Token は <https://app.circleci.com/settings/user/tokens> から取得してください。セルフホスト環境では `CIRCLECI_BASE_URL` も併せて設定します。使い方は circleci-investigate skill を参照してください。

### figma

Figmaデザインファイルの取得・コード生成プラグイン。Figma Dev Mode MCPサーバーと連携してデザインからReact+Tailwindコードを自動生成する。

Figmaデスクトップアプリと `pip3 install sseclient-py requests` が必要です。使い方は `/figma` を実行してください。

### playwright

Playwright MCPを使ったブラウザ自動化プラグイン。Webページのナビゲート、スナップショット取得、要素クリックなどのブラウザ操作をHTTPサーバーモードで実行する。

`pip3 install requests` と `npx @playwright/mcp@latest` が必要です。使い方は `/playwright-step` を実行してください。

### claude-mem

claude-mem永続メモリの検索・取得プラグイン。Worker HTTP API経由で過去のセッション情報、観察、タイムラインを参照する。接続先は環境変数 `CLAUDE_MEM_WORKER_HOST` / `CLAUDE_MEM_WORKER_PORT`、`~/.claude-mem/settings.json`、デフォルト（`127.0.0.1:37700 + UID % 100`）の順で自動解決する。

claude-mem Workerが起動していることが前提です。使い方は `/claude-mem-step` を実行してください。

### devin

Devin MCP/DeepWiki経由でGitHubリポジトリ（プライベート含む）のドキュメント構造取得・内容取得・質問応答を行うプラグイン。

プライベートリポジトリへのアクセスには環境変数 `DEVIN_API_KEY` の設定が必要です（Personal API Key `apk_user_` プレフィックス）。`pip3 install requests` が必要です。使い方は `/devin-step` を実行してください。

### chrome-devtools

Chrome DevTools MCPを使ったブラウザ自動化・デバッグプラグイン。DOMスナップショット、スクリーンショット、コンソールログ、ネットワーク監視、パフォーマンス分析などをHTTPサーバーモードで実行する。

`pip3 install requests` と `npx mcp-proxy` / `npx chrome-devtools-mcp` が必要です。使い方は `/chrome-devtools-step` を実行してください。

### slack

Slack MCP経由でメッセージ検索・送信・チャンネル読み取りを行うプラグイン。公式MCP Python SDKでOAuth認証し、Streamable HTTP経由でSlack MCPツールを実行する（複数ワークスペース対応）。

Python 3.10+ と `pip3 install 'mcp>=1.13' httpx` が必要です（Slack サーバーの新プロトコル対応のため）。初回は `/slack-login` でログインし（ブラウザが開く）、その後 `/slack-run` でツールを実行してください。

### todoist

Todoistタスク管理プラグイン。公式MCP Python SDKでOAuth 2.1認証し、Streamable HTTP経由でTodoist MCPツールを実行する。

Python 3.10+ と `pip3 install mcp httpx` が必要です。初回は `/todoist-login` でログインし（ブラウザが開く）、その後 `/todoist-run` でツールを実行してください。

### atlassian

Atlassian Rovo MCP経由でJira・Confluenceを操作するプラグイン。公式MCP Python SDKでOAuth 2.1認証し、Streamable HTTP経由でJira・Confluenceツールを実行する。

Python 3.10+ と `pip3 install mcp httpx` が必要です。初回は `/atlassian-login` でログインし（ブラウザが開く）、その後 `/atlassian-run` でツールを実行してください。

### drawio

draw.ioダイアグラム作成プラグイン。@drawio/mcpを使ってXML・CSV・Mermaid形式からダイアグラムを生成し、ブラウザのdraw.ioエディタで開く。

Node.js 20以上が必要です。使い方は `/drawio-create` を実行してください。

### mermaid

Mermaid.jsダイアグラム画像出力プラグイン。@mermaid-js/mermaid-cliを使ってMermaid構文からPNG/SVG画像を生成する。

Node.js 20以上が必要です。使い方は `/mermaid-render` を実行してください。

### jina

Jina AI Remote MCP経由でWeb検索・URLからのmarkdown抽出・arXiv/SSRN論文検索・リランク・分類などを実行するプラグイン。Streamable HTTPで `mcp.jina.ai/v1` にJSON-RPCを送信する。

`~/.config/jina/secrets.env` に `JINA_API_KEY=...` を設定してください（初回実行時にテンプレートから自動コピーされます）。API キーは <https://jina.ai/api-dashboard/key-manager/> から取得できます。使い方は `/jina-step` を実行してください。

### memory

Claude Code セッションのエピソード記憶（Raw + Wiki）を管理するプラグイン。`SessionEnd` で会話履歴を Codex で要約して `<memories_dir>/raw/session/YYYY-MM-DD/` へ保存し、`SessionStart` で staging を正規パスへ移送する。`recording` skill から URL アーカイブ（kind: web）と議事録（kind: minutes）も手動保存でき、保存直後に Codex が `wiki/projects/<p>.md` / `wiki/references.md` / `wiki/decisions.md` を自動更新する。`memory-setup` / `recording` / `memory-search` の 3 skill を同梱し、cocoindex プラグイン（同マーケットプレイス）と連携してベクトル検索を提供する。

前提条件:

- `codex` CLI（Raw / Wiki 統合の双方で使用）。インストールされていない場合 Raw 生成は失敗、Wiki 統合はスキップされる
- cocoindex プラグイン（`/plugin install cocoindex@hidetsugu-miya`）と PostgreSQL（既定 localhost:15432）。検索・インデックス更新に使用
- macOS の場合、通知・Terminal 起動・SMB マウントが利用可能。それ以外の OS では該当コマンドが無いと自動スキップされ、Raw 生成本体はバックグラウンドで動作する
- 設定ファイル `~/.config/recording/config.toml`（任意。ひな形は `${CLAUDE_PLUGIN_ROOT}/templates/config.example.toml`）

インストール直後は `memory-setup` skill（`memory/skills/memory-setup/SKILL.md`）の初期設定手順に従ってください。詳細アーキテクチャは `memory/skills/recording/SKILL.md` および `memory/skills/recording/references/architecture.md`、Wiki 統合パイプラインは `memory/skills/recording/references/wiki.md` を参照。
