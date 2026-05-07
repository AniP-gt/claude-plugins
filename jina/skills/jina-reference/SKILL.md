---
name: jina-reference
description: Jina AI MCPのコマンド詳細・オプション・対応ツール一覧のリファレンス。
user-invocable: false
---

# Jina AI リファレンス

## 主要コマンド

| サブコマンド | 引数 | 説明 |
|---|---|---|
| `tools` | なし | 利用可能な MCP ツール一覧（schema 含む）を取得 |
| `primer` | なし | 現在のコンテキスト情報（時刻・ロケール）を取得（API キー不要） |
| `read <url>` | `url`: 対象URL | URL からクリーンな markdown を抽出（`read_url`） |
| `screenshot <url>` | `url`: 対象URL | URL のスクリーンショット取得（`capture_screenshot_url`） |
| `search <query>` | `query`: 検索クエリ, `--source/-s <web\|arxiv\|ssrn\|images\|blog\|bibtex>`（既定: `web`） | 各種ソースに対する検索 |
| `expand <query>` | `query`: クエリ | クエリ拡張・書き換え（`expand_query`） |
| `extract-pdf <url>` | `url`: PDF URL | PDF から図・表・数式を抽出（`extract_pdf`） |
| `rerank <query> <doc>...` | `query`: クエリ, `documents`: 1つ以上の文書 | 関連度でリランク（`sort_by_relevance`） |
| `classify <texts>...` | `--labels <a,b,c>`: ラベル（必須・カンマ区切り）, `texts`: 分類対象 | テキストを任意ラベルで分類（`classify_text`） |
| `dedup <texts>...` | `texts`: 重複除去対象, `--top-k <n>`（既定: 10） | 意味的にユニークな上位 K 件を取得（`deduplicate_strings`） |
| `call <tool_name>` | `tool`: ツール名, `--args <json>`: 引数 JSON | 任意の MCP ツールを直接呼ぶ |

## 対応ツール（Jina MCP 一覧）

API キー必須・任意は <https://github.com/jina-ai/MCP> 参照。専用サブコマンドが無いものは `call` で呼ぶ。

| ツール | API キー | 備考 |
|---|---|---|
| `primer` | 不要 | 専用: `jina primer` |
| `read_url` | 任意（あれば高レート） | 専用: `jina read` |
| `capture_screenshot_url` | 任意 | 専用: `jina screenshot` |
| `guess_datetime_url` | 不要 | `jina call guess_datetime_url --args '{"url":"..."}'` |
| `search_web` | 必須 | 専用: `jina search` |
| `search_arxiv` | 必須 | 専用: `jina search --source arxiv` |
| `search_ssrn` | 必須 | 専用: `jina search --source ssrn` |
| `search_images` | 必須 | 専用: `jina search --source images` |
| `search_jina_blog` | 不要 | 専用: `jina search --source blog` |
| `search_bibtex` | 不要 | 専用: `jina search --source bibtex` |
| `expand_query` | 必須 | 専用: `jina expand` |
| `parallel_read_url` | 任意 | `jina call parallel_read_url --args '{"urls":[...]}'` |
| `parallel_search_web` | 必須 | `jina call parallel_search_web --args '{"queries":[...]}'` |
| `parallel_search_arxiv` | 必須 | 同上 |
| `parallel_search_ssrn` | 必須 | 同上 |
| `sort_by_relevance` | 必須 | 専用: `jina rerank` |
| `classify_text` | 必須 | 専用: `jina classify` |
| `deduplicate_strings` | 必須 | 専用: `jina dedup` |
| `deduplicate_images` | 必須 | `jina call deduplicate_images --args '{"images":[...]}'` |
| `extract_pdf` | 必須 | 専用: `jina extract-pdf` |

## コマンドライン例

```bash
# ツール一覧（schema 確認）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py tools

# URL から markdown
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py read "https://example.com"

# Web 検索
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py search "Claude Code MCP"

# arXiv 検索
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py search "diffusion transformer" --source arxiv

# スクリーンショット
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py screenshot "https://example.com"

# クエリ拡張
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py expand "vector DB pgvector"

# リランク
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py rerank "best vector DB" "pgvector" "Pinecone" "Weaviate"

# 分類
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py classify --labels "positive,negative,neutral" "I love it" "It's bad"

# 重複除去（top-k）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py dedup "apple" "apples" "banana" "fruit" --top-k 3

# PDF 抽出
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py extract-pdf "https://arxiv.org/pdf/2406.00001"

# 任意ツール呼び出し
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py call parallel_search_web --args '{"queries":["a","b","c"]}'
```

## オプション

その他のオプションは `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py --help` を参照。

## 認証

- 認証ヘッダ: `Authorization: Bearer ${JINA_API_KEY}`
- API キー保存先: `~/.config/jina/secrets.env`（`JINA_API_KEY=...` 形式）
- 既存の環境変数 `JINA_API_KEY` が設定されていればそちらを優先する
- 初回実行時に `templates/secrets.example.env` から `~/.config/jina/secrets.env` が自動コピーされる（既存ファイルは上書きしない）

## エンドポイント

- `https://mcp.jina.ai/v1` への JSON-RPC POST（Streamable HTTP）
- `Accept: application/json, text/event-stream`
- レスポンスは JSON 形式と SSE 形式の両方をパースして JSON を返す
