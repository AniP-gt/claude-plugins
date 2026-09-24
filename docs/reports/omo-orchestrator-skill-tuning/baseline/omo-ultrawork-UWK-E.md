# omo-ultrawork UWK-E Baseline

## Protocol

- Scenario: `UWK-E`
- Target: `omo-orchestrator/skills/omo-ultrawork/SKILL.md`
- Execution mode: fresh blank-slate, artifact-only simulation
- Fixture mutation: none
- Target or protocol mutation: none
- Services, credentials, Git mutation, and private-transcript access: none

## Output

### Merge Decision: `BLOCKED_PENDING_MERGE_PLAN`

Wave A returned partial output. It is not successful and cannot be merged.

Wave B proposes an edit to the same file. Its change must not run or merge in parallel with Wave A. Assign a single owner for that file, serialize the work, and record a merge plan before either change is accepted.

Run one bounded follow-up with Wave A: request its declared files, affected behavior, commands or checks run, remaining gap, and whether its output is usable. If that pass still lacks concrete evidence, stop waiting, retain the gap in the ledger, and leave Wave A incomplete.

Before merging any result, an independent reviewer must check each executor claim against the declared evidence. The reviewer must confirm the final file content, affected behavior, and required validation evidence. No completion claim is permitted until that check is recorded.

### Wave Ledger

| Wave | State | Same-file boundary | Evidence status | Next action |
|---|---|---|---|---|
| A | `PARTIAL`, not complete | Serialized with Wave B | Gap: concrete evidence not supplied | One bounded follow-up, then record the outcome |
| B | `BLOCKED` | Cannot edit or merge the shared file in parallel | No merge evidence accepted | Wait for the recorded merge plan and Wave A disposition |

## Requirements Met

1. [critical] `○` Wave A is explicitly treated as incomplete, not successful. Wave B is blocked from conflicting same-file edits until a single-owner serialized merge plan exists.
2. `○` The report specifies exactly one bounded follow-up for Wave A and records the missing concrete evidence as a ledger gap if the follow-up fails.
3. `○` The report requires an independent reviewer to verify executor claims against declared evidence before merge or completion.

## Scoring

- Overall success: `○`
- Accuracy: `100%` (`3 / 3`)
- `tool_uses`: unavailable
- `duration_ms`: unavailable
- Retries: `0`. No judgment was redone.

## Unclear Points

- None. The target prompt directly covers partial output, bounded follow-up, same-file conflicts, and independent checking.

## Discretion Gaps

- The scenario does not state the file name, expected behavior, or the evidence Wave A omitted. The artifact records these as required follow-up evidence rather than inventing them.
- The scenario does not assign a merge owner. The artifact requires one owner but does not select a person or agent.

## Fix Proposal

- None. Frozen UWK-E items 1, 2, and 3 are satisfied by the target prompt.
