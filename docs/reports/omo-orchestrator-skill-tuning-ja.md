# omo-orchestrator スキル調整レポート

## 概要

- 対象は `omo-orchestrator/skills` 配下の 27 スキルである。
- 凍結済みの評価契約は [protocol.md](./omo-orchestrator-skill-tuning/protocol.md) に置く。シナリオ、チェックリスト、critical 指定、採点、disposition は調整中に変更していない。
- baseline は 27 スキル x median と edge の 54 成果物である。保存先は [baseline](./omo-orchestrator-skill-tuning/baseline/) である。
- Iteration 1 は変更に直接対応する 11 rerun 成果物である。保存先は [iterations](./omo-orchestrator-skill-tuning/iterations/) である。
- holdout は 6 件で、`omo-implement` と `omo-work-with-pr` は Iteration 2 で同一 holdout を再確認した。

評価 task は fresh subagent として dispatch された。一方で複数の baseline、rerun、holdout 成果物は、自らを static または artifact-only evaluation と記録し、実際の disposable fixture と公開された task result metadata を持たない。この provenance は混在しているため、全 54 baseline と rerun が fresh な経験的 fixture 実行だったとは確立されていない。採点は prompt 契約とシナリオ記述を照合した構造的な記録として扱い、実 fixture 上の経験的実行結果とは区別する。

## Iteration 0, 構造確認と baseline

Iteration 0 では 54 件すべてを凍結プロトコルに対して記録した。対象は次の 27 スキルである。

| 区分 | スキル |
| --- | --- |
| orchestration | `omo-orchestrate`, `omo-plan`, `omo-implement`, `omo-start-work`, `omo-guardrails`, `omo-hyperplan`, `omo-ralph-loop`, `omo-handoff`, `omo-ultrawork` |
| research and review | `omo-research`, `omo-ultraresearch`, `omo-review`, `omo-review-work`, `omo-visual-qa`, `omo-security-research`, `omo-github-triage`, `omo-coding-agent-sessions` |
| delivery and maintenance | `omo-programming`, `omo-debugging`, `omo-refactor`, `omo-remove-ai-slop`, `omo-remove-deadcode`, `omo-get-unpublished-changes`, `omo-pre-publish-review`, `omo-work-with-pr`, `omo-git-master`, `omo-init-deep` |

baseline の構造採点で見つかった論点は、未確認 review finding、欠落 baseline、proportional planning、evidence matrix、risk と QA 境界、remote permission、fixture 不足時の停止条件であった。これらは prompt 契約の不足、または scenario に fixture が存在しないことを分けて記録した。構造採点の `○`、`partial`、`×` はプロトコルの計算規則を用いるが、実行済みの動作を表さない。

## Iteration 1, prompt-contract 調整と rerun

22 スキルを、baseline で見つかった凍結項目または判断文言に結び付けて変更した。変更はスキルごとに、scope、evidence、停止、manual checkpoint、出力境界を明確にする prompt-contract の調整に限った。各変更後の rerun は [iterations](./omo-orchestrator-skill-tuning/iterations/) に記録した。

| rerun | 結果の種別 | 構造的な所見 |
| --- | --- | --- |
| `UPC-E` | fresh executor と記録された artifact | 欠落 baseline では release 判断を停止し、dirty work を除外する契約を確認した。 |
| `HYP-M`, `HYP-E` | artifact-only simulation | planner への handoff と、small fix では hyperplanning を使わない条件を確認した。 |
| `IMP-E` | artifact-only simulation | un確認 finding を edit とせず、必要な確認証拠を記録する契約を確認した。 |
| `REV-M`, `RVW-M`, `URS-M`, `VQA-M` | 構造確認のみ | fixture、QA evidence、evidence packet がないため、経験的採点を行わなかった。 |
| `UWK-M` | artifact-only simulation | risk class と実 surface が fixture 不足で `partial` のままであり、prompt の欠陥とは断定しなかった。 |
| `WPR-M`, `WPR-E` | fresh executor と記録された artifact | local handoff、review premise の確認、未解決 check を readiness としない契約を確認した。 |

`tool_uses` と `duration_ms` は全 rerun で unavailable である。retries も executor metadata としては取得できず、artifact 内の `0` はシミュレーション上の再判断なしを示すだけである。

## Iteration 2, holdout 再確認

Iteration 2 では新たな一括 rerun を行わず、holdout で発見した 2 件の契約ギャップを同一シナリオで構造的に再確認した。

| スキル | 初回 holdout のギャップ | Iteration 2 の固定内容 | 結果 |
| --- | --- | --- | --- |
| `omo-implement` | required diagnostics が unavailable のとき completion を止める文言が不足していた。 | exact unverified area と理由を記録し、同等の証拠取得または blocker の明示 handoff まで completion と approval を禁じる。 | 構造採点 4/4。経験的実行ではない。 |
| `omo-work-with-pr` | unreadable required remote check を PR artifact で明示的に `INCONCLUSIVE` とする文言が不足していた。 | source、observation time、result がない remote check を `INCONCLUSIVE` とし、PR を not ready に保つ。Iteration 2 artifact は remote action の個別 permission model を記録した。最終 review 後、この model は categorical な external-operator handoff に置き換えた。 | 構造採点 4/4。経験的実行ではない。 |

2 件とも gap は prompt 契約上は閉じた。ただし blank-slate executor が fixture と実際の evidence を扱った結果ではないため、収束の 1 ラウンドとして数えない。

## Holdout

6 件の holdout はすべて凍結 registry と別に保管した。初回 6 件と 2 件の Iteration 2 再確認は [iterations](./omo-orchestrator-skill-tuning/iterations/) にある。

