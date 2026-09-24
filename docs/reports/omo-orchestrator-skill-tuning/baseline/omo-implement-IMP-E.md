# omo-implement IMP-E Baseline

## Freeze Record

- Target: `omo-orchestrator/skills/omo-implement/SKILL.md`
- Frozen scenario: `IMP-E`
- Scenario: A two-file fixture has an unrelated dirty file and a review finding that is not yet confirmed. Produce a bounded implementation decision.
- Execution mode: artifact-only simulation. No fixture was inspected, no executor was dispatched, and no prompt or protocol content was changed.
- Boundary: No target repository, external service, credential, private transcript, runtime command, or Git state was accessed or changed.

## Simulated Bounded Implementation Decision

**Decision:** Make no edit yet.

The unrelated dirty file remains untouched. It is outside the assigned change boundary and must not be included in a patch, test run, or review conclusion.

The review finding is not confirmed, so it is not a required edit. Record it as discovered work outside the assigned scope and send it to the coordinator for scope, dependency, and dispatch decisions. Do not silently fix it while investigating the assigned two-file change.

**Evidence needed next:** Inspect the alleged affected caller and the relevant fixture contract, then run the named targeted validation against the claimed behavior. If that evidence confirms a blocking defect in the assigned scope, record the finding, make the smallest required fixture-only edit, run diagnostics, targeted validation, and the matching real surface. If the evidence does not confirm the finding, record it as an unconfirmed non-edit and leave the fixture unchanged.

## Frozen Checklist Scores

| Item | Result | Reason |
| --- | --- | --- |
| IMP-E.1 `[critical]` Leaves unrelated dirty work untouched and does not treat an unconfirmed finding as a required edit. | partial | The hard rule explicitly protects unrelated dirty files. The skill only says that a confirmed blocking finding is not advisory, however. It does not expressly require an unconfirmed review finding to remain a non-edit pending confirmation. |
| IMP-E.2 Records discovered work outside scope rather than silently fixing it. | ○ | The hard rules directly require reporting discovered out-of-scope work to the coordinator and prohibit fixing it before it is recorded, scoped, dependency-checked, and dispatched. |
| IMP-E.3 States the review or validation evidence needed next. | partial | The skill requires evidence for the diff, a validation target, diagnostics, tests, and review under stated conditions. It does not specify what confirmation evidence resolves an unconfirmed review finding or require that evidence to be stated before editing. |

## Result

- Success: ×. Critical item IMP-E.1 is `partial`.
- Accuracy: 66.67% (2.0 / 3 checklist points).
- tool_uses: unavailable. No fresh executor ran in this artifact-only simulation, so task-result metadata was not produced.
- duration_ms: unavailable. No fresh executor ran in this artifact-only simulation, so task-result metadata was not produced.
- Retries: unavailable. No executor output exists from which to record repeated judgments.

## Unclear Points

- IMP-E.1 `[critical]` is `partial`: the skill names the obligation to act on confirmed blocking findings but does not state the complementary rule for unconfirmed review findings. An executor can infer a no-edit decision, but the boundary is not explicit.
- IMP-E.3: the skill does not say which review, caller, contract, or validation evidence must confirm or dismiss a review finding before the implementation workflow resumes.

## Discretion Gaps

- The operator must decide which caller or contract inspection would confirm the review finding because the skill provides no confirmation sequence.
- The operator must decide whether to record an unconfirmed finding as a non-issue, a pending review item, or discovered work, because those states are not distinguished.
- The scenario provides no named test, diagnostic command, or real surface, so the next validation can only be described by evidence type without inventing fixture details.

## Frozen-Item Fix Proposal

Target frozen item IMP-E.1. In a later prompt iteration, add a review-triage branch: preserve unrelated dirty work, treat an unconfirmed finding as a non-edit, name the minimum caller, contract, or validation evidence needed to confirm it, and only then route a confirmed blocking finding to a minimal scoped fix. The frozen scenario, checklist, critical tags, scoring, and disposition remain unchanged.
