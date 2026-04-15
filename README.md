# claude-plugins

Custom Claude Code plugins by miya.

## Quick Start

マーケットプレイスを登録:

```text
/plugin marketplace add hidetsugu-miya/claude-plugins
```

使いたいプラグインをインストール:

```text
/plugin install cocoindex@hidetsugu-miya
/plugin install context7@hidetsugu-miya
/plugin install rollbar@hidetsugu-miya
/plugin install sentry@hidetsugu-miya
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
/plugin install ticktick@hidetsugu-miya
```

インストール後、Claude Codeを再起動してください。

## Plugins

### cocoindex

CocoIndex を使ったコードベースのベクトル検索プラグイン。自然言語クエリで関連コードのエントリーポイントを発見する。

初回セットアップは `/cocoindex-guide` を実行し、`references/setup.md` の手順に従ってください。

### context7

ライブラリの最新ドキュメントを取得するプラグイン。Context7 MCPサーバーを使ってパッケージ名からIDを解決し、バージョン固有のドキュメントを参照する。

使い方は `/context7` を実行してください。

### rollbar

Rollbarのエラートラッキングデータを取得・管理するプラグイン。@rollbar/mcp-serverを使ってアイテム詳細、デプロイ情報、トップエラーの確認・更新を行う。

環境変数 `ROLLBAR_ACCESS_TOKEN` の設定が必要です。使い方は `/rollbar` を実行してください。

### sentry

Sentryのエラートラッキングデータを取得・管理するプラグイン。@sentry/mcp-serverを使ってイシュー詳細、プロジェクト情報、エラー分析を行う。

環境変数 `SENTRY_ACCESS_TOKEN` の設定が必要です。使い方は `/sentry` を実行してください。

### figma

Figmaデザインファイルの取得・コード生成プラグイン。Figma Dev Mode MCPサーバーと連携してデザインからReact+Tailwindコードを自動生成する。

Figmaデスクトップアプリと `pip3 install sseclient-py requests` が必要です。使い方は `/figma` を実行してください。

### playwright

Playwright MCPを使ったブラウザ自動化プラグイン。Webページのナビゲート、スナップショット取得、要素クリックなどのブラウザ操作をHTTPサーバーモードで実行する。

`pip3 install requests` と `npx @playwright/mcp@latest` が必要です。使い方は `/playwright-step` を実行してください。

### claude-mem

claude-mem永続メモリの検索・取得プラグイン。Worker HTTP API（localhost:37777）経由で過去のセッション情報、観察、タイムラインを参照する。

claude-mem Workerが起動していることが前提です。使い方は `/claude-mem-step` を実行してください。

### devin

Devin MCP/DeepWiki経由でGitHubリポジトリ（プライベート含む）のドキュメント構造取得・内容取得・質問応答を行うプラグイン。

プライベートリポジトリへのアクセスには環境変数 `DEVIN_API_KEY` の設定が必要です（Personal API Key `apk_user_` プレフィックス）。`pip3 install requests` が必要です。使い方は `/devin-step` を実行してください。

### chrome-devtools

Chrome DevTools MCPを使ったブラウザ自動化・デバッグプラグイン。DOMスナップショット、スクリーンショット、コンソールログ、ネットワーク監視、パフォーマンス分析などをHTTPサーバーモードで実行する。

`pip3 install requests` と `npx mcp-proxy` / `npx chrome-devtools-mcp` が必要です。使い方は `/chrome-devtools-step` を実行してください。

### slack

Slack MCP経由でメッセージ検索・送信・チャンネル読み取りを行うプラグイン。OAuth PKCEでブラウザ認証し、Streamable HTTPでSlack MCPツールを実行する。

`pip3 install requests` が必要です。初回は `/slack-login-step` でログインし、その後 `/slack-action-step` でツールを実行してください。

### todoist

Todoistタスク管理プラグイン。OAuth PKCEでブラウザ認証し、Streamable HTTPでTodoist MCPツールを実行する。

`pip3 install requests` が必要です。初回は `/todoist-login` でログインし、その後 `/todoist-run` でツールを実行してください。

### atlassian

Atlassian Rovo MCP経由でJira・Confluenceを操作するプラグイン。mcp-remoteプロキシ経由でOAuth 2.1認証し、Jira・Confluenceツールを実行する。

Node.js v18+が必要です。初回は `/atlassian-login` でログインし（ブラウザが開く）、その後 `/atlassian-run` でツールを実行してください。

### drawio

draw.ioダイアグラム作成プラグイン。@drawio/mcpを使ってXML・CSV・Mermaid形式からダイアグラムを生成し、ブラウザのdraw.ioエディタで開く。

Node.js 20以上が必要です。使い方は `/drawio-create` を実行してください。

### mermaid

Mermaid.jsダイアグラム画像出力プラグイン。@mermaid-js/mermaid-cliを使ってMermaid構文からPNG/SVG画像を生成する。

Node.js 20以上が必要です。使い方は `/mermaid-render` を実行してください。

### ticktick

TickTickタスク管理プラグイン。OAuth 2.0でブラウザ認証し、TickTick Open API v1でタスク・プロジェクト操作を行う。

[developer.ticktick.com](https://developer.ticktick.com/) でアプリ登録（Redirect URI: `http://localhost:3121/callback`）が必要です。初回は `/ticktick-login` でログインし、その後 `/ticktick-run` でツールを実行してください。