| スキル | 状態 | 要点 |
| --- | --- | --- |
| `omo-coding-agent-sessions` | 構造採点 100% | transcript injection を untrusted data とし、欠落 child artifact を gap とする。 |
| `omo-orchestrate` | 構造採点 100% | worker output は scope や automatic continuation の権限にならない。 |
| `omo-ralph-loop` | 未採点 | stale ledger、TodoWrite、不足 review evidence を扱う fixture がないため経験的結果なし。 |
| `omo-visual-qa` | 構造採点 100% | stale capture と live profile の不在は `INCONCLUSIVE` であり、approval しない。 |
| `omo-implement` | 75% から Iteration 2 で構造採点 100% | required diagnostics 不在時の completion boundary を明文化した。 |
| `omo-work-with-pr` | 初回は未採点、Iteration 2 で構造採点 100% | Iteration 2 は unreadable remote check と個別 permission boundary を確認した。最終 review の指摘を受け、現行 skill では remote mutation を全面的に除外し external operator へ handoff する。 |

holdout の構造採点は overfitting の経験的比較に使えない。プロトコルが要求する recent average との accuracy 比較には、同一条件の fresh executor、fixture、実測 metadata が必要である。

## 変更と維持の disposition

### 変更した 22 スキル

`omo-coding-agent-sessions`、`omo-debugging`、`omo-get-unpublished-changes`、`omo-github-triage`、`omo-guardrails`、`omo-hyperplan`、`omo-implement`、`omo-orchestrate`、`omo-plan`、`omo-pre-publish-review`、`omo-programming`、`omo-ralph-loop`、`omo-refactor`、`omo-remove-ai-slop`、`omo-review`、`omo-review-work`、`omo-security-research`、`omo-start-work`、`omo-ultraresearch`、`omo-ultrawork`、`omo-visual-qa`、`omo-work-with-pr`。

### 維持した 5 スキル

`omo-init-deep`、`omo-git-master`、`omo-handoff`、`omo-remove-deadcode`、`omo-research`。

維持は経験的な合格を意味しない。凍結項目に対して追加の prompt-contract 変更を正当化する構造的根拠がなかったため、内容を変えなかったという disposition である。

## 未解決の evidence 制限と収束判定

厳密な二回連続収束は証明されていない。理由は次のとおりである。

1. 評価 task は fresh subagent に dispatch されたが、複数の成果物は static または artifact-only evaluation を明記しており、全ケースの実 fixture 観察結果はない。
2. `tool_uses` と `duration_ms` の task result metadata は unavailable であり、プロトコル上の変動率を計算できない。
3. retries の実測 self-report も unavailable である。artifact にある `0` は実行 telemetry ではない。
4. holdout は fresh blank-slate executor と disposable fixture で実行されていないため、recent average からの 15 point 判定を行えない。

このため今回は resource cutoff を採用した。調整済み prompt-contract は出荷対象として記録するが、経験的収束の gate は開いたままである。再開時は凍結済み scenario と holdout を変えずに、fresh executor、disposable fixture、executor self-report、`tool_uses`、`duration_ms` を保存する。

## Validation

- `claude plugin validate ./omo-orchestrator`: passed。
- `claude plugin validate .`: passed。`metadata.homepage` に関する既存 warning は残るが、今回の変更による failure ではない。
- `git diff --check`: passed。
- plugin frontmatter は 27 件、凍結 protocol の対象スキルは 27 件、baseline artifact は 54 件である。
- `omo-orchestrator/.claude-plugin/plugin.json` と `.claude-plugin/marketplace.json` の version はともに `0.13.0` で一致する。
- README semantic assertions は passed。runtime file は存在しない。

## Security And Privacy

- synthetic fixture と評価成果物だけを対象とする凍結境界を維持した。
- credentials、token、private transcript、live browser profile、実サービスへの破壊的操作は対象外である。
- 初回 security review は HIGH なし、MEDIUM 2 件で `REQUEST_CHANGES` だった。
- MEDIUM 1 は GitHub、PR、review 入力に untrusted-data boundary が不足していた。issue、comment、diff、repository text、log、check artifact は証拠であり、scope、tool use、disclosure、secret access、action authorization を変更できないと明記した。
- MEDIUM 2 は pre-publish review から release dispatch、retry、publish、tag、upload、monitor が可能と読める余地だった。skill を supplied-evidence-only とし、外部 release mutation を全面的に除外した。
- 修正後の security re-review は HIGH / MEDIUM なしで `APPROVE` となった。

## Independent Review

- 初回 independent review は `REQUEST_CHANGES` だった。
- finding 1: 評価 provenance が一様な fresh empirical execution と読め、static または artifact-only と自記した成果物との不整合を十分に説明していなかった。上記の mixed provenance 記述で修正した。
- finding 2: validation と security の placeholder が残り、実行済みの確認結果と review 状態を反映していなかった。上記の actual validation、security review、pending re-review 記述で修正した。
- finding 3: README の release と PR workflow が GitHub、publish、push、merge、comment を skill 自身が実行するように読めた。content-only 境界と external operator の責任を README に明記して修正した。
- 後続 review では Iteration 2 artifact の旧 permission model と最終 categorical boundary の時系列表現も修正した。最終 independent re-review は blocking finding なしで `APPROVE` となった。

## 結論

27 スキル、54 baseline 成果物、Iteration 1 rerun、6 holdout、2 件の Iteration 2 holdout 再確認を記録した。22 スキルは prompt-contract を調整し、5 スキルは維持した。今回の成果は構造的な整合性と明示的な停止境界を強めた記録であり、経験的な収束証明ではない。
