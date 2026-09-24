# OMO Refactor Baseline, REF-E

## Evaluation Scope

- Target: `omo-orchestrator/skills/omo-refactor/SKILL.md`
- Frozen scenario: `REF-E`
- Mode: artifact-only simulation
- Fixture: no disposable fixture contents were provided or inspected.
- Boundary: no prompt edits, fixture edits, Git actions, external actions, credentials, or private transcripts were used.

This is a simulated baseline assessment of the target prompt against the frozen scenario. It is not evidence that a fresh executor ran the scenario.

## Simulated Recovery Plan

1. Keep all unrelated dirty content outside the refactor boundary untouched.
2. Record the failing targeted validation command and its observed failure output in the fixture artifact.
3. Identify the last safe state from the validation result before the failed step.
4. Undo only the recorded delta from the current refactor step. Do not use a broad reset, checkout, or restore action.
5. Confirm that the pre-existing dirty content remains present after the step-local undo.
6. Retry once only with a materially different approach, provided the behavior lock, scope, and public contract remain sound.
7. Run the targeted validation again. If the retry fails, abort the refactor and preserve the record of both failed checks, the last safe state, and the untouched pre-existing changes.

## Frozen Checklist Scoring

| Item | Result | Reason |
| --- | --- | --- |
| 1. [critical] Reverts only the recorded current-step delta and preserves pre-existing changes. | ○ | The workflow requires a step-local undo plan that preserves pre-existing changes. Its failure path says to undo only the recorded current-step delta and preserve pre-existing changes. The hard rules also prohibit broad destructive reset, checkout, and restore commands. |
| 2. Records the failed check and last safe state. | ○ | The failure path explicitly requires recording the failed check and last safe state. The report contract requires each failed check and last safe state when applicable. |
| 3. Stops after the allowed materially different retry if it also fails. | ○ | The workflow permits at most one materially different retry. It requires aborting when that retry fails, or when the behavior lock, scope, or public contract is no longer sound. |

## Result

- Success: ○
- Accuracy: 100% (3.0 of 3.0 checklist points)
- `tool_uses`: unavailable, no executor task-result metadata was seen.
- `duration_ms`: unavailable, no executor task-result metadata was seen.
- Retries: 0 observed. This artifact-only simulation did not execute the permitted retry. The simulated plan allows one materially different retry, then requires abort on failure.

## Unclear Points

- None identified for frozen item 1. The target distinguishes the current-step delta from pre-existing changes and prohibits broad undo commands.

## Discretion Gaps

- The target does not prescribe a concrete artifact format for recording the current-step delta, failed check, or last safe state. An executor must choose a suitable fixture-local record.
- The target leaves the test for a materially different retry to executor judgment. It gives the retry limit and required conditions, but not examples of approaches that qualify.

## Next Fix Proposal

- Frozen item 3: add one short criterion for what makes a retry materially different, so executors can apply the one-retry limit consistently without broadening the workflow.

## Protocol Note

The frozen protocol requires a fresh blank-slate executor and task-result metadata for empirical measurement. Because this run was explicitly artifact-only, metadata remains unavailable and this report must not be treated as an empirical baseline result.
