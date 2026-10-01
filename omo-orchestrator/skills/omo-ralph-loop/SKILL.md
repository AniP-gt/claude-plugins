---
name: omo-ralph-loop
description: Content-only manual continuation loop for iterative fix, review, validation, and handoff with bounded retries and independent approval.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task, Skill
user-invocable: true
---

# OMO Ralph Loop

Use this skill when the user wants iterative progress until a concrete completion condition is met, such as tests passing, a blocker resolved, and an independent review gate approving.

This skill installs no hooks and does not continue after the session stops unless the operator records a handoff and resumes it.

## Shared Controller

Ralph is the sole owner of implementation/review iteration counts, continuation, stuck detection, and resume state. `omo-review-loop` selects the detailed review workflow; `omo-implement` performs one implementation pass; `omo-review-work` returns one final gate verdict. Calling any of them from an active Ralph task reuses its TASK_ID, ledger, current iteration, and cap. Never start a nested Ralph controller or a fresh budget for feedback, QA failures, or gate findings.

Record `iteration`, `cap` (default 20), `status`, `phase`, `workflow`, `review_base`, blocker history, and next exact action in the append-only ledger. Reserve an iteration before dispatching its implementation/fix or evidence work. One iteration contains one scoped work pass, validation, independent review, and, if ready, QA and the final gate. Any resulting repair or renewed review pass is the next iteration; a pause, report, oracle consultation, or bounded missing-output follow-up stays in the current iteration. A failed attempt consumes its reserved iteration. An interrupted phase resumes that same iteration rather than reserving it twice.

When `omo-review-loop` is the entry, load this controller once and use that skill's phases as the iteration body. Direct Ralph implementation tasks use `omo-implement` plus independent review; tasks asking for parallel review use the review workflow. Other entry skills keep their dispatch/wave logic but pass all repair and re-review transitions to this controller. For a plan workflow, an initial wave of independent tasks is one scoped work pass; each subsequent wave or repair pass reserves the next iteration. Final QA and gate after the last wave belong to its current iteration.

## Loop Contract

1. Define the completion promise in one sentence.
2. Create or continue the visible state record at `.claude/omo/handoffs/<task-slug>.md`: current iteration, goal, blockers, changed files, validation, and next exact action. Initialize it with an append-only first entry only when no record exists.
3. Before each iteration, confirm there is no unanswered decision or unresolved in-flight work required by or overlapping the next iteration, the owner and scope are clear, the current state was freshly read, and the validation evidence to collect during this iteration is named. From iteration 2 onward, assess material task-state progress as a changed task state, resolved blocker, or new validated evidence. Tool activity alone is not progress. Apply the warning, strategy-change, and stop thresholds in `references/iteration-guards.md` using the same ledger; do not introduce an earlier independent no-progress stop.
4. Run one iteration: investigate, edit or delegate, validate, review if needed, and update the state record.
5. Continue only while the next action is clear and safe.
6. When the completion promise appears satisfied, require final independent review before completion. Only `APPROVE` may complete the loop.
7. If review returns `REQUEST_CHANGES`, append the result to the handoff ledger and request the next iteration under the same cap for a targeted fix, validation, and re-review.
8. If review returns `INCONCLUSIVE`, append the result to the handoff ledger and block completion until the required evidence is obtained or the exact blocker is handed off.
9. Iteration exhaustion, a satisfied promise, passing checks, or lack of new findings is not completion without final independent `APPROVE`.

Iteration cap (default 20), stuck detection (same error in 3 consecutive iterations stops the loop), the `omo-implementer` iteration brief, and per-task iteration shapes are in [iteration guards](references/iteration-guards.md).

## Recovery Contract

- On resume, first inspect existing review artifacts and apply the migration and blocked-run rules in `omo-review-loop` when that workflow was used. Never silently restart an exhausted or blocked run. An explicit user budget grant is required to extend an exhausted cap, and must be appended with the previous count preserved.
- On resume, read the full `.claude/omo/handoffs/<task-slug>.md` record, reconcile the latest entry with the current task state, and manually take its recorded next exact action or append a corrected one. Do not resume automatically.
- Preserve previous validation results with timestamps or command names.
- Mark stale assumptions before continuing.
- If a background agent was pending, record whether its result was used, stalled, or superseded.
- Before retrying or stopping after `REQUEST_CHANGES` or `INCONCLUSIVE`, append the gate result, evidence, blocker, retry state, and next exact action to the handoff ledger.

## Hard Rules

- Do not loop without a completion promise.
- Do not hide failed iterations.
- Do not continue after an irreversible or external-side-effect action becomes necessary.
- Do not claim autonomous completion if the final validation was not run.
- Do not treat retry-budget exhaustion as approval. Record the blocker and hand it off instead.
- Do not complete without a final independent `APPROVE` that verifies requested scope, task-specific constraints, dependencies and retries, executable QA, validation, handoff completeness, and version agreement across every manifest that declares the version for release-facing changes. Check for unsupported automation, hooks, runtime engines, scripts, dependencies, and provider-specific behavior only when the original task, repository, or plugin contract requires content-only work.

## Output Contract

- Completion promise.
- Iteration ledger.
- Current state.
- Validation evidence.
- Final review outcome and approval evidence, or the recorded blocker.
- Stop reason or next exact action.
