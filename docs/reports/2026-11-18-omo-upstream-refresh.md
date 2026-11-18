# OMO上流更新 — 2026-11-18

## 対象と採用判断

ユーザーはpull、更新、commit、push、plugin更新を承認し、ヒアリングなしの継続を指定した。上流のdevを1754bcd63cからac2844b2aaへ進めた（348コミット）。対象mainはd8d9c37から開始し、omo-orchestrator配下に未コミット変更はなかった。SSHのpullが一度応答しなくなったため、そのプロセスを止めてpullをやり直した。

上流差分の大半はsenpiのthreadツール、リモートセッション、keychain helperの脅威モデル、ネイティブランチャー、skill-pointersの発火条件で、移植しない。スキル文言の変更のうち移植できる考え方は、ulw-planとulw-loopの改訂（上流#14083、e99bd8759bと4299f1d601）にまとまっていた。

取り込んだ考え方と移植先は次のとおり。

- waveの分け方: 2つのタスクは、一方が他方の出力を読むか、両方が同じファイル・生成物・スキーマ・ポート・ブランチ・共有状態を書く場合を除いて同じwaveに入れる。依存の辺には理由を書く → `omo-plan/SKILL.md`のDependency-Aware Waves、`agents/omo-planner.md`
- 共有の準備（install、codegen、fixture、テストサーバー）は1タスクにし、必要なタスクがそれに依存する → 同上
- 依存行列の列をTask | Writes (files, shared state) | Depends on (task: reason) | Blocks | Waveにする。上流が外した「Can parallelize with」は持っていなかった → 同上
- 時間や障害のQAはfake clockか障害の注入で行い、実際の待機や実障害を使わない → `omo-plan/SKILL.md`のPer-Task QA Contract、`agents/omo-planner.md`
- retry、timeout、lock、skip、capを足すタスクは、根拠のある原因と1つの範囲を書く。原因が分からなければ修正を止める診断タスクを置く → 同上

取り込まなかったもの: 上流ulw-planの「子エージェントの完了は通知で届く」への置き換え（plugin側はClaude CodeのAgentツールを使い、元から完了通知を前提にしている）、eval専用ツールの呼び方の注記（senpi固有）、`show_html_page`などのインラインHTMLツール名（OmO固有）。mass-ulwのplanning.mdは書込範囲の重複を禁じる規則を既に持っているため変更しない。

新規のhook、skill、agentは作っていない。スクリプトの変更はない。このセッションで受けた修正指示はなく、ルールやhookへ振り分ける教訓はなかった。

## 独立executorの結果

各回とも新しいサブエージェントに`omo-plan/SKILL.md`だけを読ませ、架空のリポジトリでタスク一覧・wave・依存行列を書かせた。`[critical]`項目がすべて○なら成功とした。

| 回 | シナリオ | 成否 | 達成率 | steps | 時間 |
|---|---|---|---|---|---|
| 1 | A CSV出力とメール送信、SMTP 421への再試行（TypeScript） | ○ | 100% | 5 | 54s |
| 1 | B 原因不明のflakyテストにretryを求められる（Python） | ○ | 100% | 7 | 61s |
| 2 | B2 原因不明のflakyテストにretryか長いsleepを求められる（Go） | ○ | 100% | 6 | 55s |
| 2 | H holdout 夜間ジョブ、advisory lock、2本のmigration（Rails） | ○ | 100% | 5 | 46s |

- 1回目: Bが「ユーザーがretryを明示的に求めた場合の扱い」と「診断タスクにも先に失敗するテストが要るか」を不明点に挙げた。どちらも正しく判断していたが、文言では決まっていなかったため、「ユーザーが求めても診断タスクを先に置く」「診断タスクは再現手順と記録する証拠を書き、失敗するテストは要らない」を加えた。
- 2回目: B2とholdoutのHで、今回の変更箇所についての新しい不明点は出なかった。残りの不明点は先に失敗するテストの判定、F1からF4の参照先、1タスク1〜3ファイルの数え方で、今回の変更とは関係しない。

収束判定は2回連続の条件に1回足りないが、2回目は変更箇所の不明点が0で、holdoutの達成率も下がらなかったため、ここで止めた。

`omo-plan/SKILL.md`は155行から157行、`agents/omo-planner.md`は59行のままで、500行の予算内に収まっている。
