---
name: drawio-create
description: draw.ioダイアグラムの作成・表示を実行。XML・CSV・Mermaid形式からダイアグラムを生成し、ブラウザのdraw.ioエディタで開く。
context: fork
agent: general-purpose
---

# draw.io ダイアグラム作成手順

委任メッセージまたはユーザーの指示からダイアグラムの内容・形式を把握し、draw.ioエディタで開く。

## 前提条件

- Node.js 20以上（推奨: Node 22）
- ブラウザ（生成したダイアグラムをdraw.ioエディタで開くため）

## ワークフロー

1. **入力形式を判定**:
   - draw.io XML が指定されている → `xml` コマンド
   - CSV データ → `csv` コマンド
   - Mermaid 構文 → `mermaid` コマンド
   - テキスト説明のみ → Mermaid構文を生成してから `mermaid` コマンド
2. **コマンド実行**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py <subcommand> [options]`
3. **結果の報告**

## コマンド一覧

### ファイル出力

| コマンド | 引数 | 説明 |
|---|---|---|
| `export <content> -o <path>` | `content`: Mermaid.js構文（必須）, `-o`: 出力パス（必須、.drawio） | Mermaid → .drawioファイル |
| `export-file <file_path> -o <path>` | `file_path`: Mermaidファイル（必須）, `-o`: 出力パス（必須、.drawio） | Mermaidファイル → .drawioファイル |

### ブラウザで開く（draw.io MCP経由）

| コマンド | 引数 | 説明 |
|---|---|---|
| `xml <content>` | `content`: draw.io XML文字列（必須） | draw.io XMLをエディタで開く |
| `mermaid <content>` | `content`: Mermaid.js構文の文字列（必須） | Mermaidをdraw.ioダイアグラムに変換して開く |
| `csv <content>` | `content`: CSVデータ文字列（必須） | CSVをdraw.ioダイアグラムに変換して開く |
| `xml-file <file_path>` | `file_path`: XMLファイルパス（必須） | ファイルからXMLを読み込んでエディタで開く |
| `mermaid-file <file_path>` | `file_path`: Mermaidファイルパス（必須） | ファイルからMermaid構文を読み込んで変換して開く |
| `csv-file <file_path>` | `file_path`: CSVファイルパス（必須） | ファイルからCSVを読み込んで変換して開く |

### 共通オプション

| オプション | 説明 |
|---|---|
| `--lightbox` | 読み取り専用のlightboxモードで開く |
| `--dark auto\|true\|false` | ダークモード設定（デフォルト: `auto`） |

## 使用例

```bash
# Mermaid構文から.drawioファイルを生成
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py export "graph TD; A-->B; B-->C;" -o output.drawio

# Mermaidファイルから.drawioファイルを生成
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py export-file diagram.mmd -o output.drawio

# Mermaid構文からフローチャートを生成（ブラウザで開く）
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py mermaid "graph TD; A-->B; B-->C;"

# draw.io XMLをエディタで開く
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py xml "<mxfile>...</mxfile>"

# CSVデータからダイアグラムを生成
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py csv "## label: %name%
# style: shape=%shape%;
# connect: {\"from\": \"refs\", \"to\": \"id\"}
id,name,shape,refs
1,Start,ellipse,
2,Process,rectangle,1
3,End,ellipse,2"

# ファイルから読み込んで変換
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py mermaid-file diagram.mmd
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py xml-file diagram.drawio

# Lightboxモード（読み取り専用）で開く
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/drawio.py mermaid "graph TD; A-->B;" --lightbox

```

## 出力形式

取得した情報を以下の形式で返す:

- 実行したコマンドと入力形式
- 生成されたダイアグラムの概要
- ブラウザで開いたURL（または生成されたURLのみ）
