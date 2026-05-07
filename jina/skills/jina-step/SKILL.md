---
name: jina-step
description: Jina AI Remote MCP の利用手順。URLからのmarkdown抽出・Web/arXiv検索・リランクなどを実行する。
---

# Jina AI 利用手順

## 概要

Jina AI Remote MCP Server（`https://mcp.jina.ai/v1`）に Streamable HTTP で JSON-RPC を送り、
Reader（URL → markdown / スクリーンショット）、Search（Web / arXiv / SSRN / Images / Blog / BibTeX）、
Reranker、Embeddings（分類・重複除去）、PDF レイアウト抽出などのツールを呼び出す。

認証ヘッダ `Authorization: Bearer ${JINA_API_KEY}` は `~/.config/jina/secrets.env` から読み込む。
初回実行時に `templates/secrets.example.env` から自動コピーされる（既存ファイルは上書きしない）。

## 前提条件

- Python 3 が利用可能であること
- `~/.config/jina/secrets.env` の `JINA_API_KEY` を設定済みであること
  - API キーは <https://jina.ai/api-dashboard/key-manager/> から取得
  - `read_url` / `capture_screenshot_url` / `primer` 等は API キー無しでも動くが
    `search_*` / `sort_by_relevance` / `classify_text` / `extract_pdf` 等はキー必須

## 手順

### 1. URL からクリーンな markdown を抽出

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py read "https://example.com/article"
```

### 2. Web / arXiv / SSRN を検索

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py search "Claude Code MCP plugin"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py search "diffusion transformer" --source arxiv
```

### 3. ドキュメントをリランク

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py rerank "best vector DB" "pgvector" "Pinecone" "Weaviate"
```

### 4. ツール一覧と任意呼び出し

```bash
# 全ツールの schema を取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py tools

# 専用サブコマンド未対応のツールを直接呼ぶ
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jina.py call parallel_search_web --args '{"queries":["a","b"]}'
```

コマンドの詳細・オプションは `jina-reference` スキルを参照。

## サブエージェント

メインコンテキストの消費を抑えるため、`jina-runner` サブエージェントに委任して実行できる。
