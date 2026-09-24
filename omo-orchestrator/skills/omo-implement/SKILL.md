---
name: omo-implement
description: Execute a planned change with exploration first, minimal edits, review-fix iteration, TDD-oriented validation, and no speculative compatibility paths.
argument-hint: [task]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Implement

Use this skill for implementation after scope is concrete.

## Steps

1. Read the relevant code and nearby patterns.
2. Confirm the smallest behavior change that satisfies the request.
3. Add or identify a failing test or validation target when appropriate.
4. Edit only the required files.
5. Record evidence for the diff: changed files, affected callers, and the validation target that proves the change. For every pre-existing dirty file, record whether it is in scope and the observed status or diff evidence that it was not modified by this work.
6. Run diagnostics on changed files.
7. Run targeted tests, then broader checks if warranted. Run manual QA against the real deliverable surface: a live HTTP request for an API, a real CLI/TUI session, a real browser interaction, an import-and-use driver for a library, or the resulting artifact for data-shaped work.
8. When a required diagnostic, test, or real-surface check is unavailable, report the exact unverified area and why it is unavailable. Do not claim completion or approval until equivalent evidence is obtained or the blocker is explicitly handed off.
9. Route qualifying changes through `/omo-review` when they touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs.
10. Verify each review finding against current code, tests, or a stated contract. Record unconfirmed findings as unconfirmed and do not fix them as facts. Fix confirmed blocking findings with minimal follow-up edits.
11. After a fix, rerun the affected validation and `/omo-review` once. If the same confirmed blocker remains, stop with the exact blocker, its evidence, and the next manual decision or action.
12. Report changed files, review result, validation results, and any unverified area.

## Hard Rules

- Do not use `as any`, `@ts-ignore`, or `@ts-expect-error` to suppress errors.
- Do not delete or weaken tests to pass.
- Do not add fallback or legacy paths unless required by an existing external contract.
- Do not modify unrelated dirty files.
- Do not treat review as advisory when a finding is confirmed and blocking.
- Do not claim a check passed unless you ran it in the current session.
- Report discovered work outside the assigned scope to the coordinator. Do not fix it until it is recorded, scoped, dependency-checked, and dispatched as required work.
