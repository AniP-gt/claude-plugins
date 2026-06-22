---
name: omo-ralph-loop
description: Content-only autonomous continuation loop for iterative fix, review, validation, and handoff when runtime loop hooks are unavailable.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task
user-invocable: true
---

# OMO Ralph Loop

Use this skill when the user wants iterative progress until a concrete completion condition is met, such as tests passing, a blocker resolved, or a review gate approving.

This skill is a manual Claude Code equivalent of runtime loop behavior. It does not install hooks or continue after the session stops unless the operator records a handoff and resumes it.

## Loop Contract

1. Define the completion promise in one sentence.
2. Create a visible state record: current iteration, goal, blockers, changed files, validation, and next exact action.
3. Run one iteration: investigate, edit or delegate, validate, review if needed, and update the state record.
4. Continue only while the next action is clear and safe.
5. Stop when the completion promise is satisfied, the same blocker survives one bounded retry round, external approval is needed, or validation cannot be run.

## Recovery Contract

- On resume, read the state record before asking the user what happened.
- Preserve previous validation results with timestamps or command names.
- Mark stale assumptions before continuing.
- If a background agent was pending, record whether its result was used, stalled, or superseded.

## Hard Rules

- Do not loop without a completion promise.
- Do not hide failed iterations.
- Do not continue after an irreversible or external-side-effect action becomes necessary.
- Do not claim autonomous completion if the final validation was not run.

## Output Contract

- Completion promise.
- Iteration ledger.
- Current state.
- Validation evidence.
- Stop reason or next exact action.
