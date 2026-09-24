# omo-ultraresearch Baseline, URS-M

## 実行種別と範囲

- 実行種別: artifact-only simulation。
- 対象: `omo-orchestrator/skills/omo-ultraresearch/SKILL.md`。
- 凍結シナリオ: URS-M。read-only の disposable evidence packet を使い、decision-critical question の claim matrix を作る。
- 実施内容: target prompt と frozen protocol のみを読んだ。disposable fixture、decision-critical question、evidence packet、fresh blank-slate executor は提供されなかった。
- 境界: prompt、protocol、fixture、外部サービス、Git、認証情報、private transcript には変更やアクセスをしていない。成果物はこの報告書のみ。
- 実証性: 本記録は empirical baseline ではない。fresh executor の出力と metadata がないため、下記は supplied input 不足下で prompt が安全に導く応答を模擬した採点である。

## 模擬した応答

### Research Brief

| Field | Value |
| --- | --- |
| Decision | `UNKNOWN`。decision-critical question が未提供。 |
| Audience and owner | `UNKNOWN`。owner と audience が未提供。 |
| Deadline or budget | `UNKNOWN`。time budget が未提供。 |
| Scope | URS-M の disposable evidence packet 内に限定する。packet 自体は未提供。 |
| Exclusions | target repository、外部サービス、credentials、private transcript、implementation、runtime continuation。 |
| Claims | C1: 未提供の decision-critical question に対する結論。priority と decision impact は question がないため `UNKNOWN`。 |
| Required lanes | Codebase、official documentation、web and independent sources、repository history、empirical checks の適用可否は packet と question がないため未判定。 |
| Browsing status | 未実施。外部アクセスは artifact-only simulation の範囲外。 |
| Evidence threshold | P0 または P1 なら primary evidence、primary がなければ independent sources 2 件。decision-changing testable claim には read-only empirical check を追加する。C1 の priority が未確定なので適用できない。 |
| Declared stop condition | question と evidence packet がない blocking gap のため即時停止する。必要な input は decision question、owner、deadline or budget、synthetic evidence packet。 |
| Expected output | C1 を `UNKNOWN` とする claim matrix と、再開に必要な exact evidence の記録。 |

### Claim And Evidence Matrix

| Claim ID | Priority | Decision impact | Status | Direct evidence | Proxy evidence | Contradiction | Unknown or gap | Source status | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | None supplied | None supplied | None supplied | No decision question or evidence packet | Unavailable | None |

### Source Matrix And Convergence

| Lane | Status | Reason | Result |
| --- | --- | --- | --- |
| Codebase | Unavailable | No disposable evidence packet | No files, symbols, callers, or tests to inspect |
| Official documentation | Not run | No question, version, or source target | No evidence collected |
| Web and independent sources | Not run | Artifact-only boundary and no research question | No evidence collected |
| Repository history | Unavailable | No disposable repository packet | No history evidence collected |
| Empirical checks | Not run | No testable claim or fixture command | No observed result |

- Lead log: no lead was admitted. A lead needs triggering evidence, a parent claim, a decision impact, an owner, and a bounded budget. None was supplied.
- Convergence or stop reason: stopped for the declared blocking gap. The evidence threshold was not met, and C1 remains `UNKNOWN`. This is a responsible stop, not a research conclusion.
- Next exact evidence: supply one decision-critical question, its owner and budget, and a synthetic disposable packet with source locations and any expected empirical command.

## Checklist Scoring

| Item | Result | Reason |
| --- | --- | --- |
| 1. [critical] Defines claim IDs, decision impact, source status, confidence, and a predeclared evidence threshold. | partial | C1 has an ID, `UNKNOWN` source status and confidence, plus a predeclared threshold. A real decision impact and priority cannot be defined without the missing question. |
| 2. Separates direct evidence, proxy evidence, contradictions, and unknowns. | ○ | The matrix gives each evidence category its own field and records the only supported result, an `UNKNOWN` caused by unavailable input. It makes no unsupported claim. |
| 3. Stops when the threshold or declared convergence condition is met. | ○ | The simulation declares and follows the prompt's blocking-gap stop condition. It does not claim that the evidence threshold was met. |

- Score calculation: `(0.5 + 1 + 1) / 3 = 83.3%`。
- Success: `×`。The sole `[critical]` item is `partial`; frozen scoring permits success only when every critical item is `○`。

## Executor Metadata And Retries

| Field | Value | Reason |
| --- | --- | --- |
| `tool_uses` | unavailable | No fresh executor task result metadata exists. The protocol forbids estimating it. |
| `duration_ms` | unavailable | No fresh executor task result metadata exists. The protocol forbids estimating it. |
| Retries | 0 | The simulation made no repeated judgment. No executor retry record exists. |

## New Unclear Points

- Failed [critical] item 1: URS-M does not state the decision-critical question, owner, deadline or time budget, or disposable evidence packet contents. The prompt requires these inputs before it can define an actual claim priority and decision impact.
- The scenario says to produce a claim matrix but does not identify the expected artifact format or location within the disposable fixture. The target prompt permits research output or a journal, so a real executor must choose between them.

## New Discretion Gaps

- The prompt says to create or ask a writable owner to create an append-only journal when work crosses contexts or needs an audit trail. It does not give an artifact-only executor a decision rule for when a single fixture research task qualifies.
- The prompt requires a source matrix before dispatch, but no minimum source-matrix form is supplied for a case where every lane is unavailable at brief time.

## Item-Linked Proposal

- Item 1: Add a compact, fill-in-ready research brief and claim-matrix template that explicitly requires `decision impact`, `priority`, `source status`, `confidence`, and `evidence threshold`. Include an unavailable-input example that stops with `UNKNOWN` rather than inventing those fields.

## Baseline Disposition

- `empirical evaluation skipped: dispatch unavailable`。
- This artifact records a simulated failure signal only. It must not be compared with empirical accuracy, tool use, duration, retry, convergence, or hold-out results.
