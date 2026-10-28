# OMO upstream refresh 2026-10-28

## 上流と取り込み判断

`/Users/tk/workspace/github.com/code-yeongyu/oh-my-openagent` の `dev` で `git pull --ff-only` が成功。開始時は1671コミット遅れていた。取得後のHEADは `79d797838381957c58035425730bdf61c3192f03`、作業ツリーはクリーン。前回取り込み点 `38d992afcec512c518973c6debac8d5221d7f0c2` から比較した。前回の接続失敗記録は履歴として残す。

変更ファイル一覧と履歴から対象を分類し、研究・frontendの本文と参照、programming・refactor・coding-agent-sessions・ulw-execute・init-deepの差分を確認した。上流全ランタイムの監査や全変更の移植を主張しない。

| 上流の変更 | 判断 |
|---|---|
| `packages/shared-skills/skills/ulw-research/` のfact ledger・report gates・edition別meaning checks | 数値・引用の追跡、互換性を確認してからの計算、最終出力と検証結果の対応、未読箇所を検証済みにしない契約を移植。read-only skillなので記録は返信内に置く |
| `packages/shared-skills/skills/frontend/SKILL.md` のrequired content・before captures・draft guard・subtract・scoped fixes | 必須項目一覧、編集前キャプチャ、架空の実績の排除、重複削減、変更範囲を限定した修正を既存skillとbriefへ移植 |
| 研究用report-tools、150ファイルの検証・計算・出力実装 | 移植しない。上流CLIやledger schemaを配布しないまま利用できるとは書かず、既存read-only所有権を維持 |
| frontendのデザインライブラリ・自動導入・ブラウザ実装 | 移植しない。既存token・依存関係・ライセンス確認・no-auto-install・QAを維持。既存の参照元アクセス制約を緩和しない |
| programmingのOXC既定化・bootstrap、Pythonキャッシュ回避、ast-grep/browser/ultimate-browsingの実装変更 | 今回のcontent移植に対応する同梱実装がないため、そのまま導入しない |
| refactor・ulw-executeの表現と実行基盤、init-deepのgeneric PR fallback | 今回の移植先で有益な契約追加は見送る。上流の自動push/PR導線で既存の公開権限境界を上書きしない |

## 教訓の配置と整合性

今回開始時にユーザーからの追加修正・レビュー教訓はなかった。上流から選んだ手順の配置先は次のとおり。新規hook・skill・agentは作らない。

- 数値・引用・最終editionの検証 → 既存skill → `omo-ultraresearch/SKILL.md`
- 必須内容を維持したUI整理 → 既存skillとその直接参照 → `omo-frontend/SKILL.md`、`references/aesthetics.md`、`references/implementer-brief.md`

descriptionと本文の範囲を照合した。researchは明示依頼のあるbounded saturation researchに限りread-only、frontendはUIとHTML/CSS/SVG成果物を扱うという既存の範囲に収まる。UI自体は実装していないため、ブラウザやスクリーンショットによる実画面検証の完了は主張しない。

## Empirical prompt tuning

独立した新規executorに読ませ、実装ではなく具体的な返信・handoffを出すシミュレーションで評価した。全実行で書込、インストール、外部操作、子agent起動を禁止。入力不足と指示の曖昧さを分けて報告させた。

固定した要件はAが4項目、Bが4項目、Cが4項目。各要件を○=1、partial=0.5、×=0として採点する。

| ケース | 固定要件（criticalを含む） |
|---|---|
| A: 約40/200人・4週と60/120受診・6か月の比較 | [critical] 約・母集団・期間と非因果性を保持、[critical] 不適切な合算なし、出所と式を提示、read-only |
| B: Markdown検証後のHTMLでmay/up toが消失、未読ペアが2つ | [critical] HTMLを検証済みにしない、[critical] 未読は完了扱いにしない、現行内容に対応した再確認handoff、read-only |
| C: premium設定画面の整理 | [critical] billing/security emailを別々に維持し実機能chip/focusを保持、架空実績と重複を除去、編集前capture、限定修正と最終必須項目照合 |

Iteration 0（変更前）: A/B/Cすべて○、各100%。ただしexecutorは、数値の留保、export後の全ペア確認、編集前capture、最終必須項目照合が本文に明記されず、チェックリストから裁量で補ったと報告した。修正はこれらの要件を既存本文へ明示するものに限定した。チェックリストを提示する通常評価なので、100%を盲検評価の精度や実アプリでの成功率と解釈しない。

