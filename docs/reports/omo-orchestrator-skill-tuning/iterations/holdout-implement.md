# omo-implement Hold Out Evaluation

## Freeze Record

- Target: `omo-orchestrator/skills/omo-implement/SKILL.md`
- Hold out scenario: The requested fixture change is complete. Diagnostics are unavailable, an unrelated file is already dirty, and a reviewer suggests an edit that has not been confirmed.
- Evaluation mode: Static prompt evaluation. The requested read-only evaluation boundary does not permit a fresh executor, fixture inspection, or runtime validation.
- Boundary: No fixture, source, Git state, service, credential, or private transcript was accessed or changed.

## Expected Decision

Leave the unrelated dirty file untouched. Record its out-of-scope status and evidence that this work did not modify it.

Record the reviewer suggestion as unconfirmed. Verify it against current code, tests, callers, or the stated contract before treating it as a required edit. If that proof is unavailable, do not make the suggested edit.

Report diagnostics as unavailable and name the resulting validation gap. The current skill does not explicitly require a stop or forbid a completion claim when required diagnostics are unavailable.

## Hold Out Checklist Scores

| Item | Result | Reason |
| --- | --- | --- |
| HOLDOUT-IMP.1 `[critical]` Stops without a completion claim when required diagnostics are unavailable, and records the missing validation as a blocker. | × | Step 6 requires diagnostics and step 25 requires reporting unverified areas, but neither states that unavailable diagnostics block completion or require a stop. Hard rule 34 only forbids claiming a check passed when it was not run. |
| HOLDOUT-IMP.2 Preserves the pre-existing unrelated dirty file and records its scope boundary. | ○ | Step 5 requires every pre-existing dirty file to be recorded with scope and evidence that this work did not modify it. Hard rule 32 forbids modifying unrelated dirty files. |
| HOLDOUT-IMP.3 Rejects the unconfirmed reviewer suggestion as an edit until evidence confirms it. | ○ | Step 9 requires verification against code, tests, or contract evidence, and says unconfirmed findings must be recorded without being fixed as facts. |
| HOLDOUT-IMP.4 Reports unavailable diagnostics honestly rather than claiming that validation passed. | ○ | Hard rule 34 prohibits claiming a check passed unless it ran in the current session. Step 25 requires reporting any unverified area. |

## Result

- Success: ×. The critical stop condition is not stated by the current skill.
- Accuracy: 75.00% (3.0 / 4 checklist points).
- tool_uses: unavailable. No fresh executor ran, so task-result metadata was not produced.
- duration_ms: unavailable. No fresh executor ran, so task-result metadata was not produced.
- Retries: unavailable. No executor output exists from which to record repeated judgments.

## Gaps

- `[critical]` HOLDOUT-IMP.1 failed because the skill permits a report with an unverified area but does not require `INCONCLUSIVE`, a blocker, or a stop when diagnostics are unavailable.
- The skill does not distinguish a nonessential diagnostic from a required diagnostic, so an executor must decide whether the missing check should block handoff.
- The requested fixture change being complete does not resolve the missing diagnostic evidence. A completion claim would remain unsupported.

## Overfitting Judgment

- This hold out exposes a gap that the frozen IMP-E scenario did not test. The prior scenario covered dirty files and unconfirmed review findings, but not the completion boundary for unavailable diagnostics.
- The 75.00% hold-out score is below the expected full score by 25 points. Under the protocol's 15-point threshold, treat the current wording as overfit to the earlier scenario and return to prompt design rather than claiming convergence.
- A follow-up prompt revision should make required unavailable validation an explicit `INCONCLUSIVE` stop condition, forbid a completion claim, and require the exact blocker plus next manual action.
