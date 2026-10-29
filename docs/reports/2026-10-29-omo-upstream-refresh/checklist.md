# 固定評価契約

変更前に固定。対象は `omo-frontend/SKILL.md` と直接参照の `implementer-brief.md`。
executorは書込・インストール・外部操作・子agent・commit/pushを行わず、具体的なbrief/handoffを返信する。

## シナリオ

- A: checkout。DESIGN.mdとnested AGENTS.mdの日本語エラー要件、別々のbilling/security email。Save→Saving changes…でspinnerが挿入されfooterがずれる。
- B: 完全な新規プロジェクト。component、DESIGN.md、package.jsonなし。accessibleなminimal settingsを求められる。
- C: 既存ページの小修正。ユーザー指定の厳密なscreenshot、focusを隠すかもしれないsticky overlay、ブラウザ利用不可。

## 各シナリオ共通の4要件

1. [critical] ユーザー・デザイン制約を維持し、利用できない証拠を明記する。
2. [critical] 適用するrule/designの出所を列挙し、各制約を担当file/surfaceと具体的な事前検証計画へ対応づける。
3. idle/loading/success/disabledで寸法が変わらないcontent slotと、render後の寸法比較を具体化する。
4. 必須内容inventoryと最終QAの証拠境界を維持する。

○=1、partial=0.5、×=0。criticalすべて○のみ成功。指示に明記された内容と裁量による補完を分けて報告する。チェックリストはexecutorへ提示するため盲検精度ではない。

## Hold-out（修正後の反復に未使用）

新しい翻訳対象の招待modal。任意の長さの宛先一覧を含むがSend/Sending/Sentは同じcontrol。nested ruleは送信前preview必須。ブラウザなし、実装前。固定要件: [critical] previewと長い宛先を維持、[critical] rule→owned surface→planned proof、action stateの寸法安定をlocale/widthごとに検証し本文の自然な伸長は許容、未実施QAを完了扱いにしない。
