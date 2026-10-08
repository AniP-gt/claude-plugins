---
name: lint
description: LLM Wiki を点検して直す。リンク切れ、孤立ページ、index 漏れ、frontmatter 不足、根拠コードの変更を機械的に検出し、ページ間の矛盾や古い記述を読んで確認する。「wiki を点検」「wiki lint」で使う。
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

続けて `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py check-claims` を実行する（`--wiki` は lint と同じ）。ページ内の `repo://<project>/<path>#L<a>-L<b>@<sha>` の根拠ごとに、参照したコミットから HEAD までにその行が変わったかを調べる。コードブロック（``` と ~~~）内の参照は対象外。比較先は登録したリポジトリ本体の HEAD。worktree の未マージのコミットを根拠にした参照は、本体にマージされるまでは本体の HEAD との差分で判定される（worktree だけにあるファイルは `missing` になりうる）。JSON の `issues` に次の status が返る。

| status | 意味 | 直し方 |
|---|---|---|
| `stale` | 根拠の行が変わった（`hunks` に該当する差分。バイナリファイルは `hunks` の代わりに `message`） | `git -C <repo> diff <sha> HEAD -- <path>` と今のコードを読む。事実が変わっていれば、古い記述を取り消し線と日付で残して書き直し、`claim-ref` で作り直した参照に差し替え、`verified` を今日にする。事実が変わっていなければ、参照の差し替えと `verified` の更新だけ行う |
| `missing` | ファイルが HEAD に無い | `renamed_to` があれば移動先で該当行を探し、参照を作り直す。無ければ新しい場所を探し、見つからなければ事実を取り消し線と日付で消す |
| `unknown_commit` | 参照したコミットがリポジトリに無い（rebase や未 fetch） | `git fetch` 後に再実行する。それでも無ければ今のコードで事実を確かめ、参照を作り直す |
| `unknown_project` | プロジェクト名が projects.json に無い | 名前の typo なら直す。未登録なら `/llm-wiki:setup` で登録する |
| `invalid` | パスがリポジトリの外を指す、参照したコミットにファイルが無い、行範囲がそのコミットのファイルの行数を超えるなど | 正しいパスで参照を作り直す |
| `error` | git の実行に失敗した（`message` に理由） | 理由を見て再実行する。直らなければ未解決として報告する |

`shifted` には、内容は変わっていないが前の変更で行がずれた根拠が入る。参照の行範囲を `current` に、sha を `claim-ref` で得た今の値に差し替えるだけでよい。`claim-ref` は登録リポジトリ本体で実行する（worktree で実行すると worktree の HEAD が入り、`current` と食い違うことがある）。

## 2. 内容の点検

`<wiki>/CLAUDE.md` と `index.md` を読み、ページを読んで次を探す。ページが多い場合は、最近更新されたページとその関連ページに絞る。

- ページ間で食い違う記述
- `updated` が古く、コードや最近の資料と合わなくなっていそうな記述（必要ならリポジトリで確認する）
- 1 ページに複数トピックが混ざっていて、分けたほうがよいページ
- 同じトピックの重複ページ

## 3. 報告と修正

修正が必要と判断したものは、ユーザーに確認せずにすべて直す。機械的な修正（index 追加、frontmatter 補完、リンク修正）も、内容の修正（食い違いの解消、古い記述の更新、ページの分割・統合）も同じ扱い。
内容の修正は `<wiki>/CLAUDE.md` のルールと ingest skill の「書く言語」に従い、英語で書く。古い記述は消さずに取り消し線と日付を付けて残し、統合で不要になったページは削除せず統合先へのリンクを残す。
直したら `log.md` の先頭に `## YYYY-MM-DD Lint <summary>` を英語で追記し、修正内容を種類ごとに短く報告する。
根拠が足りず正しい内容を決められないものだけは直さず、未解決として報告に含める。
