<!-- CODEX-INSTRUCTION-MINUTES-START -->
# 命令: エピソード記憶 Wiki への統合（kind: minutes 専用、月次集約）

あなたはエピソード記憶の Wiki キュレーターです。本ファイルに含まれる「Raw（kind: minutes、議事録 1 件）」を、その月の月次集約 Wiki（`{wiki_target}` = `wiki/minutes/YYYYMM.md`）に統合してください。

## 統合先

- `{wiki_target}`（例: `wiki/minutes/202604.md` … 2026年04月分の議事録集約）

## 統合先の構造（既存がない場合は新規作成、ある場合は追記・更新）

```yaml
---
title: <YYYY>年<MM>月 議事録
month: <YYYY-MM>
status: active
updated_at: <ISO8601>
source_count: <その月に統合済みの議事録件数（後述「議事一覧」の見出し数と一致させること）>
---

# <YYYY>年<MM>月 議事録

その月に発生した議事録の集約。1 議事 1 セクションで時系列・要点・決定事項・残課題を保持する。

## 議事一覧（新しい順）

### YYYY-MM-DD — <相手・テーマ> ([raw](../../raw/minutes/YYYY-MM-DD/file.md))
- 参加者: <participants をカンマ区切りで>
- 会議種別: <meeting_type>（example: external / internal / 1on1）
- 要点:
  - <Raw 本文の主要ポイント1>
  - <主要ポイント2>
- 決定事項:
  - <明確な決定や合意があれば箇条書き。無ければ本セクション省略>
- 残課題・次アクション:
  - <未消化アクションを箇条書き>

### YYYY-MM-DD — <次の議事> ([raw](../../raw/minutes/YYYY-MM-DD/file.md))
...
```

## 重要: リンク形式

`{wiki_target}` の配置は `wiki/minutes/YYYYMM.md` です。Raw への相対リンクは必ず `../../raw/minutes/YYYY-MM-DD/<basename>.md` 形式（2 階層上る）にすること。`projects/<p>.md` の通史と同じ規約に揃えています。

**ファイル名（basename）は本ファイル末尾の Raw ブロックに出力されている `raw_basename:` の値（例: `000000_mediencer-tanpopo.md`）をそのまま使うこと**。`file.md` のような汎用語をリテラルで書いてはならない。日付（YYYY-MM-DD）も `raw_path:` の値、または Raw frontmatter の `date:` フィールドを使う。

## 統合ルール

1. **既存ファイルがある場合**: 既存の議事一覧を尊重し、本 Raw を「議事一覧」内に日付の新しい順で挿入する。同じ Raw（同 path）が既に統合済みなら最新版で置換する
2. **新規作成の場合**: 上記スケルトンに従い、本 Raw 1 件で初期化する。`title` / `month` は Raw frontmatter の `date` から `YYYY-MM` を導出する
3. **要点抽出**: Raw 本文のセクション見出し・箇条書きから主要な論点・合意・課題を 3〜6 行に圧縮する
4. **決定事項**: Raw 本文に「決定」「結論」「合意」「方針」等の明確な意思決定があれば箇条書きで記す。雑談ログのみで決定が無ければ本サブセクションを省略する
5. **残課題・次アクション**: Raw 本文の「アクション」「TODO」「次回」「やること」「次アクション候補」セクションから未消化アクションを抽出する。完了の言及があれば取り込まない
6. **保存先**: 統合結果は `{wiki_target}` に上書き保存する。標準出力への冗長な復唱は不要

## 厳守ルール

- Raw の本文を丸ごとコピーしない。要点を抽出し、リンクで Raw を指すこと
- リンク形式は `../../raw/minutes/YYYY-MM-DD/file.md` 形式（2 階層上る）厳守
- **リンク先ファイルの物理存在確認は不要。Raw の frontmatter で渡されている path 値および本指示書の相対パス形式を信頼してそのまま書け。`rg` / `find` / `ls` / `cat` 等でリンク先を探すな**（余計な exec を増やしてレイテンシ・トークンを浪費するため）
- シークレット・APIキー・個人情報・参加者の感情的表現は再掲しない
- updated_at は現在時刻を ISO8601 で記す
- **`source_count` は本文の「議事一覧」セクションに最終的に列挙される議事数（`### YYYY-MM-DD — ...` の見出し数）と必ず一致させる**（既存値の据え置き禁止、+1 の単純加算ではなく実数に合わせる）
- `{wiki_target}` 以外への書き込みは禁止

## ディレクトリ作成

`{wiki_target}` の親ディレクトリ（`wiki/minutes/`）が存在しない場合、必要に応じて作成してください。

<!-- CODEX-INSTRUCTION-MINUTES-END -->

---

このファイル末尾に「既存の月次集約 Wiki」と「統合対象の Raw（kind: minutes）」が続きます。それらを読んで `{wiki_target}` に統合結果を書き出してください。
