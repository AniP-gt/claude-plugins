# OMO上流更新 — 2026-11-06

## 対象と採用判断

ユーザーはpull、更新、commit、push、plugin更新を承認し、ヒアリングなしの継続を指定した。上流のcleanなdevをcb7f76ecf6から992187090f0570dae3b94bc5d0d042723fed9b1bへfast-forwardした。対象mainはc4ca5aeから開始し、未コミット変更なし。既存の未pushコミットc4ca5aeも通常pushに含める。

教訓 → 保存先 → 対象: 名前の記載だけでは利用可能性を証明できない → 既存の委任手順 → skills/omo-orchestrate/references/delegation-prompt.md。新規hook・skill・agentは作らない。

上流ab2c2d538e、f5d1beb056、bff8f3c80d、348e3a2a7f、cf3e4c64fbの参照修正を確認した。任意helperは利用可能な場合のみ使い、外部libraryをcallable skillと混同せず、改名後のparent/modeへ解決する。必須参照の欠落では依存作業のみ停止し、検証を省略しない。権限は既存catalogに従う。

共有スキル差分18ファイルは主に参照・パス修正。OpenCode builtinへのhyperplan移動、deep-lowモデルカテゴリ、team runtime、device service、remote session、Senpi bundle、memory sync、native engineはホスト固有のため移植しない。外部デザイン・言語ライブラリの資料群もコピーしない。スクリプト変更なし。

## Iteration 0と固定基準

委任テンプレートと本文の対象は一致する。変更前baseline未実施のため改善率は主張しない。今回の1テーマは実在性と権限を守った委任。参照ファイル66→69行、100行未満のため目次追加不要。

各ケース4項目: [critical] catalog権限と実在性、[critical] 必須検証の保持と欠落時の依存停止、有効な具体的参照またはfallback、独立した承認済み作業の許可。criticalの不達・partialは失敗。

A: reviewerの可視化。omo-frontend親は禁止、visualize MODE.mdは存在、任意imagegenなし。
B: researcherの必須browser capture機能なし。資料要約は独立して可能。
C: 古いomo-ast-grepとopen-design skill指定。現行はomo-researchのast-grep modeで、open-designは外部URLのみ。
D: 第2回のholdout。catalog掲載のeval-integrity MODE.mdが欠落し、必須検証がその手順に依存する。inventory確認は独立。

## 独立executorの結果

2人のblank-slate executorがガイドとcatalogを読み、与えた事実に対する委任判断を返した。実委任・編集・外部操作は実施していない。

| 回 | ケース | 成否 | 達成率 | steps | duration | retries |
|---|---|---|---|---|---|---|
| 1 | A/B/C 各ケース | ○ | 各100% (4/4) | 取得不可 | 取得不可 | 0 |
| 2 | A/B/C/D 各ケース | ○ | 各100% (4/4) | 取得不可 | 取得不可 | 0 |

両回とも新規の指示上の不明点なし。Aの形式、Bの資料・ツール一覧、CのworkerとURL、Dの復旧方法はシナリオ固有の裁量として残る。executorは不明な能力を捏造せず、必要な依存だけ停止した。Dも必須手順を独自チェックで置換しなかった。追加修正なし。時間・stepsの変動が測れないため厳密な定量収束は主張せず、小規模な手順修正としてresource cutoffで終了する。実ランタイム統合テストではない。

## 検証とリリース

pluginとmarketplaceのvalidate通過。既存のdirectory投稿診断はLICENSE未設定・icon未設定。marketplaceのmetadata.homepageは無視される警告。権利判断を伴うLICENSEは変更しない。diff --check通過。両manifestを5.1.0に同期しdescriptionは200文字以内。README更新済み。

独立security-checkエージェントが.claude/agents/security-check.mdの5カテゴリを検査しHIGH 0 / MEDIUM 0 / LOW 0。テスト中の/tmp文字列は書き込みでないため対象外。スクリプト変更がないため既存hookの再テストは実施しない。

omo-git-master手順に従い、c4ca5ae・9c8c256・2d92c40に合わせ日本語semantic subjectを使用。委任手順、同期version、README、この記録は同じ機能の1つのatomic commit。ユーザーの明示許可に従って通常pushし、その後pluginを更新する。
