# omo-orchestrate (shared references, not a skill)

This directory has no `SKILL.md`, so Claude Code does not load it as a skill. Version 4.0.0 removed the `omo-orchestrate` entry skill: no hook or skill routed work to it, and the hooks already send each request to a specific entry (`omo-plan`, `omo-review`, `omo-ultrawork`, `omo-work-with-pr`).

The files under `references/` stay here because other skills and hooks read them by this path:

- `skill-catalog.md`: the `LOAD_SKILLS` catalog (read by `hooks/load-skills-gate.mjs` and every controller).
- `delegation-prompt.md`: the delegation prompt template and the pending delivery and late results contract.
- `codex-implementer.md`, `codex-consult.md`: the Codex implementation lane and the read-only Codex consults.
- `routing.md`: intent routing map and codebase assessment.
- `handoff-template.md`: the ledger template used by `omo-handoff`.
- `project-rules.md`: other agents' rule files and how to pass them into delegation prompts.
