# claude-plugins

Claude Code用のカスタムプラグインリポジトリ。

## プラグイン一覧

| プラグイン | 概要 |
|---|---|
| pgvector-stack | pgvector 搭載 PostgreSQL コンテナを提供する最小プラグイン（compass / episodic の DB 基盤） |
| cocoindex-setup | ~/.config/cocoindex/ の secrets/config を所有する共通基盤（compass / episodic が fallback で参照） |
| compass | コードベースのセマンティック検索（pgvector + voyage embedding + voyage rerank、cocoindex 1.0） |
| circleci | CircleCI 調査（@circleci/mcp-server-circleci `.mcp.json` 同梱）+ ワークフロー監視（watch CLI / circleci-watch skill） |
| devin | Devin MCP（DeepWiki）`.mcp.json` 同梱 + Session API CLI でタスク委任 |
| mermaid | Mermaid 構文から PNG/SVG 画像を生成（mermaid-cli、MCP 不在） |
| episodic | Claude Code セッション・Web・議事録・プライベート日記（diary、ローカル限定）のエピソード記憶 + Wiki（人物・組織 Wiki / 名寄せ）+ cocoindex 検索（Notion URL 取込みフロー対応） |
| slack | Slack MCP（mcp.slack.com）に公式 MCP Python SDK で OAuth 2.0 PKCE 接続する CLI + skill。ワークスペース単位 token 管理 |
| omo-orchestrator | LazyCodex OMO を Claude Code 向けに移植した content-only orchestration / specialized skill / agent 集 |

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

## 設計大本線: `.mcp.json` 同梱 + deferred tools

外部 SaaS / ローカルツールへのアクセスは、可能な限り **`.mcp.json` 同梱プラグイン** として提供する。Claude Code の deferred tools 機構によって、ツール名のみが常時展開され、JSON Schema は呼び出し直前に `ToolSearch` で on-demand ロードされる。

| 方式 | 採用基準 |
|------|------|
| `.mcp.json` 同梱（stdio / http） | 公式 MCP サーバーが存在する場合の第一選択 |
| Bash + スクリプト + skill | MCP では実現できない処理（バックグラウンドポーリング、独自プロトコル、画像生成 CLI 等） |

- **`.mcp.json`**: プラグインルートに配置し、stdio または http で MCP サーバーを宣言する。OAuth は Claude Code が自動処理
- **skill**: MCP では賄えない手順（例: `circleci-watch` の REST ポーリング、`devin-session` の Session API 操作）を Bash + スクリプトで実装するときに使う
- **メインコンテキスト**: deferred tools のスキーマを必要時のみロードして MCP ツールを呼び出す

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
