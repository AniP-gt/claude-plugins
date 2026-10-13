# omo-orchestrator 1.28.0 実行評価

## 対象と方法

`empirical-prompt-tuning`に従い、別々の新規エージェントに現行プロンプトを読ませ、具体的なTODO、依存グラフ、後片付けの判断をシミュレーションさせた。実際のClaude Codeセッションでサーバーやworktreeを作成した評価ではない。評価対象は`omo-ultrawork`と`omo-mass-ulw`のplanning reference。変更後はmass-ulw本体も読み、手順の整合を確認する。

descriptionと本文の対象は実装の継続、分解、並列実行、検証で一致しており、今回の追記もその範囲内。ユーザーのコミット・push・プラグイン更新の明示許可を優先する。

## 事前固定のシナリオと判定項目

全criticalが満点の場合だけ成功とする。Fullは1点、Partialは0.5点、Noは0点。

| ID | シナリオA: Node/Bun CLI QA、scratch、server、保存する証拠、共有cache、open PR用worktree | critical |
|---|---|---|
| A1 | scratch/cache/serverのcleanupを作成時に登録 | yes |
| A2 | runtime cacheをtaskごとに分離しchildへ環境を伝達 | no |
| A3 | 他者資源、open PR用worktree、永続的な証拠を保持 | yes |
| A4 | 後片付け後の状態を読み返して確認 | no |

| ID | シナリオB: A1/A2/A3の独立producer、A1だけを使うB1、全Aを使うC1/C2、A2の検証失敗 | critical |
|---|---|---|
| B1 | B1はbranch検証後に開始し、無関係なproducerを待たない | yes |
| B2 | 全producerが必要なconsumerは1つの共有reviewで開始を制御 | no |
| B3 | 失敗producer、影響するcheck、無効化されたconsumerだけを修復・再検証 | yes |
| B4 | 自己完結したbriefと競合しないwrite scope | no |

## Iteration 0

### Changes

変更前の1.27.0を評価。executorは指定した2ファイルを読み、実作業は行わなかった。

### Execution Results

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | 失敗 | 37.5% | 1 tool call（A/B共通） | 全実行時間は取得不能 | 0 |
| B | 成功 | 100% | 同上 | 同上 | 0（模擬A2修復は1回） |

### Unclear Points

- A: critical A1はPartial。scratch/serverのTODOは作成時に登録したが、cacheが対象として明示されていない。
- A2はNo。runtime cacheの配置、環境変数、childへの伝達規約がない。
- A4はNo。teardownの実行だけで、削除後の状態を示す証拠を要求していない。
- B: 全項目を満たしたが、ultraworkの固定wave順と依存関係に応じた早期開始との関係が曖昧。共有reviewを挟む構造も明示されていない。

### Discretion Gaps

- 証拠をscratchの外に置く判断はexecutorが補った。
- cache inventory、環境の引き継ぎ、process identity、teardown確認方法が未規定。

### Next Fix

A1/A2/A4に対してTask Resourcesを追記し、A3の証拠保全と所有権を明示する。B1/B2に対してbranch/shared reviewと依存関係による開始を明記する。既存のB3/B4の修復範囲とscope規約を維持する。

## Iteration 1

### Changes

Task Resources、worker brief、reviewのreceipt確認、branch/shared reviewを追記。

### Execution Results

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | 成功 | 100% | 2 exec calls / 5 shell invocations（A/B共通） | 全実行時間は取得不能 | 0 |
| B | 成功 | 100% | 同上 | 同上 | 0（模擬A2修復は1回） |

executorは、task/childごとのrootと環境設定、cleanupの作成時登録、PID/port/pathのread-back、永続証拠の保持を具体的なledgerとcommand envelopeにした。B1はA2/A3の完了前にbranch review後から開始し、A2失敗後も独立した結果を保持。C1/C2は共有review後まで待機した。

### Unclear Points

- 新規1件: notepadの従来の`mktemp -t`例が、先に`TMPDIR`をexportすると削除予定rootへ置かれ得る。A3は本文規約で満たしたが、作成例との整合をexecutorが補った。
- executorがローカルULW状態を照会したが、`ULW_LOOP_PLAN_MISSING`だった。評価は実際のULW workflowを起動せず、返信本文でシミュレーションを返した。これは対象プロンプトの実装検証ではない。

### Discretion Gaps

永続ディレクトリ、実際のprocess ownership、listener確認手段、evidence identityはtask環境に応じて選ぶ。シナリオの完遂を妨げるgapではなかった。

### Next Fix

A3の判定を満たすため、notepadの作成例にもrepositoryの`.claude/omo/handoffs/`を明示し、`TMPDIR`の影響を受けないよう修正。変更した文面を新規executorで再評価する。

## Iteration 2

### Changes

notepadの作成例を永続保存先へ変更。

### Execution Results

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | 成功 | 100% | 1 exec / 1 read invocation（A/B共通） | 取得不能 | 0 |
| B | 成功 | 100% | 同上 | 同上 | 0（模擬A2修復は1回） |

### Unclear Points

- 「検証済みtaskを再実行しない」が、入力変更で無効化したconsumerの再検証と字面では衝突する。
- 1つの`in_progress`と、複数のworkerが並列実行中である状態の区別が未規定。
- event-driven ready setをwaveとして扱うときのiteration計上が曖昧。
- planningのworktree isolation例に、ユーザーによるworktree要求の条件が書かれていない。
- PID再利用や他者listenerに対してはlaunch identityと所有権の確認が必要。既存のidentity/owner確認で対応し、単純なPID番号だけで削除しない。

### Discretion Gaps

executorは再実行禁止を有効な証拠に限って解釈し、worktreeはより厳しいユーザー要求の条件を適用した。全critical項目は満たしたが、判断を補わせる箇所が残った。

