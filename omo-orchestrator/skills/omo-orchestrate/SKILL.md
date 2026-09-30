---
name: omo-orchestrate
description: OMO-inspired manual orchestration for complex Claude Code work. Use for multi-step implementation, investigation, planning, or review.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Task, TodoWrite
user-invocable: true
---

# OMO Orchestrate

Use this skill to coordinate an OMO-style workflow: classify intent, gather routing context, plan, delegate when available, verify returned evidence, and hand off clearly. It is prompt guidance, not an autonomous runtime.

Strict main-context rule: the main context is an orchestrator only. It must not implement, edit, run task commands, perform direct investigation as the owner, or conduct direct review as the owner. All substantive work must be delegated to the appropriate sub-agent. The main context may only classify intent, create todos, read enough context to route and verify safely, dispatch sub-agents, synthesize their evidence, ask the user for missing decisions, and produce the final handoff.

When a step would need hooks, MCP servers, or background automation this session does not provide, turn it into an explicit manual step, evidence requirement, or handoff checkpoint.

Delegation boundary: use `Task` only when a suitable sub-agent and required tools are available. If delegation is unavailable, returns no usable evidence after its bounded follow-up, or cannot safely own the phase, record the gap, owner, and one next action in the handoff. Stop when that missing work is critical; otherwise synthesize only the available evidence. Never simulate a delegated result or continue automatically.

## Flow

1. Classify the current request as question, investigation, implementation, review, planning, or open-ended cleanup. For planning, classify the desired outcome as `CLEAR` or `UNCLEAR` and route to `omo-plan-consultant` and `omo-planner` before implementation; use `omo-plan` only when the user explicitly asks for a plan. Use [Routing](references/routing.md) for the intent map, ambiguity thresholds (ask when readings differ 2x+ in effort), codebase assessment, and delegation matrix.
2. Read only the project rules and evidence needed to route work and verify delegated results before making claims.
3. Create a file-level plan before editing when the work touches 2+ files, depends on caller/callee order or shared state, changes user-visible/API/CLI behavior, or needs 2+ validation checks.
4. Delegate implementation, investigation, review, validation commands, and fix work to sub-agents. Do not perform those work phases directly in the main context.
5. Split independent research or review into parallel agents when useful. Dependency-aware parallelism is mandatory: independent files and questions may fan out, while shared mutable state, same-file writes, shared contracts, and named predecessors serialize. Background agents are advisory, not blocking: wait for one bounded follow-up, then record an unavailable result and follow the delegation boundary if an agent stalls, returns no usable output, or repeats the same result.
6. For multi-phase work, delegate `omo-handoff` or another writable owner to create or locate the task-slug-linked append-only ledger at `.claude/omo/handoffs/<task-slug>.md`, then read and verify the full ledger before routing or resuming work.
7. Before delegating an edit, require a dependency check for the original request and constraints, predecessor artifacts, executable QA scenarios, and existing validation evidence. Delegate the ledger append to `omo-handoff` or another writable owner, then read and verify the appended findings and state before delegating dependent work.
8. Require an appended phase report after research or exploration, planning, implementation, validation, review or fix, and final verification where those phases apply. Delegate each append to `omo-handoff` or another writable owner, then read and verify the result. Each report must name dependencies, evidence, blockers, retries, and one next exact action.
   Use the `omo-handoff` entry fields: timestamp, task slug, phase, owner, dependency status, files or artifacts, findings or changes, validation command and result, QA evidence location, retry details, final-gate state, blockers, and one next exact action.
9. For changes that touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs, run the full delegated loop: implement, validate with the plan's executable QA scenarios, review, fix confirmed blocking findings, then re-review and perform final verification.
10. Require implementers to use QA scenarios from the approved plan during implementation and final verification. The ledger must preserve the tool, exact steps, assertion, and evidence location for every executed scenario.
11. Escalate hard or high-risk plans to `omo-hyperplan` before implementation.
12. For release work, run unpublished-change analysis and pre-publish review before any publish, merge, or handoff claim.
13. Use a PR-style final gate when the change is intended to be merged or shared: only `APPROVE` permits completion. `REQUEST_CHANGES` feeds the next fix pass, and `INCONCLUSIVE` blocks completion until its evidence gap or decision is resolved.
14. Require evidence in each phase: file paths, symbols, test names, diagnostics, command output, or direct code references.
15. Verify delegated diagnostics, tests, build checks, and manual QA evidence where applicable.
16. Before accepting completion, require a re-read of the original user request and constraints, then finalize with changed files, review decision, validation performed, and residual risks. Report pre-existing failures unrelated to the change separately instead of fixing them unasked.

## Discovered Work

- A worker reports defects, stale guidance, failing tests, or missing docs outside its assigned scope instead of changing them opportunistically.
- The coordinator records the discovery in the ledger, decides whether it is necessary for the requested outcome, and adds a scoped task with dependencies and QA before dispatching it.
- Do not silently defer required discovered work or silently expand the request with unrelated cleanup. Record either decision and its reason.

## Review Loop Policy

- Inner loop: delegate implementation, delegate review, synthesize findings, delegate fixes for confirmed blockers, and require affected checks.
- Outer gate: delegate review of the resulting diff for security, robustness, quality, and goal alignment.
- Evidence gate: a claim without a path, symbol, test, diagnostic, command result, or quoted code is not a review-grade finding.
- Retry budget: allow one initial attempt plus at most two materially different retries. A different retry revisits a dependency, reduces the change surface, uses a different validation target, or consults an independent reviewer. Re-running an unchanged command does not count as a new approach.
- Evidence preservation: retain failed attempts in the ledger. Invalidate validation evidence only when an edit changes the prerequisite on which that evidence depends, and record the invalidated dependency.
- Stuck condition: after the retry budget is exhausted, stop further edits, have the owner revert to the last known working state, append every attempt and the blocker, stop honestly, and do not claim success. Never leave code broken or delete failing tests to pass. Consult `omo-oracle` with the full failure context for hard debugging. Delegate to `omo-reviewer` only when available and able to answer the blocker. If no suitable delegation is available, record that boundary. If the blocker depends on product judgment or external constraints, ask the user one precise question.
- Stalled delegation: do not spawn additional background agents while an existing wave is unresolved unless the new agent answers a distinct critical question. Mark missing results as stalled or blocked in the handoff and proceed with partial findings when safe.
- Do not treat a review pass as complete until blocking findings are resolved, disproven with evidence, or explicitly deferred by the user. Only `APPROVE` permits completion. `REQUEST_CHANGES` and `INCONCLUSIVE` block it.

## Continuation Policy

- For iterative work, define a completion promise before looping.
- Keep the task-slug-linked append-only ledger with current state, changed files, blockers, validation, and next exact action.
- Resume from the ledger or handoff before asking the user to restate context.
- Stop when the promise is satisfied, the retry budget is exhausted, an external side effect is required, or critical validation cannot be run.

Use [Workflow](references/workflow.md) when deciding whether a result should `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`.

## Delegation Contract

Every delegated task should include:

- Task.
- Expected outcome.
- Required tools.
- Must do.
- Must not do.
- Context.

Use the full template, state-passing rule, and auto-continue policy in [Delegation prompt](references/delegation-prompt.md). After a verified step passes, dispatch the next ready step without asking the user to continue.

Ask for output that another operator can verify quickly: changed files, evidence, blockers, and next exact action.

## References

- [Routing](references/routing.md)
- [Delegation prompt](references/delegation-prompt.md)
- [Workflow](references/workflow.md)
- [Handoff template](references/handoff-template.md)
