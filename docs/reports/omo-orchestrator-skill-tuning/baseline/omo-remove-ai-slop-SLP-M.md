# OMO Remove AI Slop Baseline, SLP-M

## Scope And Method

This is an artifact-only simulation of the frozen SLP-M scenario. It evaluates the unmodified `omo-orchestrator/skills/omo-remove-ai-slop/SKILL.md` prompt against the supplied disposable-fixture task. No fixture was inspected or changed. No target repository, external service, Git state, credential, prior finding, or other scenario was used.

Scenario: clean one noisy comment and one duplicate branch in a disposable fixture with a supplied behavior check.

## Simulated Execution Artifact

1. Identify the supplied behavior check as the regression protection and run it before cleanup.
2. Review the named noisy comment for whether it merely restates code or has meaningful boundary or non-obvious intent.
3. Remove the comment only if it is understood noise. Keep it if it explains intent, a system boundary, or BDD behavior.
4. Review the duplicate branch, confirm the duplicated behavior is understood, and collapse only the duplicate path without changing the fixture's intended behavior.
5. Re-run the supplied behavior check after the cleanup cluster.
6. Report the removed comment and duplicate-branch patterns, the fixture file changed, and the actual verification result.

## Frozen Checklist Scoring

| Item | Result | Reason | Score |
|---|---|---|---|
| 1. [critical] Uses the validation target before claiming behavior preservation. | ○ | The cleanup priorities require behavior to be locked first with regression coverage or an equivalent validation target. The hard rules prohibit a removal claim without regression protection, and re-verification follows each cleanup cluster. | 1 |
| 2. Removes only clearly understood noise and keeps meaningful boundary or intent comments. | ○ | The decision rules require understood behavior and reachability before removal, retain system-boundary and non-obvious-intent comments, and require skipping uncertain candidates. | 1 |
| 3. Reports patterns removed, files changed, and verification. | ○ | The delivery contract explicitly requires the removed patterns, changed files, and behavior-verification method. | 1 |

## Outcome

- Success: ○. The only critical item is scored ○.
- Accuracy: 100.0%. Score: 3 of 3.
- `tool_uses`: unavailable. No fresh-executor task-result metadata was observed.
- `duration_ms`: unavailable. No fresh-executor task-result metadata was observed.
- Unseen metadata: unavailable. No executor output or fixture execution record was provided.
- Retries: 0. This artifact-only simulation did not redo a judgment.

## Unclear Points

- No critical checklist item failed.
- Item 1: The prompt requires regression protection but does not say that the exact validation command, before-and-after results, or any unavailable result must appear in the final report. That weakens the audit trail for a behavior-preservation claim.

## Discretion Gaps

- The prompt does not say how to decide whether one supplied behavior check covers both the removed comment and the collapsed duplicate branch, or when broader validation is needed.
- It does not require a candidate-by-candidate record of the preserved meaningful comment and the duplicate branch's equivalence evidence.
- The delivery contract names the report fields but does not define the minimum evidence that makes the cleanup boundary inspectable.

## Proposed Fix

Tie the next prompt change to frozen item 1: require the final report to record the validation target, its result before and after the cleanup cluster, and an explicit unavailable state when it could not run. This would make the existing regression-protection rule auditable without changing the frozen scenario or scoring.

## Baseline Status

This report is a simulation artifact, not a completed empirical execution. A later empirical run needs a fresh blank-slate executor, the disposable fixture, and task-result metadata. The frozen scenario text, checklist items, critical tag, scoring, and disposition remain unchanged.
