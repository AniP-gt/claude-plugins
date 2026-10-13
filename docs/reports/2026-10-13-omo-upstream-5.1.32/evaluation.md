# 1.28.0の独立した再評価

empirical-prompt-tuningに従い、既存報告を読まない2名の新しいexecutorで模擬実行した。上流との差分がないため、今回はプロンプトを修正せず、現在の資源管理・依存検証契約を再確認した。

## Iteration 0: descriptionと本文

start-workのdescriptionはkickoff、context、plan、evidence、handoffを対象とし、本文の範囲と一致する。mass-ulwは依存graphのready wave実行を対象とし、本文と一致する。資源管理の評価にはmass-ulwが継承するultrawork本文を含める。

初回dispatchでstart-workを資源管理の単独対象として指定してしまったため、両executorにultrawork本文の読み取りを追加指示した。start-work単独に資源管理の全要件があるとは結論しない。この訂正をプロンプト修正による改善として計上しない。

## 事前固定のシナリオと判定項目

各シナリオ4項目。criticalが1つでも不合格なら失敗とする。

- A: 一時HTTP serverとcacheの後片付け。[critical] 作成時にcleanup登録し証拠を永続保存、[critical] 共有cacheとopen-PR worktreeを保持、PID/port/pathのread-back、childごとのtemp/cache分離。
- B: A1→B1、A2→B2、A1+A2→C1/C2。A2のみ1回retry。[critical] A2完了前にbranch review後のB1を開始、[critical] C1/C2は共通依存reviewを待機、明示review task、独立した検証済み結果の保持。
- Hold-out C: 資源を所有するproducerが失敗し別producerは成功。[critical] 共有DB・PR worktree・永続証拠を削除しない、[critical] 検証済み独立branchは進行、所有process停止後にread-backを伴うtemp削除、失敗producerのconsumerはpending。

## 独立実行1

変更なし。Aはultrawork継承込みで4/4、Bは4/4。各criticalを満たした。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 7 file/status commands / 2 exec calls（A/B共通、executor自己申告） | 取得不能 | 実実行0 |
| B | ○ | 100% | 同上 | 取得不能 | 模擬A2修復1 |

executorはroot作成直後のcleanup登録、childの独立root、durable HTTP capture、launch identity比較、PIDとlistenerの不存在probe、exact path削除後のreceiptを示した。共有cacheとPR worktreeは理由・次のownerを伴って保持した。BはA1検証→review-A1→B1をA2完了前に開始し、A2のみretryした。共通reviewにはA1/A2の現在のinput identityと異なるiterationの由来を渡し、その完了後にC1/C2を開始した。

不明点: start-work単独ではAの資源管理要件を満たせない。QA role由来のlive loop status lookupも発生したが、評価対象skillの要求ではなかった。

裁量: 作成と登録の短い中断窓、PID identity比較方式、inspection errorと不存在の識別。新しいcritical不合格はなし。

## 独立実行2とhold-out

変更なし。別executorがA/Bを再実行し、未使用のCも評価した。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 4 file commands / 3 tool calls（全scenario共通、executor自己申告） | 取得不能 | 実実行0 |
| B | ○ | 100% | 同上 | 取得不能 | 模擬A2修復1 |
| C | ○ | 100% | 同上 | 取得不能 | 0 |

Aは各shellにtemp/cache環境を渡し、childごとにrootを分離するenvelopeを作成。PID identity一致後に停止し、process・port・pathのread-backと永続証拠の読み戻しを削除前後に配置した。Bはbranch reviewとcommon reviewをgraph nodeにし、B1をA2未完了時に開始、C1/C2はcommon review後までpendingとした。Cは失敗producerの所有processのみを停止し、共有DB・PR worktree・failure evidenceを保持。独立producerはreview後にconsumerへ進み、失敗producerのconsumerはpendingを維持した。

不明点: criticalを妨げる新規不明点なし。

裁量: PID/port/path probeの実装、登録の中断窓、ownershipの特定、抽象producerの具体的なverification command、retainedとdeletedの区別。

## 終了判断と制約

2回の独立再評価とhold-outでcritical不合格はなかった。portable本文に上流差分がなく、今回のscopeは照合と更新であるため、新しい指示を追加しない。

両実行は同じcandidateを使った独立確認であり、修正→逐次再評価の収束証明ではない。Tool usageはexecutorの自己申告で、Agent usage metadataではない。durationは取得不能であり、steps±10%・duration±15%を含む厳密な収束条件は確認できない。これは既存candidateの再確認として終了し、正式な収束達成とは報告しない。

command envelopeとledgerはすべて模擬出力。実際のserver、process、worktree削除、並列worker dispatchは実行していない。実測はmanifest validationと27件の既存テストに限定する。
