---
name: omo-implement
description: Execute a code change with exploration first, a risk map for existing code, minimal edits, and test-first when needed. Use proactively for any non-trivial change request.
argument-hint: [task]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task, Skill
user-invocable: true
---

# OMO Implement

Use this skill for one scoped implementation or fix pass after scope is concrete. When delegated, return the result to the caller's active Ralph controller; do not start another controller or review loop. When invoked standalone and not escalated to ultrawork (below), initialize or reuse `omo-ralph-loop` for this task and return any review findings to that controller for the next pass.

Ultrawork escalation: when invoked standalone, size the task first and decide whether to enter ultrawork by the `omo-ultrawork` skill's `references/auto-escalation.md`. Skip the check when an active controller delegated this skill.

## Steps

1. Read the relevant code and nearby patterns. When the task comes from an older issue or one phase of a staged plan, first check that its premise still holds: another change already did it, the framework's default behavior already covers it (a queue that requeues on graceful stop), or a cheaper means exists. If any holds, report it with evidence and ask before implementing.
2. Confirm the smallest behavior change that satisfies the request. When it modifies existing code, build the risk map described in `/omo-review` (Review Areas, risk map) before editing, as a short list with one line per modified unit: visible callers with the search used, hidden reach for each `/omo-review` category (found, none, or could not verify; within that unit's line, the categories marked none may be grouped in one phrase), its guardrail, and business impact. Treat rows with business impact and no guardrail as places that need a test or an explicit check. For each risk, say whether it already exists or this change introduces it, and its trigger and frequency (every deploy, only on crash). When the change targets a failure path (a crash, OOM, timeout), also state its effect on the routine path (normal deploys, restarts, daytime traffic) before editing; a lock that is now reclaimed only after a TTL can stall a latency-sensitive job on every deploy. Evaluate it both on the current code and after any change already planned for the same path (a cleanup hook another issue will remove), and say which of the two each effect belongs to.
3. Decide test necessity from the change scale. Tests are required when the change adds or changes branching logic, a calculation, a state transition, a data write, parsing or validation, a public contract, or fixes a bug (the regression test must fail without the fix). When tests are required, work test-first: write the test, run it, confirm it fails for the expected reason, then implement until it passes. When tests are not required (wording, including only the text of an existing message, docs, renames, config values, wiring that adds no branch; a rename or text change needs a test only when an in-repo consumer matches on the old name or text (a lookup by string, a caller comparing an error message); an outside consumer that could not be verified is reported as unverified, not a reason to add a test), skip TDD and name the diagnostic or real-surface check that proves the change instead.
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
- When a new small type or helper exists only to satisfy another component's interface (a placeholder passed instead of a record, an adapter), give it a short comment saying why it exists and naming one caller; its own file does not show how to use it.
- Do not state a lock hold time, run time, or failure-path outcome in comments, docs, or the change description unless a measurement or test backs it; otherwise label it an estimate.
- Do not treat review as advisory when a finding is confirmed and blocking.
- Do not claim a check passed unless you ran it in the current session.
- Report discovered work outside the assigned scope to the coordinator. Do not fix it until it is recorded, scoped, dependency-checked, and dispatched as required work.
