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
5. Record evidence for the diff: changed files, affected callers, and the validation target that proves the change.
6. Run diagnostics on changed files.
7. Run targeted tests, then broader checks if warranted.
8. Send changes through review when they touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs.
9. Fix confirmed review findings with minimal follow-up edits.
10. Re-run the relevant review and validation until no blocking findings remain, or until the same blocker survives one bounded retry round; then stop with the exact blocker.
11. Report changed files, review result, validation results, and any unverified area.

## Hard Rules

- Do not use `as any`, `@ts-ignore`, or `@ts-expect-error` to suppress errors.
- Do not delete or weaken tests to pass.
- Do not add fallback or legacy paths unless required by an existing external contract.
- Do not modify unrelated dirty files.
- Do not treat review as advisory when a finding is confirmed and blocking.
- Do not claim a check passed unless you ran it in the current session.
