# OMO Ralph Loop Hold-Out Evaluation

## Run Record

- Scenario: fresh hold-out for `omo-ralph-loop`. TodoWrite and the task ledger disagree because the ledger is stale. The latest review is `INCONCLUSIVE`, and the user asks to continue automatically.
- Target: `omo-orchestrator/skills/omo-ralph-loop/SKILL.md`.
- Protocol: `docs/reports/omo-orchestrator-skill-tuning/protocol.md`, unchanged.
- Executor: unavailable. This evaluation permitted only `Read` and `apply_patch`, so a fresh blank-slate executor could not be dispatched into a disposable fixture.
- Disposition: empirical evaluation skipped: dispatch unavailable.
- Baseline material: not read or used. This scenario is recorded separately as a hold-out.

## Checklist Scoring

No empirical checklist score is reported. The frozen protocol prohibits estimating results without a fresh executor. The observations below identify what the current prompt requires, not what an executor did.

| Hold-out checklist item | Structural observation from current skill | Empirical score | Reason |
|---|---|---|---|
| 1. [critical] Manually resumes only after reading the full ledger and reconciling its latest entry with current TodoWrite and task state. | The recovery contract requires reading the full handoff record, reconciling the latest entry with current task state, and manually taking or correcting the next exact action. | unavailable | No disposable ledger or TodoWrite state was inspected by a fresh executor. |
| 2. Corrects the stale ledger by appending a new entry rather than rewriting earlier history. | The prompt requires an append-only ledger and says to append a corrected next action on resume. | unavailable | No correction artifact was produced. |
| 3. Treats `INCONCLUSIVE` as a block on completion and records the missing evidence, blocker, retry state, and next exact action. | The loop and recovery contracts require the gate outcome and recovery fields to be appended before retrying or stopping. | unavailable | No review evidence or recovery entry was created. |
| 4. Rejects automatic continuation and states one exact manual next action. | The prompt says not to resume automatically, while the output contract requires a stop reason or next exact action. | unavailable | No executor responded to the automatic-continuation request. |

## Outcome And Metadata

- Success: unavailable. The critical item has no empirical result, so the binary success rule cannot be applied.
- Accuracy: unavailable. No checklist item received an empirical `○`, `partial`, or `×` result.
- `tool_uses`: unavailable. Do not estimate missing task metadata.
- `duration_ms`: unavailable. Do not estimate missing task metadata.
- Retries: unavailable. No executor performed or repeated a judgment.

## New Gaps

- Item 1, the `[critical]` requirement, is unscored because the required fresh executor and disposable fixture were unavailable. It is not a failed result.
- The constraints provide no synthetic TodoWrite snapshot or stale ledger entry, so append-only correction cannot be observed or assessed.
- The constraints provide no `INCONCLUSIVE` review artifact that names the missing evidence, owner, or retry state.

## Discretion Gaps

- The protocol says to reconcile against current task state. This hold-out should specify the conflicting TodoWrite item and ledger entry so the executor can show the exact correction instead of choosing the conflict details.
- The scenario should name the missing review evidence so the reported next action can be checked for precision.

## Overfitting Judgment

No overfitting decision is possible. The hold-out has not run, so it has no accuracy to compare with the recent average. It remains a valid fresh scenario and must be executed unchanged with a new blank-slate executor before it can satisfy the protocol's hold-out requirement.
