---
name: omo-work-with-pr
description: "OMO PR lifecycle workflow: understand the issue, isolate work, implement with gates, review, update the PR, and verify checks."
argument-hint: [pr-or-issue]
allowed-tools: Read, Grep, Glob, Bash, TodoWrite, Task
user-invocable: true
---

# OMO Work With PR

Use this skill for end-to-end PR work: preparing changes, responding to review, or bringing an existing PR to a mergeable state.

## Flow

1. Identify the PR or issue goal, acceptance criteria, and non-goals.
2. Inspect current branch state before editing.
3. Build or update a file-level plan.
4. Implement the smallest safe change and keep commits or change clusters reviewable.
5. Run targeted validation, then wider checks when the change warrants it.
6. Run PR-style review for goal alignment, security, robustness, quality, tests, and scope control.
7. Feed confirmed blockers into a fix pass and re-run affected checks.
8. Prepare the PR summary with what changed, why, validation, and residual risks.

## Hard Rules

- Do not mix unrelated fixes into a PR lifecycle task.
- Do not call a PR ready while blocking review findings or required checks remain unresolved.
- Do not rewrite history, push, or publish unless the user explicitly asks.
- Do not answer review feedback without checking the code or diff that triggered it.

## Output Contract

- PR or issue objective.
- Changed files or planned files.
- Review decision.
- Validation run.
- Remaining blockers.
- Suggested PR summary or response.
