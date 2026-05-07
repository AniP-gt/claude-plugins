---
name: figma-design
description: FigmaデザインファイルからデザインコンテキストやUIコードを取得する。ノードID指定でデザイン情報・コンポーネント構造・コードを取得して結果を返す。
context: fork
effort: low
---

# Figma デザインコンテキスト取得

## 入力

$ARGUMENTS

## 手順

### 1. ログイン確認

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/figma_cli.py status
```

未認証なら `figma:login` スキルの手順に従いログインを実行。

### 2. ノードIDを特定

FigmaのURLからノードIDを抽出:
- URL: `https://www.figma.com/design/.../...?node-id=21146-88120`
- ノードID: `21146:88120`（ハイフンをコロンに変換）

### 3. コマンドを実行

```bash
# デザインコンテキスト取得
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/figma_cli.py call get_design_context --arg nodeId="<ID>"

# コード生成オプション付き
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/figma_cli.py call get_design_context --arg nodeId="<ID>" --arg forceCodeGen=true --arg dirForAssetWrites="/tmp/figma_assets"
```

利用可能なツール一覧は `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/figma_cli.py tools` で確認できる。

### 4. 出力の解析

コンポーネントツリーを階層ごとに要約し、主要な構造・スタイル・テキスト内容を抽出する。全データを羅列せず、階層構造・繰り返しパターン・主要コンポーネントを重点的に報告する。

## コマンドオプション

- `--debug` - デバッグログを有効化
- `--arg key=value` - ツール引数（複数指定可）

`--arg` の値は自動的に型変換される:
- `true` / `false` → bool
- 数値文字列 → int / float
- JSON文字列 → パース結果
- その他 → 文字列

## 出力

取得した情報を以下の形式で返す:
- 実行したコマンドと対象ノードID
- デザインコンテキストの構造・コンポーネント概要
- 生成されたコード（コード生成時）の要約と技術スタック

## サブエージェント

メインコンテキストの消費を抑えるため、`figma-runner` サブエージェントに委任して実行できる。

## 注意事項

- 初回利用時は `login` でOAuth認証が必要（ブラウザが開く）
- Figmaデスクトップアプリは不要（リモートMCPサーバーに接続）
- 生成されるReact+Tailwindコードは、プロジェクトの技術スタックに合わせて変換が必要
