---
name: lint
description: LLM Wiki を点検して直す。リンク切れ、孤立ページ、index 漏れ、frontmatter 不足を機械的に検出し、ページ間の矛盾や古い記述を読んで確認する。「wiki を点検」「wiki lint」で使う。
---

# LLM Wiki: Lint

## 1. 機械的な点検

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py lint` を実行する（登録外の wiki は `--wiki <path>`）。JSON で次が返る。

| キー | 意味 | 直し方 |
|---|---|---|
| `broken_links` | リンク先のページが無い | 作るべきページならページを作る。typo ならリンクを直す |
| `orphans` | どこからもリンクされていない | 関連ページか index.md からリンクする |
| `not_in_index` | index.md に載っていない | index.md の該当セクションに追加する |
| `missing_frontmatter` | frontmatter が無い | `<wiki>/CLAUDE.md` の形式で追加する |
| `missing_updated` | `updated` が無い | 分かる範囲の日付を入れる |

## 2. 内容の点検

`<wiki>/CLAUDE.md` と `index.md` を読み、ページを読んで次を探す。ページが多い場合は、最近更新されたページとその関連ページに絞る。

- ページ間で食い違う記述
- `updated` が古く、コードや最近の資料と合わなくなっていそうな記述（必要ならリポジトリで確認する）
- 1 ページに複数トピックが混ざっていて、分けたほうがよいページ
- 同じトピックの重複ページ

## 3. 報告と修正

検出結果を種類ごとに短くまとめて報告し、どこまで直すか確認する。機械的な修正（index 追加、frontmatter 補完）は確認なしで直してよい。
内容の修正は `<wiki>/CLAUDE.md` のルールに従い、`log.md` の先頭に `## YYYY-MM-DD Lint <概要>` を追記する。
