# omo-debugging DBG-M Baseline

## Evaluation Boundary

Scenario: DBG-M, median.

This is an artifact-only simulation. The evaluator read only `omo-orchestrator/skills/omo-debugging/SKILL.md` and the frozen DBG-M protocol entry. No disposable fixture was supplied or changed. No diagnosis artifact or patch was produced because this baseline records prompt coverage, not a live fixture execution.

## Requirements Met

1. [critical] `○` Reproduces the stated failure before changing the fixture. The workflow starts with “Reproduce the issue first,” and the hard rules forbid speculative fixes and a fixed claim without reproducing the prior failure mode or validating affected behavior.
2. `○` States at least three hypotheses and evidence for the proven root cause. The workflow requires at least three plausible hypotheses, evidence that eliminates or strengthens each one, and root-cause proof before code changes.
3. `○` Adds or identifies a failing validation target and reruns it after the fix. The workflow requires a failing test or validation target when the project supports it, then requires rerunning the reproduction and related validation after the minimal fix.

## Result

Success: `○`

Accuracy: `100%` (`3 / 3` checklist points)

The critical item is `○`, so the immutable success rule passes.

## Execution Metadata

`tool_uses`: unavailable. This artifact-only simulation did not dispatch a fresh executor, so task-result metadata does not exist.

`duration_ms`: unavailable. This artifact-only simulation did not dispatch a fresh executor, so task-result metadata does not exist.

Retries: `0`. No judgment was redone during this artifact-only simulation.

## Unclear Points

None identified for the frozen DBG-M checklist. The skill names the required order of work and the required evidence for diagnosis, patch scope, and recovery validation.

## Discretion Gaps

The exact form of the diagnosis artifact and the specific validation command are left to the fixture and project. This does not block DBG-M because the frozen scenario supplies a documented failure and the skill permits either a failing test or another validation target when the project supports it.

## Frozen-Item Fix Proposal

No prompt change proposed. Frozen checklist item 3 is already satisfied by the explicit requirement to add or identify a failing test or validation target, followed by rerunning the reproduction and related validation. Preserve the frozen prompt and protocol for later measured execution.
