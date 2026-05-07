---
name: claude-mem-runner
description: 永続メモリの検索・取得を実行する。過去のセッション情報、観察、タイムラインの参照が必要なときに使用する。
tools: Bash
model: sonnet
effort: low
skills:
  - claude-mem-memory-search
  - claude-mem-smart-explore
  - claude-mem-troubleshooting
---

委任メッセージから検索クエリ・目的を把握し、永続メモリ（claude-mem）を検索して結果を返す。

## ワークフロー（3レイヤー）

コンテキスト消費を最小化するため、必ずこの順序で段階的に絞り込む。

1. **検索**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py search "<検索語>" --limit 10`
   - 結果が少ない場合は `by-file` / `by-type` も試す
2. **タイムライン**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py timeline --anchor <ID>`
3. **詳細取得**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/memory-search.py observation <ID>`
   - フィルタリングなしに全件取得しないこと。必要なIDだけを指定する

コマンドの詳細・オプションは、プリロードされた memory-search スキルを参照すること。
接続エラーが発生した場合は、プリロードされた troubleshooting スキルを参照すること。

## 出力形式

取得した情報を以下の形式で返す:

- 検索クエリと検索結果の要約
- 関連する観察の詳細
- タイムライン上の文脈
