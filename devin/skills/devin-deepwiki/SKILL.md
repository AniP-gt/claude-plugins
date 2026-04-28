---
name: devin-deepwiki-step
description: DeepWiki CLIでGitHubリポジトリのドキュメント構造取得・内容取得・質問応答を行う手順。
context: fork
effort: low
---

# DeepWiki CLI 利用手順

## いつ使うか

- GitHubリポジトリのドキュメント・実装を調べたいとき
- リポジトリ（公開・プライベート問わず）の内容を確認したいとき

## 手順

### 1. ドキュメント構造を確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/deepwiki_cli.py structure <owner/repo>
```

### 2. 必要に応じてドキュメント内容を取得

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/deepwiki_cli.py read <owner/repo>
```

### 3. 質問で直接回答を得る

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/deepwiki_cli.py ask <owner/repo> "質問文"
```

## 共通オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--server` | MCPサーバーURL | `https://mcp.devin.ai/mcp` |
| `--api-key` | Bearer認証用APIキー | 環境変数 `DEVIN_API_KEY` |
| `--debug` | デバッグログを出力 | off |

## 認証

`DEVIN_API_KEY` が必要。以下のいずれかで指定:

1. 環境変数 `DEVIN_API_KEY`（`.claude/settings.local.json` の `env` で設定済み）
2. `--api-key` オプション

### APIキーの種類に関する注意

**Personal API Key (`apk_user_` プレフィックス) を使用すること。**

| キー種別 | プレフィックス | `read_wiki_*` | `ask_question` |
|---|---|---|---|
| Personal API Key | `apk_user_` | OK | OK |
| Service User Credential | `cog_` | OK | 500エラー |

Service User Credential (`cog_`) はv3 Beta API専用で、`ask_question` が内部で呼ぶ `ada/query` エンドポイントがv3トークンに未対応のため500エラーになる。
