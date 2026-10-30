# OMO upstream refresh 2026-10-30

## 調査範囲と採否

上流 `oh-my-openagent` の `dev` で `git pull --ff-only` を実行し、
`8c12be2b31b33aa49f8bce9822ac951fc242b073` から
`9eaaedfb24e421c29561767b143ec1ce9ae08570` に更新した。
差分676ファイルのパスを分類し、共有skillsの変更履歴、frontend / visual-qa
本文、craft-floor、design-systemテンプレート、帰属表示を確認した。
全ランタイムの実装監査はしていない。

| 上流の変更 | 採否と配置 |
|---|---|
| 見出し比率、余白、本文幅、display/tracking、ブラウザ部品 | `omo-frontend/references/quality-floor.md` に既定値と実表示からの確認手順を追加 |
| kicker、icon tile grid、nested cards、装飾mono、灰色補助文、glow | 既存 `aesthetics.md` に意味のある代案と、指定デザインの例外を追加 |
| typography roleの意味の明確化 | 既存 `design-system.md` のlabel定義と新規scale確認を更新 |
| visual-qaの測定と検出結果の扱い | 既存 `omo-visual-qa/SKILL.md` にcomputed evidenceと未検証の扱いを追加 |
| detect SDK / CLI / WebView renderer / probe injection | 専用ランタイムを必要とするため移植しない。未同梱ツールの実行や自動検出成功を要求しない |
| type等を例外なしのfloorにする規則、phoneの45文字下限 | そのまま移植しない。既存projectと明示デザインを尊重し、欧文幅をCJK・狭い画面へ強制しない |
| desktop、memory RPC、keychain、telemetry、OpenCode/Codex/Senpi固有変更 | Claude Codeのportable prompt更新の対象外 |

開始時の追加retrospective lessonはなし。今回の手順はすべて既存skillへ配置し、
新しいhook・skill・agentを作らない。権限、allowed-tools、依存取得禁止、
外部テキストをデータとして扱う境界は変更しない。由来、変更内容、Apache-2.0と
上流ライセンスの全文を `omo-frontend/ATTRIBUTION.md` と同階層へ保持した。

## Iteration 0: 変更前

descriptionと本文はUI/design-systemと手動QAの範囲で整合していた。
[evaluation.md](evaluation.md) の基準を結果を見る前に固定し、
新規の独立executorに仮想案件の実装briefを生成させた。
これはUI実表示の合格判定ではなく、指示に基づく出力の実行評価である。

| Scenario | 要件ごとの得点 | Accuracy | 成否 | Retries |
|---|---|---|---|---|
| A | 0, 1, 0.5, 0.5, 0.5, 1 | 58.3% | × | 0 |
| B | 1, 1, 1, 1 | 100% | ○ | 0 |

Aのcritical 1は×。executorはbody16 / h3 18 / h2 20 / h1 24を
「維持候補。規定上の違反ではない」と返した。critical 5はpartialで、
gray-on-blueをコントラストだけで判定し、色相を揃える代案は示さなかった。
24/8pxの見出し余白、16/8pxのgroup gap、65ch、mono制限とglow不採用は
出力されたが、executor自身はこれらを指示にない裁量の提案と報告した。
selection/caret/scrollbar等はブラウザ既定も許す方針で、tokenから定義する指示が不足。
Bでは視覚契約とnative controlsを維持しfocus/reduced motionを守った。
overlay scrollbarへの明示言及はなかったが、基準はgutter追加をしないことであり、
禁じる変更をしていないため減点しない。

自己報告はfunctions.exec 3回（内部shell 2回、時刻取得2回）、観測区間42秒。
最終応答までの総時間とツール提供のduration_ms / tool_usesは未提供。
後続の自己申告と同一尺度とみなさない。

## Iteration 1: Rendered craftの判断をbriefへ具体化

修正テーマは「新規または拡張するデザインの既定値と、その例外・測定を具体化する」。
A1〜5の不足を補い、B1〜3の既存デザインとアクセシビリティを維持する。
quality-floor 51→67行、aesthetics 69→72行、design-system 55→55行、
frontend本文124→126行、visual-qa本文115→116行。本文は500行未満、
変更した参照ファイルは100行未満、description変更なし。

新規独立executorの出力は、Aがbody16 / h3 20 / h2 25 / h1 32、
見出し余白24/16、group gap16/8、本文70ch、display最大6rem / tracking下限-0.04em。
各比率、margin collapse、実背景のコントラストを計測予定として指定した。
ブラウザ詳細のトークンとoverlay維持、不要scaffoldの代案も具体化した。
Bは8rem等の契約、native controlsを保持し、focus/reduced motionの削除を拒否した。

| Scenario | 要件ごとの得点 | Accuracy | 成否 | Retries |
|---|---|---|---|---|
| A | 1, 1, 1, 1, 1, 1 | 100% | ○ | 0 |
| B | 1, 1, 1, 1 | 100% | ○ | 0 |

