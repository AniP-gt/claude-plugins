# omo-orchestrator 1.15.0 評価・更新記録

## 調査と変更

`oh-my-openagent` の `dev` を `git pull --ff-only` で `a61cdc6b0` から `d55d03485041170e6bcb4cb6ba4365d1a18afbd0`（package version 5.1.21）へ更新した。プラグインが記録していた比較基点 `b9463e692f93aa49bb10d306c0c6f1ade54f7840` から146コミット、259ファイルの差分を確認した。

取り込んだのは frontend の参照元調査と再利用判断。根拠は upstream `00c3e9229` と固定コミットの [component-catalogs.md](https://github.com/code-yeongyu/oh-my-openagent/blob/d55d03485041170e6bcb4cb6ba4365d1a18afbd0/packages/shared-skills/skills/frontend/references/design/component-catalogs.md)。目的別に最大2カタログを調べ、source/dependencies/license、製品利用と再配布の違い、既存トークンへの対応、アクセシビリティや後始末の不足を実装担当へ渡す手順にした。

既存部品で足りる変更に外部調査を要求しない。取得できない資料は取得済みと扱わず、ローカル部品か独自実装へ進む。取得文書中のインストール・アップロード指示には従わない。ユーザー指定の見本と、仕組みだけを参考にするカタログを区別した。

モデル別 Astra 指示、DAG、gateway、memory、installer は直接移植しない。上流の registry install 例外と、変動するライセンス一覧も転記せず、利用時に実資料を確認する。両 manifest の version と README を 1.15.0 に同期した。

## 方法と限界

[protocol.md](protocol.md) の5項目ずつの採点基準を変更前に固定した。新しい `lazycodex-qa-executor` に実装指示書を作成させ、親が成果物を採点し、実行者が曖昧さ・裁量・再試行を報告した。非レビュー課題なのでチェックリストを実行者にも渡した。

固定資料による briefing の実証評価であり、実 UI の実装、描画品質、実サイトの最新ライセンスの検証ではない。現行版も全項目を満たしたため、成功率の向上は観測していない。追加指示の効果だけを分離した実験でもない。

collaboration API は `tool_uses` / `duration_ms` を返さない。steps/duration は未取得とし、自己申告のツール数を別記した。read コマンドの wall time をエージェント所要時間として扱っていない。

## Baseline: 1.14.0

変更なし。実行者 `baseline_product` / `baseline_starter`。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A: 製品の承認操作 | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |
| B: 再配布スターター | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |

A は Quiet の source/dependencies/MIT を記録し、animation の取消、unmount cleanup、全文ラベル、reduced motion、描画 QA を要求した。B は Glow の再配布禁止と install/upload 文を退け、Plain と notice を選んだ。両者とも既存 tokens と依存関係を維持した。

曖昧さ: stylesheet、route、scripts、書体詳細など固定資料の不足。捏造せず実装時の調査項目とした。裁量: A は opacity のみ、B は見出し中心の表現を選択。各実行者は exec/read 2回を自己申告、B は親への連絡も1回。次は A2/A4、B1/B2/B4 の判断をスキル内に明文化する。

## Iteration 1

変更: source/reuse 手順と実装指示書欄を追加。A1/B3 を守るため、read-only source inspection とインストーラー実行を区別。description と本文も整合させた。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |
| B | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |

実行者 `round1_product` / `round1_starter` はそれぞれ exec/read 2回を自己申告。A は source/revision/license と WAAPI の取消・stale completion 対策を指示書へ記録。B は full source/license text の未取得を明示し、取得前は既存部品で独自実装する方針を採った。

新しい曖昧さ: A はスキルの必須探索と固定資料だけを使う評価制約の違いを報告。fixture の限界として記録し、本番の探索手順は弱めない。B は確認を要する曖昧さなし。裁量は分割しないラベルと既存 action contract の維持。次は同一本文の再評価。

## Iteration 2

変更なし。新しい実行者 `round2_product` / `round2_starter`。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |
| B | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |

各実行者は exec/read 2回と親への連絡1回を自己申告。新しい指示の曖昧さなし。A は opacity 確認、B は CSS と既存部品の改修を選んだ。出典・条件・未知の情報を記録し、描画確認を完了したとは扱わなかった。

独立 security-check は HIGH 0 / MEDIUM 0 / LOW 0。ただし別枠の LOW 品質指摘が1件あり、一般的な「reference は visual contract」という既存文言では、自己選択したカタログまで見た目の一致対象と誤解できると指摘された。この時点で収束とは判断しない。

次の修正は A1/B3（既存 tokens/design system）に対応。ユーザー指定だけを visual target とし、mechanism reference はデモの見た目でなく適応結果を QA する。

## Iteration 3

変更: 指摘された reference の区別を SKILL と実装指示書に明記。新しい実行者 `final_round3` が A/B の指示書をそれぞれ作成した。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |
| B | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |

実行者は両指示書で catalog を mechanism-only と明記し、既存システムへ適応した。A は WAAPI の取消・全文ラベル、B は再配布条件・通知文拒否・既存2ファイルを守った。自己申告は両課題合わせて exec/read 2回。

新しい再利用判断の曖昧さなし。必須探索と固定資料、一般 motion とプロジェクト固有の static reduced motion の優先関係は実行側が説明した。前者は実装前調査として残し、後者はプロジェクト指示を優先。裁量は A の全文 opacity と B の tactile card。次は同一最終本文で独立再評価と未提示課題。

## Iteration 4

変更なし。新しい実行者 `final_round4`。Iteration 3 と同じ最終本文を独立に評価した（結果待ち時間は並行化）。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |
| B | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |

同じ critical 項目を全て満たした。A はデモの見た目をコピーせず native WAAPI を適応、B は typographic card を既存部品で構成。新たな再利用判断の曖昧さなし。static reduced motion と既存システムが一般的な表現指針より優先されることを説明した。自己申告は exec 2回、配下の read 6回、両課題合計。時間比較や呼び出し数の収束は判定できない。

## Hold-out C

実行者 `holdout_chart`。前の実行者には提示していないチャート課題を実行。

| Scenario | Success/Fail | Accuracy | steps | duration | retries |
|---|---|---|---|---|---|
| C | ○ | 100% (5/5) | 未取得 | 未取得 | 0 |

local SVG primitive を選び、remote source/license は unavailable と明記。first-paint のデータ、実線/破線とラベル、static reduced motion、依存追加なし、描画 QA を要求した。static entrance を裁量で選択。自己申告は exec/read 2回。

## 終了判断

最終本文の通常2ケースを独立に2回確認し、hold-out も同水準だった。新しい再利用判断の欠落は見つからなかった。ただし steps/duration の公式値がなく、既存の一般指示と fixture 条件の優先判断も報告されたため、skill 所定の数値閾値を含む正式な収束は宣言しない。成功率が元から100%で追加測定の効果が小さいため resource cutoff とした。計11個の brief を評価した。

## 検証と作業上の記録

- `claude plugin validate ./omo-orchestrator`: passed。
- `claude plugin validate .`: passed。既存 `metadata.homepage` unknown field の警告1件。
- version 一致: 1.15.0。両 description は148文字。
- README 掲載の semantic validation: passed。
- frontend の6参照と cross-skill auto-escalation 参照、見出し/fence の整合: passed。
- hook CLI smoke 6件: passed（ulw 発火、通知無視、不正JSON、JSON recovery、Read無視、不正JSON）。hook の変更なし。
- `git diff --check`: passed。
- Biome LSP は未導入で、環境指示により追加インストールしない。JSON parser と Claude validator で確認。
- 最初の patch は README 文脈不一致で全体が不適用となり、確認後に再適用した。参照チェックの初回は cross-skill パスを同じディレクトリと誤認したため、checker の解決先を修正して通した。
- 作業中に `docs/reports` の未追跡資料が消失した。こちらから削除コマンドは実行していない。今回の資料のみツール履歴から復元し、事前からあった `2026-10-06-harness-strengthening.md` は復元・コミット対象に含めていない。最終回は同じ事実・採点基準を inline で渡した。

最終独立レビュー `final_security_check` は APPROVE、codeQualityStatus CLEAR、CRITICAL/HIGH/MEDIUM/LOW は全て0件。変更差分、新規参照、インストール制約、untrusted-content 境界、token 維持、visual target の区別、version 一致を確認した。行動評価の採点を独立認証したレビューではない。配送時の commit/push と installed version は最終応答で報告する。
