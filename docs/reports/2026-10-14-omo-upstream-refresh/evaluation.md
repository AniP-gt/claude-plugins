# Empirical prompt tuning

## 事前固定のシナリオと判定

対象は omo-mass-ulw 本文・planning reference、omo-ulw-execute の discovered-work 規約。description と本文の対象範囲は一致している。Ralph の iteration controller と、Workflow の明示的なユーザー要求条件を維持する。

| ID | シナリオ・判定項目 | critical |
|---|---|---|
| A1 | 1200 sources、6 batches。既知の harvest -> expand -> verify を開始前に宣言し、具体的な handoff を指定。Workflow 未承認なら Agent のみ | yes |
| A2 | bounded report、disjoint write scopes | no |
| B1 | A の report がないのに done と報告。consumer C は release しない | yes |
| B2 | 独立した B が verified なら consumer D を開始し、A 全体を待たない | no |
| B3 | coordinator が知る固定事実には新しい dependency edge を作らない | no |
| C1 | checkpoint 中の非阻害の in-scope docs 修正は後続 task、acceptance regression は現在の checkpoint 内 | yes |
| C2 | coordinator のみ task/todo 登録。Ralph count/cap/history をリセットしない | no |

Holdout D は3 slots・10 batch chains・P の old input hash・Q の current report・新しい verified leadで scope が決まる追加 task。

| ID | 未使用シナリオの判定項目 | critical |
|---|---|---|
| D1 | slot 上限は dispatch batch を制限し、既知 stage の phase graph を分割しない | yes |
| D2 | stale P は consumer を止め、current Q は検証後に release | yes |
| D3 | newly-known chain を追加し、独立した有効な証拠は保持 | no |
| D4 | producer は自身の handoff のみ、journal は coordinator 所有 | no |

## Iteration 0: baseline

新規 executor `baseline_eval` は変更前の対象を読んで A/B/C の graph・dispatch・ledger 出力を作った。全 critical を満たし100%だったが、C1 の順序は executor が補ったと報告。A1 も「既知の stage と新規の lead」の区別が明記されていなかった。tool usage metadata・総 duration は tool から取得できず、数値を捏造しない。実 retry は0。

## Iteration 1: stage と handoff、checkpoint の明文化

A1/B1/C1 の判定を満たすため、既知 stage の事前宣言、producer/consumer の絶対パス、欠落・stale artifact の release 禁止、非阻害 discovery と acceptance blocker の順序を追記した。

| Executor / Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| candidate_eval_1 / A | 成功 | 100% | metadata取得不能 | 取得不能 | 0 |
| candidate_eval_1 / B | 成功 | 100% | 同上 | 同上 | 0 |
| candidate_eval_1 / C | 成功 | 100% | 同上 | 同上 | 0 |
| candidate_eval_2 / A/B/C | 成功 | 各100% | metadata取得不能 | 取得不能 | 0 |
| candidate_eval_2 / D | 成功 | 100% | 同上 | 同上 | 0 |

candidate_eval_1 は research reference 末尾の「wave leads define next tasks」が既知 stage の事前定義と衝突し得ること、coordinator artifact check と独立した dependency review の区別を指摘。candidate_eval_2 は変更前 candidate を読み、slot 上限と whole-ready-set の表現、古い research tail に軽い曖昧さを指摘。後者の D は修正前 candidate の holdout であり、最終版の検証とは分ける。

裁量で補った値は report 上限の具体的 token 数、handoff の fixture path、slot 解放後の priority、scenario にない Ralph iteration 値。存在しない report や実行していない harvest を実証済みとは扱っていない。

## Iteration 2: stage と dependency review の整合

A1/B1 の判定に結びつけ、research 末尾も既知 chain の事前宣言に統一。required dependency review は graph に明記し、coordinator の existence/identity check だけで置換しない。独立 reviewer stage の check が consumed inputs を網羅するときは同じ証拠を二重 review しない。

最終 candidate を独立した新規 executor `final_eval_a` と `final_eval_b` で評価した。

| Executor / Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| final_eval_a / A | 成功 | 100% | metadata取得不能 | 取得不能 | 0 |
| final_eval_a / B | 成功 | 100% | 同上 | 同上 | 0 |
| final_eval_a / C | 成功 | 100% | 同上 | 同上 | 0 |
| final_eval_b / A/B/C | 成功 | 各100% | metadata取得不能 | 取得不能 | 0 |
| final_eval_b / D | 成功 | 100% | 同上 | 同上 | 0 |

両者は `H -> review-H -> E -> V` と reduction 前の shared review を graph に宣言し、missing/stale handoff を pending とした。C の順序も明記された契約で判断した。D は31以上の既知 nodesを一つの acceptance phase として登録し、3 slotsに収まる ready dispatch を行い、verified lead で決まった追加 chainだけを登録した。accuracy低下は0 points。

変更した stage/handoff/checkpoint の判断で未解決の critical はない。残る裁量は token上限の具体値、ready queueの順序、Bの既存reviewが consumed inputsを網羅するかの証拠確認。既存の Agent/Task 呼称、ulw-execute の no-QA と root verification exceptionの関係は、今回の移植対象外の観察として残した。whole-ready-set と slot 上限はplanningの具体的な容量規則を優先して両者とも正しく扱ったが、表現上の曖昧さは残る。

2人の最終 executor と holdout は全項目を満たした。ただし新規曖昧さが厳密に0かつ timing/step変動も閾値以内という形式的な収束は宣言しない。残る観察が今回のcritical判断を妨げず、他の契約へ変更を広げる費用が利益を上回るため、skill の resource cutoff で終了する。

## 評価の限界

これは新規 agent が実際に instruction を読み、具体的な simulated workflow output を作る評価。Claude Code Agent/Workflow runtime、1200件の research、製品変更を実行したという QA 記録ではない。QA-role harness が照会した live ULW state は `ULW_LOOP_PLAN_MISSING` だが、この評価は active ULW を開始しない契約なので、scenario 評価とは切り分けた。

step count ±10%・duration ±15% の形式的な収束基準は metadata が取れないため証明できない。質的な新規 ambiguity と critical 達成を判断し、残る裁量・観測限界を明示して resource cutoff を判断する。