自己報告のtool countはfunctions.exec 2回、内部exec_command 2回、総時間は未計測。
新しい判断上の曖昧さは「chosen directionで例外を作る範囲と承認主体」。
これをA1とB1に結び付けてIteration 2で補う。
sub-agentをtool有無で判定する既存記述と、シナリオが4ファイルだけを指定したことによる
brief参照制限も報告された。前者は今回の移植外、後者は評価ハーネスの制約であり、
以後は必要な直接参照だけの追加読込を許可する。既定値変更の成果としては数えない。

## Iteration 2: 例外の根拠

quality-floorを67→69行へ修正。未承認草案の値だけでは例外にならないこと、
選んだ方向にはbriefの目的からの理由とdesigner choiceの表示が必要なこと、
既存の明示契約には再承認を求めないことを追加した。
この1テーマ以外に指示を変更しない。

新規executorはAの「未承認草案は例外ではない」とBの「既存契約へ再承認不要」を
直接引用し、主要判断は明確と報告した。Aは16/20/25/31.25px、24/16px、
16/8px、70ch、6rem/-0.04emを提案し、将来のcomputed evidenceを分離した。
Bは8rem、-0.05em、kicker、hard shadow、monoを保持してfocus/motionだけを修正した。

| Scenario | 要件ごとの得点 | Accuracy | 成否 | Retries |
|---|---|---|---|---|
| A | 1, 1, 1, 1, 1, 1 | 100% | ○ | 0 |
| B | 1, 1, 1, 1 | 100% | ○ | 0 |
| 未知C | 1, 1, 1, 1 | 100% | ○ | 0 |

A/B自己報告のtool countはfunctions.exec 3回、内部exec_command 3回、総時間未計測。
残る解釈幅として、chosen directionの理由の十分性、本文roleの「closer」の境界、
65-75文字が全行の厳密閾値でないこと、装飾accent線と通常link underlineの境界が挙がった。
どれも今回のcritical要件違反にはならなかったが、ゼロ曖昧性とは扱わない。

未知Cの新規executorは、日本語320pxへ45文字幅を強制する案、scrollbar隠し、
focus削除をすべて拒否。native controlsとsystem paletteは保持し、存在しない
column/display/数値tableは検査のために追加せずN/Aとした。
QAへは320/375/390/1440px・両themeと、必要状態・scroll末尾・focus操作を渡し、
実画面がないため現在はINCONCLUSIVEとした。予定パスと既存証拠を混同しなかった。
自己報告はfunctions.exec 6回、内部exec_command 6回・時計3回、親への連絡1回。
観測時計差69秒、文書再読1回、同じ判断のretry 0。総完了時間ではない。

未知Cの残る指摘は、特定幅がQA既定幅を置換するか追加するか、native例外と
browser-detail定義の配置、operationalの抑制とflatness判定の関係。
今回は全幅を保持し、native例外を明記し、装飾追加は要求しないbriefを生成した。

**停止判断:** 固定要件は再評価A/B・未知Cすべて100%、過適合の15点低下なし。
ただし新規曖昧性ゼロの連続2回、tool count±10%、duration±15%という厳密な
収束条件は未達・一部未計測。完全収束とは報告しない。残る指摘は文脈依存の
デザイン判断や既存のQA／dispatch方針が中心で、今回のportをそれらの全面改修へ
広げる費用に見合わないため、skillのresource cutoffで終了する。
本評価はbrief生成のみであり、実際のUIが視覚QAを通ったという主張ではない。

## 検証

- `node --test omo-orchestrator/hooks/*.test.mjs omo-orchestrator/scripts/*.test.mjs`: 114 pass、0 fail。
- `claude plugin validate ./omo-orchestrator --json`: success=true、manifest errors/warningsなし。
- `claude plugin validate ./.claude-plugin/marketplace.json --json`: success=true。既存の `metadata.homepage` unknown-field warningあり。
- directory申請向けには既存のpluginルートLICENSE不足・icon不足の指摘が残る。今回directory申請やプラグイン全体のライセンス変更はしない。
- `git diff --check`: 通過。
- plugin/marketplaceのversionは3.2.0、description各148文字。script/hookの変更なし。
- 独立security-check: HIGH 0 / MEDIUM 0 / LOW 0。[詳細](security.md)。

## 開始状態と公開権限

ユーザーはこのセッションに限りcommit・pushとClaude plugin更新を許可した。
`empirical-prompt-tuning` の既定のpush禁止より今回の指示を優先する。
`claude-plugins` は `main` / `e7c0a75`、origin/mainより1commit先行し、
未追跡 `docs/reviews/` が存在した。既存commitは書き換えず、未追跡ファイルは
今回のcommitへ含めない。通常pushは既存commitも公開するためその旨を結果に記す。
omo-orchestratorはuser/local両scopeに3.1.1が導入済み。

## 公開・導入結果

検証と独立評価を終えてから実施し、結果を追記する。
