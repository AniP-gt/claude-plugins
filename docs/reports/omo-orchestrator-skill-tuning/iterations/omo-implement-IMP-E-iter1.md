# omo-implement IMP-E Iteration 1

## Freeze Record

- Target: `omo-orchestrator/skills/omo-implement/SKILL.md`
- Frozen scenario: `IMP-E`
- Scenario: A two-file fixture has an unrelated dirty file and a review finding that is not yet confirmed. Produce a bounded implementation decision.
- Execution mode: artifact-only simulation. No fixture was inspected, no executor was dispatched, and no prompt or protocol content was changed.
- Boundary: No target repository, external service, credential, private transcript, runtime command, or Git state was accessed or changed.

## Simulated Bounded Implementation Decision

**Decision:** Make no edit until the review finding is confirmed.

Keep the unrelated dirty file outside the change boundary and do not modify it. Record its pre-existing status or diff evidence as required by step 5.

Record the review finding as unconfirmed. Verify it against the affected caller, current code, tests, or stated contract. Until that evidence confirms a blocking finding, do not treat it as a required edit. If it is confirmed and in scope, make only the minimal follow-up edit. If it is not confirmed, record it as unconfirmed and leave the fixture unchanged.

**Evidence needed next:** The relevant caller or contract evidence, plus the targeted validation that exercises the claimed behavior. The outcome must show whether the finding is a confirmed blocker, an unconfirmed non-edit, or discovered work that needs coordinator routing.

## Frozen Checklist Scores

| Item | Result | Reason |
| --- | --- | --- |
| IMP-E.1 `[critical]` Leaves unrelated dirty work untouched and does not treat an unconfirmed finding as a required edit. | ○ | Step 5 requires pre-existing dirty files to be recorded with scope and observed-status or diff evidence. Step 9 requires each finding to be verified and expressly says unconfirmed findings must be recorded as unconfirmed and not fixed as facts. |
| IMP-E.2 Records discovered work outside scope rather than silently fixing it. | ○ | Hard rule 35 requires discovered work outside the assigned scope to be reported to the coordinator and forbids fixing it until it is recorded, scoped, dependency-checked, and dispatched as required work. |
| IMP-E.3 States the review or validation evidence needed next. | ○ | Step 9 names current code, tests, or a stated contract as confirmation evidence. Steps 3, 5, 7, and 10 require a validation target, recorded validation evidence, targeted checks, and rerunning affected validation after a confirmed fix. |

## Result

- Success: ○. Every `[critical]` checklist item is `○`.
- Accuracy: 100.00% (3.0 / 3 checklist points).
- tool_uses: unavailable. No fresh executor ran in this artifact-only simulation, so task-result metadata was not produced.
- duration_ms: unavailable. No fresh executor ran in this artifact-only simulation, so task-result metadata was not produced.
- Retries: unavailable. No executor output exists from which to record repeated judgments.

## New Unclear Points

- None. The current skill specifies that unconfirmed findings must be recorded without being fixed as facts, and names the evidence classes used to verify them.

## New Discretion Gaps

- The scenario does not name the alleged caller, contract, validation command, or real surface. A real executor must select the applicable available evidence without inventing fixture details.
- The scenario does not establish whether the unconfirmed finding is in scope. If confirmation reveals out-of-scope work, the operator must route it to the coordinator under hard rule 35.

## Convergence Note

- Convergence is not established. This is one artifact-only iteration, the required fresh-executor metadata is unavailable, and no hold-out scenario has run. The protocol requires two consecutive qualifying rounds and a hold-out result.
