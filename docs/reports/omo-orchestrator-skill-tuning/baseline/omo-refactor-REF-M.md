# OMO Refactor Baseline, REF-M

## Scope And Method

This is an artifact-only simulation of the frozen REF-M scenario. It evaluates the unmodified `omo-refactor` prompt against the supplied disposable-module task. No fixture was inspected or changed. No target repository, external service, Git state, credential, or prior evaluation finding was used.

Scenario: reorganize a small disposable module without intended behavior change while preserving its supplied regression check.

## Simulated Execution Artifact

1. Set the boundary to internal organization of the named disposable module. Exclude feature work, public-contract changes, unrelated cleanup, and pre-existing changes.
2. Run the supplied regression check before editing and record its result as the behavior lock.
3. Inventory the module's callers, callees, inputs, outputs, and side effects before the first edit.
4. Make one small internal reorganization in the fixture. Record the exact step delta and its local undo action before the next step.
5. Run the supplied targeted regression check after the meaningful step. If it fails, undo only that recorded delta, preserve earlier work, record the failed check and last safe state, then make at most one materially different retry.
6. Report the reorganized internal structure, the behavior lock, the validation result, and that the public contract did not move.

## Frozen Checklist Scoring

| Item | Result | Reason |
|---|---|---|
| 1. [critical] Locks behavior and inventories callers, callees, inputs, outputs, and side effects before refactoring. | ○ | The workflow requires a baseline, then behavior lock, then the complete inventory before refactoring. |
| 2. Makes small reversible fixture-only steps with targeted validation. | partial | The workflow requires small reversible steps and targeted validation. The fixture-only boundary comes from the frozen protocol, not the prompt. The prompt also requires a step-local undo plan but does not say what evidence must record that boundary. |
| 3. Reports whether any public contract moved. | ○ | The hard rules prohibit unnecessary public-contract reshaping, and the report contract requires a statement about contract movement. |

## Outcome

- Success: ○. The only critical item is scored ○.
- Accuracy: 83.3%. Score: 2.5 of 3.
- `tool_uses`: unavailable. No executor task metadata was seen.
- `duration_ms`: unavailable. No executor task metadata was seen.
- Retries: unavailable. No executor retry record was seen.

## Unclear Points

- Item 2: The prompt requires a step-local undo plan, but it does not say where the executor must record the exact current-step delta and last safe state before continuing. That makes reversibility hard to audit from the final artifact.

## Discretion Gaps

- The prompt leaves the choice of regression coverage open when an existing check is available but does not isolate the reorganized behavior.
- It does not define the smallest report shape that proves a step was fixture-only and reversible.

## Proposed Fix

Tie the next prompt change to frozen item 2: require each meaningful refactor step to record the fixture path, exact current-step delta, local undo action, targeted check, and resulting safe state before the next step. This would make the existing reversibility and validation requirements inspectable without changing the scenario or scoring.

## Baseline Status

This report is a simulation artifact, not a completed empirical execution. A later empirical run needs a fresh blank-slate executor, the disposable fixture, and task-result metadata. The frozen scenario text, checklist items, critical tag, scoring, and disposition remain unchanged.
