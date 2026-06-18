---
name: omo-orchestrate
description: OMO-inspired end-to-end orchestration for complex Claude Code work. Use for multi-step implementation, investigation, planning, review, or autonomous workflows.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Task, TodoWrite, Bash
user-invocable: true
---

# OMO Orchestrate

Use this skill to run work through an OMO-style loop: classify intent, gather context, plan, delegate or execute, review, fix, verify, and hand off clearly.

## Flow

1. Classify the current request as question, investigation, implementation, review, planning, or open-ended cleanup.
2. Read relevant project rules and files before making claims.
3. Create a file-level plan before editing when the work touches 2+ files, depends on caller/callee order or shared state, changes user-visible/API/CLI behavior, or needs 2+ validation checks.
4. Split independent research or review into parallel agents when useful. Background agents are advisory, not blocking: wait for one bounded follow-up, then continue with available evidence if an agent stalls, returns no usable output, or repeats the same result.
5. Track state explicitly with todos or a handoff file.
6. For changes that touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs, run the full loop: implement, review, fix confirmed blocking findings, then re-review.
7. Use a PR-style final gate when the change is intended to be merged or shared: `APPROVE` exits, `REQUEST_CHANGES` feeds the next fix pass.
8. Verify with diagnostics, tests, build checks, and manual QA where applicable.
9. Finalize with changed files, review decision, validation performed, and any residual risks.

## Review Loop Policy

- Inner loop: implement, review, synthesize findings, fix confirmed blockers, and re-run affected checks.
- Outer gate: review the resulting diff for security, robustness, quality, and goal alignment.
- Stuck condition: if the same blocking issue survives one bounded retry round, stop and route to `omo-reviewer` for independent analysis. If the blocker depends on product judgment or external constraints, ask the user one precise question.
- Stalled delegation: do not spawn additional background agents while an existing wave is unresolved unless the new agent answers a distinct critical question. Mark missing results as stalled or blocked in the handoff and proceed with partial findings when safe.
- Do not treat a review pass as complete until blocking findings are resolved, disproven with evidence, or explicitly deferred by the user.

Use [Workflow](references/workflow.md) when deciding whether a result should `APPROVE`, `REQUEST_CHANGES`, or escalate.

## Delegation Contract

Every delegated task should include:

- Task.
- Expected outcome.
- Required tools.
- Must do.
- Must not do.
- Context.

## References

- [Workflow](references/workflow.md)
- [Handoff template](references/handoff-template.md)
