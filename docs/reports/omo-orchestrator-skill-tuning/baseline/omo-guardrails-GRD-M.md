# omo-guardrails GRD-M Baseline

## Protocol

- Target: `omo-orchestrator/skills/omo-guardrails/SKILL.md`
- Frozen scenario: `GRD-M`, a disposable handoff says one research lane stalled during a delegated task. Write an operator checkpoint artifact.
- Execution mode: fresh blank-slate, artifact-only simulation.
- Fixture activity: none. The scenario supplies no disposable handoff content.
- External effects: none. No service, credential, Git state, target repository, or skill file was changed.
- `tool_uses`: unavailable. Task-result metadata was not supplied, so this value is not estimated.
- `duration_ms`: unavailable. Task-result metadata was not supplied, so this value is not estimated.

## Output

### Operator Checkpoint

**Coordinator boundary:** The main context remains coordinator-only. It records the stalled lane, requests the bounded follow-up, verifies returned evidence, and updates the handoff. It does not perform the research lane's substantive investigation or create a duplicate lane.

**Trigger condition:** The assigned research lane has stalled because it returned no usable evidence for its delegated question.

**Stalled-lane record:** Append a short checkpoint to the handoff that identifies the lane as `STALLED`, names its delegated question, records its current dependency status, and identifies the missing evidence. The supplied scenario does not name the lane, question, task slug, or expected research result, so those fields remain explicit required inputs rather than invented facts.

**One bounded follow-up:** Send one follow-up to the existing research-lane owner. Request the delegated question, inspected fixture paths or sources, findings or explicit evidence gap, and a concise state report. Do not repeat the research in the main context and do not open a duplicate lane.

**Evidence required:** Usable follow-up evidence consists of the lane's inspected paths or sources, its finding or documented gap, and enough state to determine whether its dependency is resolved. The coordinator records the returned evidence in the handoff before using it in a final claim.

**Stop condition:** If the one follow-up does not produce usable evidence, stop retrying that lane. Keep it marked `STALLED`, preserve the evidence gap, and continue only when the available evidence makes that safe. Otherwise, record the unresolved dependency as a blocker and ask one precise question if the missing information materially changes the result.

**Next handoff field:** `Next action: request one bounded follow-up from the existing research-lane owner, then append its evidence or continuing gap before routing further work.`

**Manual control point:** This is a content-only process. There is no automatic stall monitor, retry mechanism, handoff writer, or continuation. An operator must issue the follow-up, inspect the response, and append the checkpoint fields manually.

## Requirements Met

1. [critical] `○` The checkpoint records the lane as `STALLED`, limits recovery to one follow-up with its existing owner, and rejects duplicate research by the main context or a new lane.
2. `○` It explicitly states the trigger condition, required follow-up evidence, stop condition, and a named next handoff field.
3. `○` It keeps the main context in a coordinator role that tracks, verifies, and hands off evidence without taking over the delegated research.

## Overall Result

- Success: `○`. Every critical checklist item is `○`.
- Accuracy: `100%` (3.0 of 3 checklist points).
- Retries: `0`. No judgment was redone.

## Metadata

| Measurement | Value |
| --- | --- |
| `tool_uses` | unavailable, task-result metadata was not supplied |
| `duration_ms` | unavailable, task-result metadata was not supplied |
| retries | 0, no judgment was redone |

## Unclear Points

- The scenario does not identify the stalled lane, delegated research question, task slug, dependency, or expected evidence. The checkpoint requires those fields without fabricating fixture facts.
- The phrase "when safe" has no scenario-specific decision rule. The checkpoint limits continuation to cases where the available evidence resolves the remaining dependency, otherwise it preserves a blocker.

## Discretion Gaps

- The skill requires one bounded follow-up but gives no time limit. This baseline bounds it by count, exactly one follow-up, rather than inventing a response window.
- The skill's handoff minimum lists the required information but not a field order. This checkpoint orders it as trigger, stalled-lane record, follow-up, evidence, stop condition, and next action.

## Item-Tied Proposal

- No prompt change proposed. Frozen items `GRD-M.1`, `GRD-M.2`, and `GRD-M.3` are fully satisfied. The unclear points and discretion gaps result from intentionally absent scenario inputs, not from a partial or failed frozen item.
