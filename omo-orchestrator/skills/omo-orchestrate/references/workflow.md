# OMO Workflow Mapping

This plugin adapts OMO concepts into portable Claude Code skills and agents.

## Role map

| Component | Purpose |
|---|---|
| `omo-coordinator` | Intent routing, delegation, verification, and completion checks |
| `omo-planner` | File-level implementation planning |
| `omo-plan-consultant` | Read-only intent classification, exploration, affected-user ideal-state and gap analysis, and planning directives |
| `omo-plan-reviewer` | Read-only plan executability check with `OKAY` or `REJECT` |
| `omo-plan` | User-invoked only: TL;DR, dependency matrix, blocking executable QA scenarios, gap classification, and handoff inputs |
| `omo-hyperplan` | Adversarial planning for high-risk or ambiguous work before implementation |
| `omo-implementer` | Minimal verified implementation |
| `omo-researcher` | Read-only codebase investigation |
| `omo-librarian` | Read-only external library, upstream source, and dependency-history research with permalinks |
| `omo-implement` + `omo-review` | Implement, consume planned QA, review, fix, re-review, and final-verify within the bounded retry budget |
| `omo-review` | PR-style evidence-first review gate with `APPROVE` / `REQUEST_CHANGES` / `INCONCLUSIVE` |
| `omo-get-unpublished-changes` + `omo-pre-publish-review` | Diff-based release impact analysis and publish-readiness gate |
| `omo-work-with-pr` | Issue understanding, implementation, review response, validation, and handoff |
| `omo-security-research` | Exploitability-first security investigation and severity calibration |
| `omo-github-triage` | Evidence-first issue and PR classification, priority, and next action |
| `omo-remove-deadcode` | Reference-checked deletion workflow with zero-false-positive discipline |
| `omo-reviewer` | Independent change review with `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` |
| `omo-handoff` + handoff template | Manual task-slug-linked append-only ledger with explicit phase checkpoints |
| `omo-ralph-loop` + `omo-handoff` + guardrails | Completion promise, append-only phase ledger, and manual continuation checkpoint |
| Manual Claude Code checks | Rules and diagnostics: read rules, inspect files, run diagnostics or tests when available |

## Core Principles

- Verify before claiming.
- Plan before multi-step implementation.
- Before an approval brief, name affected users and record concrete `IS-*` ideal-state rows and `GAP-*` shortfalls. Every gap needs a closing task; every ideal-state row needs a delivering task, proving QA scenario, and evidence location.
- Parallelize independent investigation and review.
- Keep background agents bounded: after one stalled or repeated result, record the gap and continue with available evidence when safe.
- Avoid duplicate work once a specialist owns a search area.
- Keep state explicit and portable.
- Prefer small verified changes over broad rewrites.
- Route blocking review findings back into implementation, then re-review within the bounded retry budget.
- Use final approval gates for mergeable or user-visible changes.
- Treat release, PR, and security work as separate gates with stronger evidence requirements than ordinary implementation summaries.
- Make continuation visible through a ledger or handoff; hidden memory is not a valid state store.
- Use the manual ledger at `.claude/omo/handoffs/<task-slug>.md` for every multi-phase task. Before an edit or dependent delegation, check the original user request and constraints, predecessor artifacts, executable QA scenarios, and validation evidence. Delegate ledger creation and append operations to `omo-handoff` or another writable owner, then read and verify the resulting entry.
- Append reports after research or exploration, planning, implementation, validation, review or fix, and final verification where applicable. Use the `omo-handoff` entry fields: timestamp, task slug, phase, owner, dependency status, files or artifacts, findings or changes, validation command and result, QA evidence location, retry details, final-gate state, blockers, and one next exact action.
- Consume executable QA scenarios from the approved plan during implementation and final verification. Preserve the tool, steps, assertion, and evidence location for each executed scenario.
- Use `omo-plan-reviewer` for bounded plan executability review. It approves with `OKAY` unless verified blockers require `REJECT`; it does not replace `omo-reviewer` or its implementation-review lifecycle.
- Keep failed evidence. Invalidate validation evidence only when a changed prerequisite actually affects it.
- Use one initial attempt plus at most two materially different retries. Valid changes include revisiting a dependency, reducing the change surface, using a different validation target, or consulting an independent reviewer. An unchanged command rerun is not a new approach.
- Before claiming completion, re-read the original user request and constraints. After the retry budget is exhausted, record attempts and the blocker, then stop without claiming success.

## Claude Code Translation Notes

- Treat the coordinator as the aggregator. It merges findings from planner, implementer, researcher, and reviewer instead of depending on runtime automation.
- Treat ultrawork as a prompt discipline: parallel only independent work, require evidence in each return, and bound follow-up when a delegated wave stalls.
- Treat continuation as a durable task-slug-linked append-only ledger, not hidden memory. If work pauses, delegate the append to `omo-handoff` or another writable owner, then verify blockers, validation, and one next exact action before another operator continues.
- Treat runtime loops as manual promises: define the completion condition, run bounded iterations, and stop on repeated blockers or missing approval.
- Treat rules, LSP, and comment checks as manual tool-driven steps. The plugin does not ship runtime enforcement.

## Decision Gate

- `APPROVE`: the sole completion state. Evidence supports the change, blocking findings are closed, and validation is either complete or any gaps are clearly non-blocking.
- `REQUEST_CHANGES`: a confirmed blocker remains or required validation has not been run. It blocks completion and requires a targeted fix, affected validation, and re-review.
- `INCONCLUSIVE`: required evidence is missing, unavailable, or untrustworthy. It blocks completion until the evidence gap or needed decision is resolved.
