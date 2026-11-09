# OMO上流更新 — 2026-11-09

## 対象と採用判断

ユーザーはpull、更新、commit、push、plugin更新を承認し、ヒアリングなしの継続を指定した。上流のdevを992187090fから4dd2565923へ進めた（1313コミット）。対象mainは5032890から開始し、未コミット変更はなかった。

上流差分の大半はSenpi、memory、device service、native engine、Web、service-authなどホスト固有の実装で、移植しない。共有スキル94ファイルのうち、ツール名の置き換え、パス修正、言語別ライブラリ（ast-grep、lsp-setup、ultimate-browsing）の更新もホスト固有か既存の内容と同じなので取り込まない。

取り込んだ考え方と移植先は次のとおり。

- review-work: 実行中のレビュアーは止まっていないので待つ。判断行なしで終わったレビュアー（判断行なしで完了、追加質問に了解のみで返答、ブロッカー報告）には一度だけ代わりのレビュアーを立てる。代わりも判断行を返さなければ、そのレーンを名指しして`INCONCLUSIVE`にする（上流`review-work/SKILL.md`）→ `skills/omo-review/modes/review-work/MODE.md`
- ulw-execute: コントローラは自分で実装していないタスクも自分で検証しない。独立した検証者がいなければタスクは`needs-human-review`のまま開いておく（上流`ulw-execute/SKILL.md`）→ `skills/omo-ultrawork/modes/ulw-execute/MODE.md`
- visualize: 集計はデータベース内で行い結果行だけを取る。日・週・月の区切りは読み手の時間帯の0時にして、時間帯を軸かキャプションに書く。集計途中の区間は暫定と示す。見出しの数値を別の情報源と照合し、一致したか、どれだけずれたかを書く（上流`data-scientist`の`SKILL.md`と`references/visualization.md`）→ `skills/omo-frontend/modes/visualize/MODE.md`
- visual-qa: ページ全体のレイアウトは`1920x1080`でも撮る。デバイスピクセル比を固定できないブラウザでは比を記録し、同じ比の参照画像とだけ比べる（上流`visual-qa`）→ `skills/omo-implement/modes/visual-qa/MODE.md`
- refactor: ベースラインにテスト結果と既存の診断・警告を含め、ベースラインになかった警告が出たら不合格とする（上流`refactor/SKILL.md`）→ `skills/omo-programming/modes/refactor/MODE.md`
- アクセント色は画面の主要アクション1つだけに使い、2番目のアクションは控えめなスタイルにする（上流`frontend/references/design/design-system-architecture.md`）→ `skills/omo-frontend/references/aesthetics.md`

取り込まなかったもの: 250行上限に伴うデバッグ時の分割例外（omoに行数上限の規則がない）、git-masterのGitHub添付アップロード手順（ブラウザセッション前提）、ulw-researchの`fact`ツール周りの規則（上流固有のスクリプト前提）、owner decisionの定義拡張（`omo-plan`の既存定義が同じ範囲を含む）。

新規のhook、skill、agentは作っていない。スクリプトの変更はない。

## 独立executorの結果

各回とも新しいサブエージェントに対象ファイルだけを読ませ、`[critical]`項目がすべて○なら成功とした。

| 回 | シナリオ | 成否 | 達成率 | steps | 時間 |
|---|---|---|---|---|---|
| 1 | A review-work（実行中→了解のみの返答） | ○ | 100% | 3 | 17s |
| 1 | B ulw-execute（検証者が起動できない） | ○ | 88% | 3 | 18s |
| 1 | C visualize（東京の日次登録数） | ○ | 100% | 3 | 32s |
| 2 | A2 review-work（実行中→BLOCKED報告） | ○ | 88% | 4 | 18s |
| 2 | D holdout refactor（新しい警告） | ○ | 100% | 1 | 14s |
| 3 | A3 review-work（証拠ファイル欠落→REQUEST_CHANGES） | ○ | 100% | 2 | 18s |

1回目のAで「smaller」の意味が不明と報告されたため、代わりのレビュアーを「同じ入力で、判断行を先に求める短い指示」と言い換えた。2回目のA2で、証拠の読めなさが原因のBLOCKEDをQA手順に戻すかどうかが不明と報告されたため、「証拠そのものが原因のブロッカーは手順3に戻し、証拠が読めるようになってから代わりを立てる」と追記した。Bの部分点（依存しない他タスクを続けてよいか）は今回の変更前からある停止条件の書き方によるもので、今回は直さない。

3回目のA3では、変更した文について新しい不明点は出なかった（残りは保存先などの裁量事項）。新規不明点ゼロの連続は1回だけで、収束条件の2回連続には届いていない。重要度と費用の釣り合いから、ここで打ち切った。