### Next Fix

B3/B4の意味を揃えるため、有効な証拠に限った再利用、主担当のTODOとgraph worker状態の区別、ready setのiteration計上、worktree作成条件を明示する。既に動いているworkerの予約は維持し、検証task自体を新たな実装iterationとして数えない。

### 独立したhold-out確認（Iteration 2と同じ修正前candidate）

別の新規executorがA/Bと未使用シナリオCを評価。A/Bはいずれも100%。Cは、interruption後の未知owner root、未closeのowned browser、scratch内のreport、open PRはないがhandoffで保持するworktree、A2変更で無効化されたC1、独立したA3を扱う。

| ID | 事前固定のhold-out判定項目 | critical | 結果 |
|---|---|---|---|
| C1 | 未知owner rootと承認済みhandoff worktreeを保持し、理由とownerを記録 | yes | full |
| C2 | reportを移動して読取り確認し、browser終了receiptまでcleanupをpendingにする | yes | full |
| C3 | C1と影響するreviewを再検証し、独立したA3を保持 | no | full |

Cは成功・100%。取得可能なtool数1、duration取得不能、実retry 0。既知の再実行禁止・並列TODO・worktree条件の曖昧さに加え、ultraworkの「full scenario listを再実行」と有効な証拠再利用との関係を指摘。完全なcurrent evidence setの照合を必須とし、影響した／未実行のcheckを実行する表現へ揃える。これは変更前candidateの補助評価であり、最終版の確認とは区別する。

## Iteration 3

### Changes

再利用する証拠の有効性、並列worker状態、ready-set iteration、worktree条件、full scenario setの照合を明示。

### Execution Results

同一candidateを独立した2人の新規executorで確認した。両者は改善案を知らず、指定したプロンプトとシナリオから判断した。

| Executor / Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| final-eval-a / A | 成功 | 100% | 1 exec / 1 read（A/B共通） | 取得不能 | 0 |
| final-eval-a / B | 成功 | 100% | 同上 | 同上 | 0 |
| final-eval-b / A | 成功 | 100% | 1 tool invocation（A/B/C共通） | 取得不能 | 0 |
| final-eval-b / B | 成功 | 100% | 同上 | 同上 | 0 |
| final-eval-b / C | 成功 | 100% | 同上 | 同上 | 0 |

### Unclear Points

両者とも「every renewed review dispatch」によるiteration計上が、同じrepair passでQA/re-reviewを行う規約と衝突し得ると指摘。具体的なdependency reviewとfinal gateの規約を優先して全項目を満たしたが、字面を揃える。

### Discretion Gaps

状態確認の実装は実環境に応じる。PID不在と権限エラーの区別、C2がA2変更の影響を受けるかのinput確認は必要。存在確認の失敗を不在の証拠として扱わない。C2の未確認な独立性はPASSにしない。

### Next Fix

B3の予算規約を満たすため、repair/re-review passを1予約とし、同pass内のQA/re-reviewを二重計上しない表現に変更。A4のreceiptについて、権限・tool errorはinconclusive、再利用され得るPIDはlaunch identityを確認する条件を追記。

## Iteration 4（最終candidateの独立した反復確認）

### Changes

repair/re-reviewを1予約に統一。状態確認の権限・tool errorとPID再利用をreceipt規約へ明記。

### Execution Results

| Executor / Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| final-recheck1 / A | 成功 | 100% | 1 exec / 3 reads（A/B共通） | 取得不能 | 0 |
| final-recheck1 / B | 成功 | 100% | 同上 | 同上 | 0 |
| final-recheck2 / A | 成功 | 100% | 1 read invocation（A/B/C共通） | 取得不能 | 0 |
| final-recheck2 / B | 成功 | 100% | 同上 | 同上 | 0 |
| final-recheck2 / C | 成功 | 100% | 同上 | 同上 | 0 |

### Unclear Points

両executorとも新しい実行上の曖昧さなし。所有権・process不在のplatform別probe、実際のdependency blast radiusは必要な技術判断であり、未確認な結果を成功として扱わない。

### Discretion Gaps

具体的なcommand、owner識別子、依存するinputのidentityは実taskから与える。シミュレーション上のPATH/PIDを実測の証拠に使わない。

### 確認した判断

- scratch/cache/serverは作成時にcleanup登録。task shellと独立childごとに環境を指定。
- 証拠とnotepadを永続保存。foreign cache、open PR／handoff用worktree、未知ownerのrootを保全。
- read-backがinconclusiveならcleanupをpendingに維持。PIDのlaunch identityを照合。
- A1のbranch review後にB1を先行開始。C1/C2は1つの共有reviewを通す。
- A2の変更後は影響したconsumerとreviewだけを再検証し、独立したA3の証拠を保持。
- coordinatorの1つの`in_progress`と並列workerのledger状態を区別。repair/QA/re-reviewは同じ予約を共有。

### 終了判断

最終candidateへの独立した2回の確認で全critical項目を満たし、精度改善は0、新しい実行上の曖昧さは0。hold-outも100%で、15ポイント以上の精度低下はなかった。文面の追加修正はしない。

厳密なsteps/durationの収束は以下の計測制約で確認不能。したがって数値収束を達成したとは報告せず、全criticalの安定とhold-out成功を根拠に、追加executorの費用との釣り合いからskillのresource cutoffで終了する。これは定性的な反復確認であり、Claude Codeの実runtimeを使った評価完了を意味しない。

## 計測の制約

この環境のspawn_agent結果にはTaskの`tool_uses`と`duration_ms`がない。executorが観測できたtool数だけを記録し、tool自身の所要時間をexecutor全体の時間に置き換えない。厳密なsteps/durationの収束条件を確認したとは主張しない。
