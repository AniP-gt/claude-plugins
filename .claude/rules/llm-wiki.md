---
paths:
  - "llm-wiki/**"
---

# llm-wiki プラグインは英語で書く

`llm-wiki/` 配下のファイル（SKILL.md、スクリプトのコメント・docstring・CLI メッセージ・help・プロンプト、hooks.json、テンプレート）は、追加も修正もすべて英語で書く。`llm-wiki/.claude-plugin/plugin.json` の `description` と、`.claude-plugin/marketplace.json` の llm-wiki エントリの `description` も英語にする。

- 例外: 日本語を例として示す箇所（`CLAUDE.md.template` の `prescription refill (処方箋の再調剤)` など）と、日本語の入力を処理するための正規表現や文字列。
- ルート `README.md` の llm-wiki 節はリポジトリ全体の日本語ドキュメントの一部なので対象外。
- コミットメッセージは従来どおり日本語でよい。
