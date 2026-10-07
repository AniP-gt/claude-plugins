---
name: query
description: LLM Wiki を根拠に質問へ答える。過去の設計判断、仕様、障害対応、用語を聞かれたとき、または作業中に仕様や経緯で迷ったときに使う。wiki に無ければ MemPalace などを検索し、良い答えや誤りの訂正は確認なしで wiki に書き戻す。「wiki で調べて」「前にどう決めた？」で使う。
---

# LLM Wiki: Query

## 1. wiki を特定する

`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py resolve` で `<wiki>` を得る。失敗したら `/llm-wiki:setup` を案内する。

## 2. wiki から答える

1. `<wiki>/index.md` を読み、関連しそうなページを選ぶ。見つからなければ `<wiki>` 内を Grep する（`raw/` も対象にする）。
2. 選んだページとリンク先を読んで答える。答えに使うページに `repo://` の根拠があれば、`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py check-claims --page <wiki からの相対パス>` を実行する。`stale` や `missing` の事実は、答える前にコードで確かめる。直す必要があれば手順 4 で書き戻す。
3. 答えには根拠のページを `<wiki>` からの相対パスで示す。推測の部分は推測と明記する。

## 3. wiki に無いとき

- MemPalace が使えるなら `mempalace_search` で検索する。コードで確認できることはリポジトリを調べる。
- wiki 以外で見つかった答えは「wiki に無かった」と明示する。今後も使えそうなら手順 4 で書き戻す。

## 4. 書き戻し

次の場合は、ユーザーに確認せずに wiki を更新する。

- 調べて得た答えが今後も使えそうなとき（設計判断の理由、ハマりどころ、手順など）
- wiki の記述がコードや資料と食い違っていて、修正が必要と判断したとき（コードを正とする）

ingest skill の手順 1、3〜4 に従って raw/、ページ、index.md、log.md を更新する。log には `Query` と書く。
更新したページは答えの最後に一言添えて報告する。
