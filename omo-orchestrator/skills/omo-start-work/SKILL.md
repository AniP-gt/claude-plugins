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
2. Confirm either an approved, decision-complete plan or a bounded task with a clear outcome, scope, owner, and validation target. Do not treat plan approval as permission to edit until this kickoff contract is complete.
3. Gather local context: likely files, existing patterns, related tests, and project rules.
4. Identify missing facts that must be resolved before editing.
5. Define evidence targets for completion, such as tests, diagnostics, build checks, or manual QA. Record the goal, non-goals, evidence targets, risks, shared-file owners, and dependency waves.
6. Require a behavior assertion before an edit: identify an existing characterization, a failing proof, or another concrete expected-behavior check that the change must preserve or satisfy.
7. Create an executable plan with atomic steps and clear dependencies. When `TodoWrite` is available, materialize the steps as atomic items and keep exactly one item active at a time under this manual local contract.
8. Serialize same-file writes, shared contracts, mutable state, and named predecessors. Parallelize only independent tasks with distinct owners and no shared-file conflict.
9. Set up the task-linked append-only ledger at `.claude/omo/handoffs/<task-slug>.md` for every active task. Append a kickoff checkpoint before dispatch that records the approved plan or bounded task, scope, non-goals, owners, dependencies, evidence targets, risks, and first exact action.
10. For iterative work, write the completion promise and first iteration state before starting the loop.
11. For release or PR work, identify the baseline, publish target, branch state, and approval gates before editing.

## Manual State Synchronization

This is a manual, content-only contract. Manual `TodoWrite` state and the latest entry in the append-only handoff ledger are synchronized views of the same work state. They do not synchronize through hooks, hidden memory, automatic resume, a team engine, or another runtime service.

1. For each active task, maintain one current TodoWrite item and one corresponding ledger phase state. Both must name the same owner, dependency status, completion criteria or final-gate state, and one next exact action.
2. Before dispatch, handoff, retry, review, and completion, compare the current TodoWrite state with the latest ledger entry. Do not proceed across that boundary until they agree.
3. If the views disagree, update the current TodoWrite item and append a corrective ledger entry that identifies the correction. Never replace, delete, reorder, or rewrite earlier ledger history.
4. Preserve failed attempts, blockers, retry details, validation results, and evidence locations in later ledger entries. Use `omo-handoff` for the required entry fields and append-only record rules.
5. Before a later operator manually continues after a context or owner change, read the full ledger, reconcile it with the current TodoWrite state, and take the recorded next exact action or append a corrected one.
6. Block completion until TodoWrite and the latest ledger entry both show the same satisfied completion criteria and final gate. Where a review gate applies, only `APPROVE` permits completion; `REQUEST_CHANGES` and `INCONCLUSIVE` require another recorded next action.

## Evidence Targets

- Changed files.
- Validation commands or diagnostics to run.
- Review gate, if the task changes public behavior, data flow, or security-sensitive code.
- Explicit blockers and the single question each blocker would require.
- Completion promise and iteration state when looped work is expected.
- Release or PR gate when publish, merge, or review handoff is part of done.

## Hard Rules

- Do not start editing before the scope and validation target are clear enough.
- Do not confuse open questions with blockers unless they change the implementation path.
- Do not leave the next agent guessing about what done looks like.
