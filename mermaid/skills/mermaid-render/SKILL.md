---
name: mermaid-render
description: Mermaid.js構文からPNG/SVG画像を生成する。@mermaid-js/mermaid-cliを使って画像出力する。
context: fork
agent: general-purpose
---

# Mermaid.js 画像出力手順

委任メッセージまたはユーザーの指示からMermaid構文を把握し、PNG/SVG画像を生成する。

## 前提条件

- Node.js 20以上（推奨: Node 22）

## ワークフロー

1. **Mermaid構文を準備**: テキスト説明のみの場合はMermaid構文を生成する
2. **コマンド実行**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mermaid.py <subcommand> [options]`
3. **結果の報告**

## コマンド一覧

| コマンド | 引数 | 説明 |
|---|---|---|
| `render <content> -o <path>` | `content`: Mermaid.js構文（必須）, `-o`: 出力パス（必須、.png/.svg） | Mermaid構文 → PNG/SVG画像 |
| `render-file <file_path> -o <path>` | `file_path`: Mermaidファイル（必須）, `-o`: 出力パス（必須、.png/.svg） | Mermaidファイル → PNG/SVG画像 |

## 使用例

```bash
# Mermaid構文からPNG画像を生成
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mermaid.py render "graph TD; A-->B; B-->C;" -o output.png

# Mermaid構文からSVG画像を生成
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mermaid.py render "graph TD; A-->B; B-->C;" -o output.svg

# Mermaidファイルから画像を生成
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/mermaid.py render-file diagram.mmd -o output.png
```

## 出力形式

取得した情報を以下の形式で返す:

- 実行したコマンドと出力形式（PNG/SVG）
- 生成された画像ファイルのパスとサイズ
