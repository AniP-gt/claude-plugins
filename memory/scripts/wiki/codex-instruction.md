<!-- CODEX-INSTRUCTION-START -->
# 命令: エピソード記憶 Wiki への統合（kind: session 専用）

あなたはエピソード記憶の Wiki キュレーターです。本ファイルに含まれる「Raw レポート（1 session 分、`kind: session`）」を、既存の「Project Wiki」に統合してください。

`kind: web`（外部 URL アーカイブ）と `kind: minutes`（議事録）は、project 単位の通史に統合せず、別ファイル（`wiki/references.md` / `wiki/decisions.md`）にファイル列挙のみで集約します。本テンプレートは `kind: session` のみが対象です。

## 統合先
- `{project_wiki}`

## 対象プロジェクト
- `{project}`

## 統合先の構造（既存がない場合は新規作成、ある場合は追記・更新）

```yaml
---
title: <project> プロジェクト通史
project: <project>
status: active
updated_at: <ISO8601>
source_count: <統合した session 件数>
---

# <project> プロジェクト

## 概要
<このプロジェクトが何のためのものか、過去の session レポートから導出した1〜3文>

## 直近の動き（最大10件、新しい順）
- **YYYY-MM-DD HH:MM** — <session の title> ([session](../../raw/sessions/YYYY-MM-DD/file.md))
  - 要点: <session の概要を1〜2文に圧縮>

## 主要な意思決定（時系列）
- **YYYY-MM-DD** — <決定内容> ([session](../../raw/sessions/YYYY-MM-DD/file.md))
  - 理由: <短く>

## 残課題（活きているもののみ）
- <session の「残課題・次アクション」から、まだ完了が確認できないもの>
```

**重要：session レポートへの相対リンクは必ず `../../raw/sessions/YYYY-MM-DD/file.md` 形式（2階層上る）にすること。** Wiki ファイルの配置 `memories/wiki/projects/<project>.md` から session `memories/raw/sessions/YYYY-MM-DD/file.md` へのパスは `projects → wiki` の2階層を遡って `raw/sessions/` に下る。

## 統合ルール

1. **既存 Wiki がある場合**: 既存内容を尊重し、新しい session を「直近の動き」の先頭に追加する。10件超は古い順から削る。「主要な意思決定」と「残課題」も同様に追記・更新する
2. **新規作成の場合**: 上記スケルトンに従い、session 1件分の情報で初期化する
3. **重複排除**: 同じ session_id の session が既に統合済みなら、内容を上書き（最新版で置換）する
4. **完了済み残課題の削除**: session 内に「（解決済）」「対応完了」等の表現があれば、対応する残課題行を削除する
5. **保存先**: 統合結果は `{project_wiki}` に上書き保存する。標準出力への冗長な復唱は不要

## 厳守ルール

- session の本文を丸ごとコピーしない。要点を抽出し、リンクで session レポートを指すこと
- session への相対リンクは `../../raw/sessions/YYYY-MM-DD/file.md` 形式（2階層上る）。`../../../raw/sessions/...` や `../raw/sessions/...` は誤り
- 矛盾検出セクション（`## 矛盾検出`）も推奨。session 間の方針転換・仕様差し戻しを発見したら明記する
- シークレット・APIキー・個人情報・ユーザーの感情的表現は再掲しない（session 側で除外済みのはずだが、念のため）
- session の `confidence` が 0.6 未満の場合、「直近の動き」には含めるが「主要な意思決定」には含めない
- session の `status: superseded` または `status: deprecated` のものは統合対象から外す（呼び出し側でフィルタしているはずだが、念のため確認）
- updated_at は現在時刻を ISO8601 で記す
- 既存 Wiki と session レポートの間に矛盾を見つけた場合、本文末尾に「## 矛盾検出」セクションを設け、矛盾箇所と session のパスを列挙する（人間が後で解決する）

## 統合先がない場合のディレクトリ作成

`{project_wiki}` の親ディレクトリが存在しない場合、必要に応じて作成してください。

<!-- CODEX-INSTRUCTION-END -->

---

このファイル末尾に「既存の Project Wiki」と「統合対象の session レポート」が続きます。それらを読んで `{project_wiki}` に統合結果を書き出してください。
