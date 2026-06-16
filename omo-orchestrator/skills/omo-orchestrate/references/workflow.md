# OMO Workflow Mapping

This plugin adapts OMO concepts into portable Claude Code skills and agents.

| OMO concept | Plugin equivalent | Purpose |
|---|---|---|
| Sisyphus | `omo-coordinator` | Intent routing, delegation, verification, and completion checks |
| Prometheus | `omo-planner` | File-level implementation planning |
| Work planner | `omo-plan` | TL;DR, dependency matrix, QA scenarios, gap classification, and executable handoff |
| Hephaestus | `omo-implementer` | Minimal verified implementation |
| Explore / Librarian | `omo-researcher` | Read-only code and reference investigation |
| Implementation review loop | `omo-implement` + `omo-review` | Implement, review, fix, and re-review until blockers are resolved |
| Review PR | `omo-review` | PR-style evidence-first review gate with `APPROVE` / `REQUEST_CHANGES` |
| Oracle / Momus | `omo-reviewer` | Independent reasoning, review, stuck-case escalation, and risk checks |
| Atlas | Handoff template | Explicit cross-agent state transfer |

## Core Principles

- Verify before claiming.
- Plan before multi-step implementation.
- Parallelize independent investigation and review.
- Avoid duplicate work once a specialist owns a search area.
- Keep state explicit and portable.
- Prefer small verified changes over broad rewrites.
- Route blocking review findings back into implementation, then re-review.
- Use final approval gates for mergeable or user-visible changes.
