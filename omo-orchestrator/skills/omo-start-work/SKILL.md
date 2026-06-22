---
name: omo-start-work
description: Kick off non-trivial work with context gathering, plan creation, evidence targets, risk checks, and handoff setup.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Write, TodoWrite
user-invocable: true
---

# OMO Start Work

Use this skill at the start of non-trivial work, especially when the task spans multiple files, has unclear dependencies, or may need handoff.

## Kickoff Workflow

1. Restate the goal, constraints, and non-goals.
2. Gather local context: likely files, existing patterns, related tests, and project rules.
3. Identify missing facts that must be resolved before editing.
4. Define evidence targets for completion, such as tests, diagnostics, build checks, or manual QA.
5. Create an executable plan with atomic steps and clear dependencies.
6. Mark safe parallel work only when the steps do not share state.
7. Set up a short handoff note if the task is likely to outlive the current session.
8. For iterative work, write the completion promise and first iteration state before starting the loop.
9. For release or PR work, identify the baseline, publish target, branch state, and approval gates before editing.

## Evidence Targets

- Changed files.
- Validation commands or diagnostics to run.
- Review gate, if the task changes public behavior, data flow, or security-sensitive code.
- Explicit blockers and the single question each blocker would require.
- Completion promise and iteration ledger when looped work is expected.
- Release or PR gate when publish, merge, or review handoff is part of done.

## Hard Rules

- Do not start editing before the scope and validation target are clear enough.
- Do not confuse open questions with blockers unless they change the implementation path.
- Do not leave the next agent guessing about what done looks like.
