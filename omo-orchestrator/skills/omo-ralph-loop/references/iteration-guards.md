# Ralph Loop Iteration Guards

## Iteration Budget

- Default cap: 20 iterations unless the user sets another number. Record the cap in the completion promise entry.
- Never exceed the cap silently. On reaching it, append the remaining issues and the blocker, then stop without claiming completion.
- All implementation, feedback, evidence, QA-repair, and final-gate re-review passes share this cap. No phase or entry skill grants extra iterations. A local tool/worker recovery limit may stop sooner, but never starts another implementation/review pass outside Ralph accounting.
- Before a next pass, require `iteration < cap`, increment and append the reserved number, then dispatch. If the current pass approves at the cap, completion is allowed; otherwise record `MAX_ITERATIONS_REACHED` and stop. Only an explicit user grant may extend the cap.

## Measured Goals

Use this when the goal is a quantity ("reduce", "faster", "smaller", "fewer", "raise coverage") or when a number can decide done. A loop with a number to move runs without calling the user each iteration; a loop judged by taste does not.

1. Define the metric before the first edit: the command, how the number is read from its output, the baseline value, and the target. Measure the baseline first, read-only, before iteration 1; it reserves no iteration. Re-measure numbers the user reported rather than copying them. When the user gave a direction but no target ("down", "faster"), propose a target from that baseline and ask for it before iteration 1. Asking is required here and is not inventing a budget; "keep going until done" does not waive it. Until the answer arrives, the ledger shows iteration 0 with the open decision; read-only exploration, planning, and ledger or notepad writes may continue; product edits may not.
2. Prefer a deterministic measure: counts (warnings, failing tests, duplicate blocks, surviving mutants), allocations, instruction or operation counts, or bytes. Wall-clock time varies between runs and machines, and peak memory often does too. When the user named a timing benchmark, keep it as the target and add a deterministic companion measure when one exists, such as an operation or allocation count from the runtime's own profiler or benchmark flags. For any measure whose baseline runs differ, run before and after several times on the same machine (never compare numbers from different machines, such as CI against local), compare medians, and require the median improvement to exceed the baseline runs' full spread (max minus min). One run of such a measure is never evidence.
3. Lock behavior while the number moves: the existing tests stay green with the same test count, and outputs for fixed inputs stay identical unless the goal is to change them.
4. Give the ledger a metric row per iteration (`iteration | metric | value | target`), starting with the baseline as iteration 0, and append the measured value every iteration. Movement toward the target counts as material progress. No movement for 2 iterations triggers the warning row below.
5. Gaming the metric is a defect, not progress: changing the rule, threshold, config, or ignore list that produces the number; adding suppression comments; changing benchmark inputs, sizes, or repetition counts; deleting or skipping tests or benchmark cases.
6. Name every criterion that needs human taste (look, naming, readability) as an owner decision at the start, with the evidence the owner will judge. Do not discover it mid-loop.

## Stuck Detection

Track each blocker by stable file and defect mechanism, or by the missing evidence requirement, across iterations and review stages. Lines and exact messages are evidence locators; changing their wording or location does not reset the streak. Findings that one fix would resolve share an identity.

| Signal | Action |
|---|---|
| Same error in 3 consecutive iterations | Stop. Classify the cause (below), append the approaches tried per iteration, and take that cause's next action. |
| The environment refuses the work (missing access below) | Stop now, even before the third iteration. |
| No material progress for 2 iterations | Record a warning and switch to a materially different approach, or consult `omo-oracle`. |
| A fix recreates an earlier error | Treat as the same error for the 3-iteration count. |
| A destructive or external-side-effect action becomes necessary | Stop and ask before acting. |

### Classify The Cause

Before switching strategy or stopping, classify why the blocker persists. The class picks the next action; "try again harder" is never one of them.

| Cause | Signal | Next action |
|---|---|---|
| Missing context | The agent lacked a fact, convention, spec, or expected behavior; fixes contradict an unwritten rule or guess at intent. A fact that exists in the repository but never reached the brief counts as missing. | Add the missing instruction, spec excerpt, or a failing test that pins the expected behavior to the next brief. That counts as the materially different approach. If only the user knows it, ask that one question. |
| Missing access | The environment refuses: permission or sandbox denial, missing credential, tool not installed, or a needed service or network that is confirmed down or unreachable from here. A connection error alone is not yet this class; check whether the service runs and is reachable before the next code change. | Stop at first sight, without spending more iterations. Ask the user for the specific access, or for them to run the check and share the output. Never mock around the check, weaken it, or count it as passed. |
| Beyond reach | The briefs carried the needed context, access is present, and materially different approaches still fail | Consult `omo-oracle` once if not yet done. If it names a new cause and a concrete fix, that is the materially different approach for the next iteration. Otherwise stop and hand off the smallest reproducing case and what each approach ruled out. |

- In `Cause`, always say in a few words why the other two classes do not fit.
- When the 3-iteration rule and a missing-access stop apply together, write one `STUCK` entry with the access cause.
- Every stop in this table is a pause. Once the user supplies the answer, the access, or a new strategy, resume at the next iteration under the same cap. Only cap exhaustion needs a user grant.
- A missing-access blocker is tracked as a missing evidence requirement. Record what was verified without the access (for example unit tests) and what stays unverified.
- For any cause, mark code changes made while chasing a blocker as unconfirmed and leave them in place. Once the check can run, rerun it before any new edit and keep or revert them on that result.
- If an earlier iteration skipped one of these guards, say so in the current entry; never rewrite earlier entries.

Stuck entry shape:

```text
STUCK: "<error>" persisted for <n> iterations.
Cause: <missing context | missing access | beyond reach> - <evidence>
Verified: <checks that ran and passed>
Unverified: <checks that could not run>
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
