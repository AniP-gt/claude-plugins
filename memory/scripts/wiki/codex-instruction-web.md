<!-- CODEX-INSTRUCTION-WEB-START -->
# 命令: エピソード記憶 Wiki への統合（kind: web 専用）

あなたはエピソード記憶の Wiki キュレーターです。本ファイルに含まれる「Raw（kind: web、外部 URL アーカイブ 1 件）」を、既存の References Library（`{wiki_target}`）に統合してください。

## 統合先

- `{wiki_target}` (= `wiki/references.md`)

## 統合先の構造（既存がない場合は新規作成、ある場合は追記・更新）

```yaml
---
title: References Library
status: active
updated_at: <ISO8601>
source_count: <本文の「時系列インデックス」セクションに列挙された件数と一致させること>
---

# References Library

外部 URL のアーカイブ集。`kind: web` の Raw を時系列・テーマ別に整理する。

## テーマ別

### <テーマ名（例: AI/LLM、Webフレームワーク、設計、運用 等）>
- **YYYY-MM-DD** — [<title>](../raw/web/YYYY-MM-DD/file.md) — `<source_url>`
  - 要点: <Raw 本文の概要を1〜2文で>
  - tags: `tag1`, `tag2`

## 時系列インデックス（最新50件、新しい順）
- **YYYY-MM-DD HH:MM** — [<title>](../raw/web/YYYY-MM-DD/file.md)

## 矛盾・更新検出
（同一 source_url の旧版が存在する場合、最新版へのリンクと旧版の supersede 関係を記す）
```

## 重要: リンク形式

References Library は `wiki/references.md` に配置されます。Raw への相対リンクは必ず `../raw/web/YYYY-MM-DD/file.md` 形式（1 階層上る）にすること。`../../raw/web/...` は誤り（projects/ 配下と混同しないこと）。

## 統合ルール

1. **既存ファイルがある場合**: 既存内容を尊重し、新しい URL を「時系列インデックス」の先頭に追加。「テーマ別」では適切なテーマ節へ追記。テーマが既存に無ければ新規節を追加する
2. **新規作成の場合**: 上記スケルトンに従い、本 1 件で初期化する
3. **テーマ判定**: Raw の frontmatter `tags` と本文要点から、既存テーマと一致するか判断する。一致しなければ新規テーマを作る（粒度が細かすぎないよう注意。3 件未満のテーマは「その他」に統合してよい）
4. **重複排除**: 同じ `source_url` を持つ Raw が既に統合済みなら、最新版で置換する（旧 Raw のエントリは削除し、本 Raw のリンクに差し替え）
5. **時系列インデックス**: 新しい順に最大 50 件。超過分は削除
6. **保存先**: 統合結果は `{wiki_target}` に上書き保存する。標準出力への冗長な復唱は不要

## 厳守ルール

- Raw の本文を丸ごとコピーしない。要点を抽出し、リンクで Raw を指すこと
- リンク形式は `../raw/web/YYYY-MM-DD/file.md` 形式（1 階層上る）厳守
- **リンク先ファイルの物理存在確認は不要。Raw の frontmatter で渡されている path 値および本指示書の相対パス形式を信頼してそのまま書け。`rg` / `find` / `ls` / `cat` 等でリンク先を探すな**（余計な exec を増やしてレイテンシ・トークンを浪費するため）
- シークレット・APIキー・個人情報は再掲しない
- updated_at は現在時刻を ISO8601 で記す
- **`source_count` は本文の「時系列インデックス」セクションに最終的に列挙される件数と必ず一致させる**（既存値の据え置き禁止、+1 の単純加算ではなく実数に合わせる）
- `{wiki_target}` 以外への書き込みは禁止

## ディレクトリ作成

`{wiki_target}` の親ディレクトリが存在しない場合、必要に応じて作成してください。

<!-- CODEX-INSTRUCTION-WEB-END -->

---

このファイル末尾に「既存の References Library」と「統合対象の Raw（kind: web）」が続きます。それらを読んで `{wiki_target}` に統合結果を書き出してください。
