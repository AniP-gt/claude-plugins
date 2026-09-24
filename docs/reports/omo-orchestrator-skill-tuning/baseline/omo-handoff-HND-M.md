# omo-handoff HND-M Baseline

## Frozen Scenario

- Scenario: HND-M, median.
- Target: `omo-orchestrator/skills/omo-handoff/SKILL.md`.
- Requested outcome: create a disposable task ledger with immutable metadata and one kickoff phase entry.
- Evaluation mode: artifact-only simulation. No disposable fixture was materialized and no target repository, external service, credential, transcript, or Git state was accessed or changed.

## Simulated Output

The target directs the executor to create `.claude/omo/handoffs/<task-slug>.md` from the referenced handoff template before the first phase. The simulated ledger has one immutable metadata block and one appended kickoff entry. The entry contains these required fields: timestamp, task slug, phase, owner, dependency status, files or artifacts, findings or changes, validation command and result, QA evidence location, retry details, final-gate state, blockers, and next exact action.

Where the scenario supplies no command output or QA artifact, the simulated entry records `not run` and `not applicable`, as required by the target. Its next exact action is one manual, bounded operator action. The simulated content contains no secrets or private material.

## Requirements And Scoring

| Frozen checklist item | Result | Reason |
|---|---|---|
| 1. [critical] Uses the task-linked append-only ledger shape with all required phase fields. | ○ | The target fixes the ledger location, requires immutable metadata, prohibits rewriting prior entries, and lists every required phase field. Its referenced template supplies the metadata block and phase-entry shape. |
| 2. Includes inspectable validation and QA evidence locations, using explicit unavailable values where needed. | ○ | The target requires a validation command and result plus a QA evidence location. It also explicitly permits `none`, `not run`, `not applicable`, and `unknown` when a field does not apply. |
| 3. Names one exact next action without secrets or private content. | ○ | The target requires a next exact action for every entry and forbids secrets, tokens, private transcripts, and unrelated context in the ledger. |

- Checklist score: 3 / 3.
- Accuracy: 100%.
- Success: ○. Every critical checklist item is ○.

## Execution Metadata

| Measurement | Value | Reason |
|---|---|---|
| `tool_uses` | unavailable | No fresh executor result metadata exists in this artifact-only simulation. The protocol forbids estimating a missing measurement. |
| `duration_ms` | unavailable | No fresh executor result metadata exists in this artifact-only simulation. The protocol forbids estimating a missing measurement. |
| Retries | 0 | The simulated first-pass ledger construction needs no repeated judgment. This is a simulation result, not task-run metadata. |

## Unclear Points

- None that block the frozen checklist. The scenario does not provide a concrete task slug, goal, owner, timestamp, or evidence artifact, so a real executor must choose synthetic fixture values or record the target's allowed unavailable values.

## Discretion Gaps

- The target does not prescribe a kickoff phase name. An executor can choose a valid phase such as `planning`, `handoff`, or `validation` based on the fixture's intended first meaningful outcome.
- The task-specific immutable metadata is not included in the HND-M scenario text. A real fixture must provide it, or the executor must create safe synthetic values without implying real work occurred.

## Item-Linked Proposal

- Item 1: In a later, separately approved tuning iteration, consider adding one inline kickoff example that names a valid initial phase and uses explicit unavailable evidence values. It would reduce phase-selection discretion without changing the append-only contract. No prompt or protocol edit was made for this baseline.

## Baseline Disposition

The simulated baseline passes HND-M at 100% accuracy. Qualitative follow-up is limited to the two non-blocking discretion gaps above. This record is not an empirical executor run and must not be used as a substitute for fresh-executor metadata in a later iteration.
