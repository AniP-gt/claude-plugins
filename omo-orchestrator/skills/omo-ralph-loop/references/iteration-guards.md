# Ralph Loop Iteration Guards

## Iteration Budget

- Default cap: 20 iterations unless the user sets another number. Record the cap in the completion promise entry.
- Never exceed the cap silently. On reaching it, append the remaining issues and the blocker, then stop without claiming completion.
- The cap bounds the loop. The per-fix retry budget (one attempt plus two materially different retries) still applies to each individual blocker inside it.

## Stuck Detection

Track each blocking error by `file:line` or exact message across iterations.

| Signal | Action |
|---|---|
| Same error in 3 consecutive iterations | Stop. Append the approaches tried per iteration and ask for a different strategy or a user decision. |
| No material progress for 2 iterations | Record a warning and switch to a materially different approach, or consult `omo-oracle`. |
| A fix recreates an earlier error | Treat as the same error for the 3-iteration count. |
| A destructive or external-side-effect action becomes necessary | Stop and ask before acting. |

Stuck entry shape:

```text
STUCK: "<error>" persisted for 3 iterations.
Approaches tried:
1. Iteration <n>: <approach>
2. Iteration <n+1>: <approach>
3. Iteration <n+2>: <approach>
Next exact action: <user decision or different strategy needed>
```

## Iteration Brief

When an iteration is delegated to `omo-implementer`, send a self-contained brief:

```text
Task: <original goal>
Iteration: <n> of <cap>
Previous attempts: <what was tried in earlier iterations and what succeeded or failed>
Scope: <files or area; no unrelated changes>
Done when: <binary condition, e.g. `bun test src/auth` exits 0>
Report: changed files, validation command and result, remaining issues
```

An executor without a `Done when` condition has no exit. Do not delegate without one.

## Iteration Shapes

| Task | Typical progression | Done when |
|---|---|---|
| Test fixing | Run tests and list failures, fix a batch, fix regressions from the fixes | Target suite passes |
| Lint or type errors | Collect errors, fix them, fix cascading errors | Zero errors from the named command |
| Refactoring | Lock behavior, extract one responsibility per iteration, fix imports | Target structure reached and tests green |

Each iteration changes only what its brief scopes. Unrelated edits during a fix iteration are a defect.
