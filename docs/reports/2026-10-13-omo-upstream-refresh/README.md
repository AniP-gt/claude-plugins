# omo upstream refresh: 1.28.0

## 照合した上流

- ローカル`oh-my-openagent`の`dev`を`git pull --ff-only`で更新。
- 前回照合: `5943705430de7879690923a61b6ca5b94d282783`（5.1.27）。
- 今回照合: `7b44ad22b02d2f3f55769406c553210ed42157df`（package version 5.1.30）。
- `packages/prompts-core`、`packages/shared-skills`、`packages/skills-loader-core/src/features/builtin-skills`、`packages/omo-senpi/skills`、Codex bundled rulesの変更を確認。

## 取り込んだ判断基準

| 上流 | Claude Codeへの適用 |
|---|---|
| `57e07dfc5`、`c76ac2636`、`0a2470320`: taskの一時領域、runtime cache、作成時のcleanup登録 | ultraworkのTask Resourcesへ移植。別shellへの環境再設定、childごとのroot、read-back receipt、永続証拠の保存を明示。ulw-executeのworker briefとreview-workの検証にも接続 |
| `76e8d432a`: wave間の全結合を1つのreview nodeへ集約 | mass-ulwの手動task graphへ移植。部分依存はbranch review後に開始し、無関係なproducerの失敗で待たせない。影響する結果だけを再検証。評価で見つかった既存規約との衝突を解消し、主担当TODOとworker状態、ready setのiteration計上、最終scenario全件の証拠照合を明記 |

上流の自動worktree作成・mergeは導入しない。既存の「ユーザーが要求したときだけworktreeを使う」規約を維持し、open PR、別task、handoffで必要なworktreeと共有cacheを保全する。成果物やnotepadを一時領域ごと消さない。

## 今回取り込まない変更

- Browser/ultimate-browsingの特定engine、remote browser、tab API、読み取り全件のブラウザー必須化。Claude版は特定のbrowser runtimeを同梱せず、source provenance、proxyの裏付け、アクセス不能の記録を既に規定する。
- onboarding、provider/model variant、Senpi task/thread/gateway、installer、desktop、memory、runtime cache削除の実装。Claude Codeの可視プロンプト契約への移植対象外。
- research/visual QA scriptのテストfixture変更。対応する実行runtimeをClaude版に導入していない。

## 検証

- `claude plugin validate ./omo-orchestrator`: 成功。
- `claude plugin validate .`: 成功。既存の`metadata.homepage` unknown-field警告1件。変更前のmanifestにも存在することを確認。
- READMEの既存semantic validation: 成功。これは静的な文書確認であり、実行評価の代替にはしない。
- `node --test omo-orchestrator/hooks/pasted.test.mjs omo-orchestrator/hooks/review-gate.test.mjs omo-orchestrator/scripts/impact.test.mjs`: exit 0。
- plugin/marketplaceのversionは1.28.0で一致。両descriptionは148文字で、200文字以内。
- `git diff --check`: 成功。
- プロンプトのblank-slate実行評価は[evaluation.md](evaluation.md)を参照。
- repositoryの`security-check`定義によるread-only review: HIGH 0 / MEDIUM 0 / LOW 0。共有・他者資源の削除、証拠の消失、秘密情報、実行許可の拡張について具体的な導入問題なし。script変更を条件とする必須triggerには該当しないが、今回はreviewを実施。
- notepad作成例と評価文書の追加deltaもsecurity-checkで再確認し、HIGH 0 / MEDIUM 0 / LOW 0。

スクリプト・hookの変更はない。実際のClaude Codeでの長時間の並列実装やサーバー後片付けは未評価であり、シミュレーション結果を実測として扱わない。
