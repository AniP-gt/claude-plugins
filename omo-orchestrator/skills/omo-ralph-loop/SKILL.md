---
name: omo-ralph-loop
description: Content-only manual continuation loop for iterative fix, review, validation, and handoff with bounded retries and independent approval.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task
user-invocable: true
---

# OMO Ralph Loop

Use this skill when the user wants iterative progress until a concrete completion condition is met, such as tests passing, a blocker resolved, and an independent review gate approving.

This skill is a manual Claude Code equivalent of runtime loop behavior. It does not install hooks or continue after the session stops unless the operator records a handoff and resumes it.

## Loop Contract

1. Define the completion promise in one sentence.
2. Create a visible state record: current iteration, goal, blockers, changed files, validation, and next exact action.
3. Run one iteration: investigate, edit or delegate, validate, review if needed, and update the state record.
4. Continue only while the next action is clear and safe.
5. When the completion promise appears satisfied, require final independent review before completion. Only `APPROVE` may complete the loop.
6. If review returns `REQUEST_CHANGES`, append the result to the handoff ledger, run a bounded targeted fix, validate the affected behavior, then re-review.
7. If review returns `INCONCLUSIVE`, append the result to the handoff ledger and block completion until the required evidence is obtained or the exact blocker is handed off.
8. Iteration exhaustion, a satisfied promise, passing checks, or lack of new findings is not completion without final independent `APPROVE`.

## Recovery Contract

- On resume, read the state record before asking the user what happened.
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
- Do not complete without a final independent `APPROVE` that verifies requested scope, task-specific constraints, dependencies and retries, executable QA, validation, handoff completeness, and version parity for release-facing changes. Check for unsupported automation, hooks, runtime engines, scripts, dependencies, and provider-specific behavior only when the original task, repository, or plugin contract requires content-only work.

## Output Contract

- Completion promise.
- Iteration ledger.
- Current state.
- Validation evidence.
- Final review outcome and approval evidence, or the recorded blocker.
- Stop reason or next exact action.
