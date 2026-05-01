# claude-plugins

Claude Code用のカスタムプラグインリポジトリ。

## プラグイン一覧

| プラグイン | 概要 |
|---|---|
| pgvector-stack | pgvector 搭載 PostgreSQL コンテナを提供する最小プラグイン（compass / memory の DB 基盤） |
| cocoindex-setup | ~/.config/cocoindex/ の secrets/config を所有する共通基盤（compass / memory が fallback で参照） |
| compass | コードベースのセマンティック検索（pgvector + voyage embedding + voyage rerank、cocoindex 1.0） |
| context7 | ライブラリの最新ドキュメント取得（Context7 MCP） |
| rollbar | Rollbar エラートラッキングの取得・更新 |
| sentry | Sentry エラートラッキングの取得・更新 |
| circleci | CircleCI のビルド失敗調査（investigate）と目的状態到達までの監視（watch）。@circleci/mcp-server-circleci 利用 |
| figma | Figma デザイン取得・コード生成（OAuth PKCE） |
| playwright | Playwright MCP によるブラウザ自動化 |
| claude-mem | claude-mem 永続メモリの検索・取得（Worker HTTP API） |
| devin | Devin MCP 経由のリポジトリ Q&A・Session API でのタスク委任 |
| chrome-devtools | Chrome DevTools MCP 経由のブラウザ自動化・デバッグ |
| slack | Slack メッセージ検索・送信・読取（複数ワークスペース対応） |
| todoist | Todoist タスク管理（公式 MCP + OAuth 2.1） |
| atlassian | Jira・Confluence 操作（Atlassian Rovo MCP + OAuth 2.1） |
| drawio | draw.io ダイアグラム生成（XML/CSV/Mermaid → ブラウザエディタ） |
| mermaid | Mermaid 構文から PNG/SVG 画像を生成 |
| jina | Jina AI Remote MCP 経由の Web 検索・URL→Markdown・論文検索 |
| memory | Claude Code セッション・Web・議事録のエピソード記憶 + Wiki + cocoindex 検索（Notion URL 取込みフロー対応） |
| notion | Notion ページ・データベース操作（公式 MCP Python SDK + OAuth 2.1） |

詳細は `.claude-plugin/marketplace.json` および各プラグインの `README.md` / `SKILL.md` を参照。

## プラグイン新設時

- README.mdにプラグインの説明とインストールコマンドを追加すること
- `.claude-plugin/plugin.json` にバージョン情報を含めること
- `.claude-plugin/marketplace.json` の `plugins` 配列にエントリを追加すること
- 上記の「プラグイン一覧」表に1行サマリを追加すること
- スクリプトを含むプラグインは、実際にコマンドを実行して動作確認すること（サーバー起動・主要コマンドの実行など）

### description の長さ規約

`plugin.json` および `marketplace.json` の `description` は **100 文字前後（目安、最大でも 200 文字以内）** に収めること。

- 理由: CLI のプラグイン一覧表示や検索結果で視認性が下がるため。長文化すると `claude plugin validate` の見栄えも悪くなる
- 詳細仕様・変更履歴・運用注意は `README.md` / `SKILL.md` / コミットメッセージ側に書くこと
- バージョンアップで機能差分を description に追記し続ける運用は禁止（履歴は git log で追える）

## 設計大本線: code execution with MCP

このプロジェクトのツール実行における根幹方針。MCPが提供するツールは、**runnerサブエージェント経由のコード実行（code execution with MCP）** として利用する。メインコンテキストからMCPツールを直接呼び出す「MCPツール呼び出し」とは区別する。

| 方式 | 主体 | メインコンテキスト影響 | 採用 |
|------|------|----------------------|------|
| MCPツール直接呼び出し | メインコンテキスト | 大（ツール結果が流入） | ❌ 禁止 |
| code execution with MCP | runnerサブエージェント | 小（要約のみ受け取る） | ✅ 推奨 |
| Bash + スクリプト | runnerサブエージェント | 小（要約のみ受け取る） | ✅ 推奨 |

- **スキル**: MCP経由ツールの呼び出し手順・パラメータをリファレンスとして記載
- **runner**: `tools: Bash` を基本とし、スキルをプリロードしてコード実行を担う
- **メインコンテキスト**: runnerに委任し、結果の要約のみを受け取る

## 必須: `{plugin}/` 配下を変更したらバージョン更新

`{plugin}/` 配下のファイルを追加・変更・削除する作業には、以下のバージョン更新が含まれる。ファイル変更とバージョン更新は一体であり、バージョン更新なしにプラグインの変更は完了しない。

1. `{plugin}/.claude-plugin/plugin.json` の `version` を更新
2. `.claude-plugin/marketplace.json` の同プラグインの `version` を同期

バージョン判断: 機能追加→マイナー、修正→パッチ、破壊的変更→メジャー

## 必須: プラグイン作成・更新後のセキュリティチェック

プラグインの新設または `{plugin}/` 配下のスクリプト変更後、コミット前に `security-check` エージェントを実行すること。

```text
Agent(security-check): {plugin} プラグインのセキュリティチェック
```

HIGH が検出された場合はコミット前に修正すること。MEDIUM以下は検出内容を確認し、対応要否を判断すること。