測定上の制約: このdispatch surfaceはTaskの`usage.tool_uses`や`duration_ms`を返さない。executor自己申告のtool数と実行時間は参考値に留め、未計測値を推定しない。変更前executorは2 orchestration calls / 6 file commands、retry 0、合計時間未計測と報告した。

Iteration 1（変更後、新規executor）: A/B/Cすべて○、各4/4・100%、retry 0。新規の指示曖昧性は0。AでF1–F5とD1/D2を分け、約20%と50%を示し合算を拒否。Bで現在のHTMLを未検証とし、未読2件を復元して最終内容に対応した再確認をhandoff。Cで別々の入力と実機能chip/focusを残し、架空実績・重複を削除、編集前captureと最終照合をhandoffした。出所revision、未読ペアID、実画面pathなどの不足は未提供入力として区別された。3 orchestration calls、合計時間未計測。既存のvisual QAを実行したとの主張なし。

Iteration 2（本文変更なし、さらに新規executor）: A/B/Cすべて○、各4/4・100%。新規曖昧性0、retry 0。read-only tool call 2、合計時間未計測。前回の修正後、定性的には2回連続で新規曖昧性なし。

同じexecutorへ初めて提示したhold-out D: Pが「at least EUR 1.2 million revenue, FY2024, consolidated」、Qが「USD 900,000 receipts, first half FY2025, cash basis」、Sourcesに根拠なしのgrew 33%、chart captionにexact EUR 1.2 million、旧PDF approvalと変更済みHTML、という入力。固定要件は6項目（[critical] 非互換な成長率を採用しない、[critical] at leastを維持してexactを拒否、[critical] PDF検証をHTMLへ流用しない、fact種別と出所区別、Sourcesと最終内容確認、read-only）。6/6・100%。根拠のない成長率を拒否し、下限を復元し、最終HTMLと再生成PDFの各検証をhandoff。直近平均からの精度低下0ポイント。

停止判断: 精度改善0ポイントと2回連続の新規曖昧性0、hold-out成功により今回の限定された変更を出荷する。正式な停止条件のtool数±10%・所要時間±15%は必要なusage metadataがなく判定不能なので、完全な数値的収束は主張しない。参考自己申告tool数も3→2で安定条件を満たさない。ここで費用対効果によるresource cutoffとし、メトリクスを揃えるだけの追加反復は行わない。

## 検証とsecurity-check

- 変更前の `node --test omo-orchestrator/hooks/*.test.mjs omo-orchestrator/scripts/*.test.mjs`: 74件通過、失敗0。
- 変更後も同じテストを実行: 74件通過、失敗0。
- 更新後 `claude plugin validate ./omo-orchestrator --json`: success=true、manifest error/warningなし。
- 更新後 `claude plugin validate ./.claude-plugin/marketplace.json --json`: success=true。
- `git diff --check`: 通過。
- plugin/marketplaceは1.59.0で一致、descriptionはいずれも148文字。READMEにも1.59.0と上流HEADを記載。
- skill本文はresearch 131→141行、frontend 118→122行（500行未満）。直接参照はaesthetics 65→69行、brief 79→84行（100行未満）。
- directory submission向けの既存LICENSE/icon不足は変更前から同じ。通常のplugin検証の失敗ではなく、今回は公開directory申請を行わない。

独立security-check executorが `.claude/agents/security-check.md` の5カテゴリと変更差分を確認。HIGH 0 / MEDIUM 0 / LOW 0、全チェック通過。scripts/hooksには.py/.shがなく、全ファイルへ対象を広げたnpx・SQL・変数混在・資格情報・tmp検索も該当なし。runtime変更なし。新しいresearch記録は返信に限り、ソースの指示を無視する境界、インストール禁止、権限の出所を保持する規則も維持されている。

## 公開・インストール

ユーザーが今回のセッションに限りコミット・pushとplugin更新を明示許可。skillの既定の「pushしない」より今回の指示を優先する。開始時のclaude-pluginsは `main`、`74c5587` でクリーン、origin/mainと一致。無関係な変更はなかった。更新対象は既存のuser/local両scopeの `omo-orchestrator@AniP-gt`。
