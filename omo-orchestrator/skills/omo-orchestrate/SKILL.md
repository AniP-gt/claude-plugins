---
name: omo-orchestrate
description: OMO-inspired end-to-end orchestration for complex Claude Code work. Use for multi-step implementation, investigation, planning, review, or autonomous workflows.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Task, TodoWrite
user-invocable: true
---

# OMO Orchestrate

Use this skill to run work through an OMO-style loop: classify intent, gather context, plan, delegate to sub-agents, verify delegated results, and hand off clearly.

Strict main-context rule: the main context is an orchestrator only. It must not implement, edit, run task commands, perform direct investigation as the owner, or conduct direct review as the owner. All substantive work must be delegated to the appropriate sub-agent. The main context may only classify intent, create todos, read enough context to route and verify safely, dispatch sub-agents, synthesize their evidence, ask the user for missing decisions, and produce the final handoff.

Claude Code translation rule: when a runtime OMO feature depends on hooks, MCP servers, or hidden automation, convert it into an explicit manual step, evidence requirement, or handoff checkpoint.

## Flow

1. Classify the current request as question, investigation, implementation, review, planning, or open-ended cleanup.
2. Read only the project rules and evidence needed to route work and verify delegated results before making claims.
3. Create a file-level plan before editing when the work touches 2+ files, depends on caller/callee order or shared state, changes user-visible/API/CLI behavior, or needs 2+ validation checks.
4. Delegate implementation, investigation, review, validation commands, and fix work to sub-agents. Do not perform those work phases directly in the main context.
5. Split independent research or review into parallel agents when useful. Background agents are advisory, not blocking: wait for one bounded follow-up, then continue with available evidence if an agent stalls, returns no usable output, or repeats the same result.
6. Track state explicitly with todos or a handoff file.
7. For changes that touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs, run the full delegated loop: implement, review, fix confirmed blocking findings, then re-review.
8. Escalate hard or high-risk plans to `omo-hyperplan` before implementation.
9. For release work, run unpublished-change analysis and pre-publish review before any publish, merge, or handoff claim.
10. Use a PR-style final gate when the change is intended to be merged or shared: `APPROVE` exits, `REQUEST_CHANGES` feeds the next fix pass.
11. Require evidence in each phase: file paths, symbols, test names, diagnostics, command output, or direct code references.
12. Verify delegated diagnostics, tests, build checks, and manual QA evidence where applicable.
13. Finalize with changed files, review decision, validation performed, and any residual risks.

## Review Loop Policy

- Inner loop: delegate implementation, delegate review, synthesize findings, delegate fixes for confirmed blockers, and require affected checks.
- Outer gate: delegate review of the resulting diff for security, robustness, quality, and goal alignment.
- Evidence gate: a claim without a path, symbol, test, diagnostic, command result, or quoted code is not a review-grade finding.
- Stuck condition: if the same blocking issue survives one bounded retry round, stop and route to `omo-reviewer` for independent analysis. If the blocker depends on product judgment or external constraints, ask the user one precise question.
- Stalled delegation: do not spawn additional background agents while an existing wave is unresolved unless the new agent answers a distinct critical question. Mark missing results as stalled or blocked in the handoff and proceed with partial findings when safe.
- Do not treat a review pass as complete until blocking findings are resolved, disproven with evidence, or explicitly deferred by the user.

## Continuation Policy

- For iterative work, define a completion promise before looping.
- Keep an iteration ledger with current state, changed files, blockers, validation, and next exact action.
- Resume from the ledger or handoff before asking the user to restate context.
- Stop when the promise is satisfied, the same blocker survives one bounded retry round, an external side effect is required, or critical validation cannot be run.

Use [Workflow](references/workflow.md) when deciding whether a result should `APPROVE`, `REQUEST_CHANGES`, or escalate.

## Delegation Contract

Every delegated task should include:

- Task.
- Expected outcome.
- Required tools.
- Must do.
- Must not do.
- Context.

Ask for output that another operator can verify quickly: changed files, evidence, blockers, and next exact action.

## References

- [Workflow](references/workflow.md)
- [Handoff template](references/handoff-template.md)
