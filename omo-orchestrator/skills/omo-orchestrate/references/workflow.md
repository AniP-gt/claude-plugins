# OMO Workflow Mapping

This plugin adapts OMO concepts into portable Claude Code skills and agents.

| OMO concept | Plugin equivalent | Purpose |
|---|---|---|
| Sisyphus | `omo-coordinator` | Intent routing, delegation, verification, and completion checks |
| Prometheus | `omo-planner` | File-level implementation planning |
| Work planner | `omo-plan` | TL;DR, dependency matrix, QA scenarios, gap classification, and executable handoff |
| Hephaestus | `omo-implementer` | Minimal verified implementation |
| Explore / Librarian | `omo-researcher` | Read-only code and reference investigation |
| Implementation review loop | `omo-implement` + `omo-review` | Implement, review, fix, and re-review until blockers are resolved or the same blocker survives one bounded retry round |
| Review PR | `omo-review` | PR-style evidence-first review gate with `APPROVE` / `REQUEST_CHANGES` |
| Oracle / Momus | `omo-reviewer` | Independent reasoning, review, stuck-case escalation, and risk checks |
| Atlas | Handoff template | Explicit cross-agent state transfer |
| Hook-driven continuation | Handoff template + guardrails | Manual continuation checkpoint for context loss, stalled waves, or paused sessions |
| MCP-backed rules or diagnostics | Manual Claude Code checks | Read rules, inspect files, run diagnostics or tests when available |

## Core Principles

- Verify before claiming.
- Plan before multi-step implementation.
- Parallelize independent investigation and review.
- Keep background agents bounded: after one stalled or repeated result, record the gap and continue with available evidence when safe.
- Avoid duplicate work once a specialist owns a search area.
- Keep state explicit and portable.
- Prefer small verified changes over broad rewrites.
- Route blocking review findings back into implementation, then re-review within the bounded retry budget.
- Use final approval gates for mergeable or user-visible changes.

## Claude Code Translation Notes

- Treat the coordinator as the aggregator. It merges findings from planner, implementer, researcher, and reviewer instead of depending on runtime automation.
- Treat ultrawork as a prompt discipline: parallel only independent work, require evidence in each return, and bound follow-up when a delegated wave stalls.
- Treat continuation as durable text, not hidden memory. If work pauses, leave a handoff with blockers, validation, and next exact action.
- Treat rules, LSP, and comment checks as manual tool-driven steps. The plugin does not ship runtime enforcement.

## Decision Gate

- `APPROVE`: evidence supports the change, blocking findings are closed, and validation is either complete or any gaps are clearly non-blocking.
- `REQUEST_CHANGES`: a confirmed blocker remains, evidence is missing for a material risk, or required validation has not been run.
