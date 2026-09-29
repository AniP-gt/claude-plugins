---
name: query
description: LLM Wiki を根拠に質問へ答える。過去の設計判断、仕様、障害対応、用語を聞かれたときに使う。wiki に無ければ MemPalace などを検索し、良い答えは wiki に書き戻すよう提案する。「wiki で調べて」「前にどう決めた？」で使う。
---

# LLM Wiki: Query

## 1. wiki を特定する

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py resolve` で `<wiki>` を得る。失敗したら `/llm-wiki:setup` を案内する。

## 2. wiki から答える

1. `<wiki>/index.md` を読み、関連しそうなページを選ぶ。見つからなければ `<wiki>` 内を Grep する（`raw/` も対象にする）。
2. 選んだページとリンク先を読んで答える。
3. 答えには根拠のページを `<wiki>` からの相対パスで示す。推測の部分は推測と明記する。

## 3. wiki に無いとき

- MemPalace が使えるなら `mempalace_search` で検索する。コードで確認できることはリポジトリを調べる。
- wiki 以外で見つかった答えは「wiki に無かった」と明示する。そのうえで `/llm-wiki:ingest` で取り込むか提案する。

## 4. 書き戻し

調べて得た答えが今後も使えそうなら（設計判断の理由、ハマりどころ、手順など）、wiki に追記してよいかユーザーに確認する。
了承されたら、ingest skill の手順 3〜4 に従ってページ、index.md、log.md を更新する。log には `Query` と書く。
