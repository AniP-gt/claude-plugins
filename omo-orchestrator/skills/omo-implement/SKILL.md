---
name: omo-implement
description: Execute a planned change with exploration first, minimal edits, one-pass implementation, TDD-oriented validation, and no speculative compatibility paths.
argument-hint: [task]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task, Skill
user-invocable: true
---

# OMO Implement

Use this skill for one scoped implementation or fix pass after scope is concrete. When delegated, return the result to the caller's active Ralph controller; do not start another controller or review loop. When invoked standalone, initialize or reuse `omo-ralph-loop` for this task and return any review findings to that controller for the next pass.

## Steps

1. Read the relevant code and nearby patterns.
2. Confirm the smallest behavior change that satisfies the request.
3. Add or identify a failing test or validation target when appropriate.
4. Edit only the required files.
5. Record evidence for the diff: changed files, affected callers, and the validation target that proves the change. For every pre-existing dirty file, record whether it is in scope and the observed status or diff evidence that it was not modified by this work.
6. Run diagnostics on changed files.
7. Run targeted tests, then broader checks if warranted. Run manual QA against the real deliverable surface: a live HTTP request for an API, a real CLI/TUI session, a real browser interaction, an import-and-use driver for a library, or the resulting artifact for data-shaped work.
8. When a required diagnostic, test, or real-surface check is unavailable, report the exact unverified area and why it is unavailable. Do not claim completion or approval until equivalent evidence is obtained or the blocker is explicitly handed off.
9. Return changed files, validation results, evidence, and any unverified area to the controller. The controller routes qualifying changes through `/omo-review` (2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs), or through its active `omo-review-loop` lanes without duplicating review.
10. Verify supplied findings against current code, tests, or a stated contract. Record unconfirmed findings as unconfirmed. A fix pass applies the confirmed scoped directives, validates them, and returns; it never dispatches another fix pass.
11. Further repair and re-review require the next iteration of the same Ralph ledger and budget. Report blocking findings and evidence to the controller; do not claim task completion before its independent final `APPROVE`.

## Hard Rules

- Do not use `as any`, `@ts-ignore`, or `@ts-expect-error` to suppress errors.
- Do not delete or weaken tests to pass.
- Do not add fallback or legacy paths unless required by an existing external contract.
- Do not modify unrelated dirty files.
- Do not treat review as advisory when a finding is confirmed and blocking.
- Do not claim a check passed unless you ran it in the current session.
- Report discovered work outside the assigned scope to the coordinator. Do not fix it until it is recorded, scoped, dependency-checked, and dispatched as required work.
