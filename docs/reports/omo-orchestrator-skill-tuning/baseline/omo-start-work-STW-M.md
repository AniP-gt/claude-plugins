# STW-M Baseline Execution

## Frozen Scenario

**Skill:** `omo-start-work`  
**Scenario:** STW-M, start a synthetic two-task change with an approved bounded plan.  
**Execution mode:** artifact-only simulation in a disposable fixture. No edit, service contact, Git mutation, or validation command was performed.

## Output

### Kickoff State

**Goal:** Add synthetic slug normalization in two ordered tasks.

**Scope:**

1. Task A adds the fixture's `normalizeSlug` behavior.
2. Task B updates the fixture command to use `normalizeSlug`.

**Non-goals:**

1. No changes outside the two synthetic fixture tasks.
2. No new command options, persistence format, or release work.
3. No editing begins from plan approval alone. Editing remains blocked until this kickoff state and its behavior assertion are recorded.

**Behavior assertion before editing:** A fixture call with `" Hello World "` must produce `"hello-world"`; the task's characterization test must fail before Task A and pass after both tasks are complete.

**Dependency order:** Task A must finish and satisfy its characterization test before Task B begins. Task B depends on Task A's exported behavior.

**Evidence targets:**

1. Characterization test for `normalizeSlug`, evidence location: unavailable until the disposable fixture test is run.
2. Targeted command test, evidence location: unavailable until the disposable fixture test is run.
3. Fixture diagnostics, evidence location: unavailable until diagnostics are run.
4. Command invocation using `" Hello World "`, expected output `"hello-world"`, evidence location: unavailable until the fixture command is exercised.

### Proposed TodoWrite State

| Status | Owner | Task | Dependency | Completion criteria | Next exact action |
|---|---|---|---|---|---|
| `in_progress` | fixture implementer | Task A: add `normalizeSlug` | None | The characterization test proves `" Hello World "` becomes `"hello-world"`. | Add the failing `normalizeSlug` characterization test in the disposable fixture. |
| `pending` | fixture implementer | Task B: connect the command to `normalizeSlug` | Task A characterization test passes | The command test proves the command emits `"hello-world"`. | Wait for Task A completion and synchronized state before starting. |

Exactly one TodoWrite item is active: Task A.

### Proposed Append-Only Handoff Entry

```md
# synthetic-slug-normalization

## Immutable Task Metadata

- Goal: add synthetic slug normalization in two ordered fixture tasks.
- Scope: Task A adds `normalizeSlug`; Task B connects the fixture command.
- Non-goals: command options, persistence formats, release work, and files outside the fixture tasks.

## Phase 1: kickoff

- Owner: fixture implementer
- Active task: Task A, add `normalizeSlug`
- Dependency status: no predecessor; Task B remains pending on Task A's characterization result.
- Behavior assertion: `" Hello World "` must become `"hello-world"`.
- Completion criteria: the Task A characterization test proves the assertion.
- Evidence targets: characterization test, targeted command test, fixture diagnostics, and command invocation. Evidence locations are unavailable until those checks run.
- Risks: Task B must not begin before Task A's exported behavior is proven.
- Final-gate state: not applicable at kickoff; no completion decision is recorded.
- Next exact action: add the failing `normalizeSlug` characterization test in the disposable fixture.
```

The active TodoWrite item and kickoff entry match on owner, active task, dependency status, completion criteria, and next exact action.

## Requirements Met

1. **[critical] ○** Scope, non-goals, evidence targets, dependency order, and a pre-edit behavior assertion are stated in the kickoff state.
2. **○** Task A is the sole `in_progress` TodoWrite item. Task B is explicitly `pending`.
3. **○** The proposed TodoWrite state and append-only kickoff entry use the same owner, active task, dependency status, completion criteria, and next exact action.

## Overall Result

**Success:** ○. All critical requirements are ○.

**Accuracy:** 100% (3.0 of 3.0 checklist points).

## Metadata

| Measurement | Value |
|---|---|
| `tool_uses` | unavailable |
| `duration_ms` | unavailable |
| retries | 0, no judgment was redone |

## Unclear Points

- None that blocked the simulated kickoff. The scenario did not name the two fixture tasks, so the output uses a clearly marked synthetic slug-normalization example.

## Discretion Gaps

- The scenario does not prescribe task names, owners, behavior, or validation commands. The report selected a minimal ordered helper-and-command example to make the required state fields inspectable.
- The scenario does not state whether a review gate applies. The kickoff entry records no completion decision and leaves the final gate not applicable at this pre-edit boundary.

## Fix Proposal

No prompt change proposed. No STW-M frozen checklist item was partial or failed.
