<!-- CODEX-INSTRUCTION-MINUTES-START -->
# 命令: エピソード記憶 Wiki への統合（kind: minutes 専用）

あなたはエピソード記憶の Wiki キュレーターです。本ファイルに含まれる「Raw（kind: minutes、議事録 1 件）」を、既存の Decisions Log（`{wiki_target}`）に統合してください。

## 統合先

- `{wiki_target}` (= `wiki/decisions.md`)

## 統合先の構造（既存がない場合は新規作成、ある場合は追記・更新）

```yaml
---
title: Decisions Log
status: active
updated_at: <ISO8601>
source_count: <本文の「直近の議事」セクションに列挙された件数と一致させること>
---

# Decisions Log

議事録・指示・合意の集約。`kind: minutes` の Raw を時系列・テーマ別に整理する。

## 主要な意思決定（時系列、新しい順）
- **YYYY-MM-DD HH:MM** — <決定内容の見出し> ([minutes](../raw/minutes/YYYY-MM-DD/file.md))
  - 背景: <短く>
  - 決定: <短く>
  - 関連 session: <related_session があれば session 名>
  - 参加者: <participants>

## 直近の議事（最新 50 件、新しい順）
- **YYYY-MM-DD HH:MM** — [<title>](../raw/minutes/YYYY-MM-DD/file.md)
  - 要点: <Raw 本文の冒頭から要点を1文で>

## テーマ別アクション
### <テーマ（例: アーキテクチャ、運用、リリース等）>
- **YYYY-MM-DD** — <アクション内容> ([minutes](../raw/minutes/YYYY-MM-DD/file.md))

## 未消化アクション・残課題
- <minutes の本文から「アクション」「TODO」「次回」等のキーワード周辺を抽出し、まだ完了が確認できないものを列挙>
```

## 重要: リンク形式

Decisions Log は `wiki/decisions.md` に配置されます。Raw への相対リンクは必ず `../raw/minutes/YYYY-MM-DD/file.md` 形式（1 階層上る）にすること。`../../raw/minutes/...` は誤り（projects/ 配下と混同しないこと）。

## 統合ルール

1. **既存ファイルがある場合**: 既存内容を尊重し、新しい minutes を「直近の議事」の先頭に追加。「主要な意思決定」と「テーマ別アクション」も該当があれば追記
2. **新規作成の場合**: 上記スケルトンに従い、本 1 件で初期化する
3. **意思決定の抽出**: Raw 本文の「決定」「結論」「合意」「方針」等のキーワード周辺を読み、明確な意思決定があれば「主要な意思決定」セクションに追記する。雑談ログのみで決定が無ければ追記しない
4. **アクション抽出**: 「アクション」「TODO」「次回」「やること」のキーワード周辺から未完了アクションを抽出し「未消化アクション・残課題」に追記する。完了の言及があれば、対応する既存項目を削除する
5. **直近の議事**: 新しい順に最大 50 件。超過分は削除
6. **重複排除**: 同じ Raw（同 path）が既に統合済みなら、最新版で置換する
7. **保存先**: 統合結果は `{wiki_target}` に上書き保存する。標準出力への冗長な復唱は不要

## 厳守ルール

- Raw の本文を丸ごとコピーしない。要点を抽出し、リンクで Raw を指すこと
- リンク形式は `../raw/minutes/YYYY-MM-DD/file.md` 形式（1 階層上る）厳守
- **リンク先ファイルの物理存在確認は不要。Raw の frontmatter で渡されている path 値および本指示書の相対パス形式を信頼してそのまま書け。`rg` / `find` / `ls` / `cat` 等でリンク先を探すな**（余計な exec を増やしてレイテンシ・トークンを浪費するため）
- シークレット・APIキー・個人情報・参加者の感情的表現は再掲しない
- updated_at は現在時刻を ISO8601 で記す
- **`source_count` は本文の「直近の議事」セクションに最終的に列挙される件数と必ず一致させる**（既存値の据え置き禁止、+1 の単純加算ではなく実数に合わせる）
- `{wiki_target}` 以外への書き込みは禁止

## ディレクトリ作成

`{wiki_target}` の親ディレクトリが存在しない場合、必要に応じて作成してください。

<!-- CODEX-INSTRUCTION-MINUTES-END -->

---

このファイル末尾に「既存の Decisions Log」と「統合対象の Raw（kind: minutes）」が続きます。それらを読んで `{wiki_target}` に統合結果を書き出してください。
