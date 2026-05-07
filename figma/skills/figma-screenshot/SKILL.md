---
name: figma-screenshot
description: Figmaデザインファイルのスクリーンショットを取得し、視覚的内容を解析する。レイアウト・色・UI要素の詳細をテキストで報告する。
context: fork
effort: low
---

# Figma スクリーンショット取得

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
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/figma_cli.py call get_screenshot --arg nodeId="<ID>"
```

利用可能なツール一覧は `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/figma_cli.py tools` で確認できる。

### 4. 画像の解析

生成・保存された画像ファイルを `Read` ツールで読み込み、視覚的内容を解析する。

解析観点:
- レイアウト構成
- 色使い
- テキスト内容
- UI要素の種類と配置
- インタラクション要素

画像の内容をテキストで詳細に記述し、呼び出し元が画像なしで実装判断できるようにする。

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
- レイアウト・色・テキスト・UI要素の視覚的解析結果

## サブエージェント

メインコンテキストの消費を抑えるため、`figma-runner` サブエージェントに委任して実行できる。

## 注意事項

- 初回利用時は `login` でOAuth認証が必要（ブラウザが開く）
- Figmaデスクトップアプリは不要（リモートMCPサーバーに接続）
