# Skill Catalog

Controllers choose the `LOAD_SKILLS` line of every delegation prompt from this table. A worker loads the dispatch's `LOAD_SKILLS` first, and may load another `worker` or `both` skill when its trigger appears.

## How to choose LOAD_SKILLS

- Gated workers: `omo-implementer`, `omo-researcher`, `omo-reviewer`, `omo-planner`. Every dispatch to one of them carries a `LOAD_SKILLS:` line, and the `hooks/load-skills-gate.mjs` PreToolUse hook denies a dispatch without it.
- On every dispatch to a gated worker, evaluate every row of the table against the task. Do not skim for the obvious one.
- Include a skill when in doubt. A skill that turns out unneeded costs a few lines of context; a missing one costs a wrong or unverified result.
- Write `LOAD_SKILLS: none` explicitly when no row applies. An absent line is a violation, `none` is an answer.
- Never name a `main-only` skill. Those are workflows the main context runs by itself; a worker cannot dispatch further workers. Use `worker` and `both` rows only.
- Skills preloaded by the agent definition's `skills:` field are already in the worker's context. Do not repeat them in `LOAD_SKILLS`: `omo-implementer` has `omo-guardrails` and `omo-programming`; `omo-reviewer` has `omo-guardrails`; `omo-researcher` has `omo-research`.
- Skills a read-only agent (`omo-researcher`, `omo-reviewer`, `omo-planner`) may load pre-approve no Bash, except that `omo-research` allows only `node "${CLAUDE_PLUGIN_ROOT}/scripts/impact.mjs"` (writes no files; the whole path sits before the pattern's first `*`) and `omo-ast-grep` allows the `ast-grep` CLI (whose `--update-all` rewrites files, the same reach as its Edit pre-approval). Rows marked `omo-implementer only` (`omo-programming`, `omo-frontend`, `omo-handoff`) pre-approve unrestricted Bash or a launcher, and a skill's `allowed-tools` grant applies inside the sub-agent that loads it, so the gate denies them in a `LOAD_SKILLS` sent to any worker other than `omo-implementer`. Read-only git needs no rule because Claude Code allows it without a prompt by default, and an explicit git rule would also allow `--output=<path>` file writes. A permission pattern is narrowed only by the text before its first `*` (https://code.claude.com/docs/en/permissions, Wildcard patterns), so never add an interpreter pattern such as `Bash(node *x*)`.
- Sub-agents already receive `CLAUDE.md`, so project rules need no `LOAD_SKILLS` entry.
- Format: `LOAD_SKILLS: [omo-test-design, omo-ast-grep]` or `LOAD_SKILLS: none`.
- Modes: a parent row lists its modes in the When cell. A mode is a procedure inside its parent skill (`skills/<parent>/modes/<mode>/MODE.md`), not a catalog row. The brackets of `LOAD_SKILLS` carry parent names only, never `<parent>/<mode>`.
- To request a mode, add a line of its own after `LOAD_SKILLS`, in this format: `MODES: <parent>/<mode>[, <parent>/<mode>]`. Example: `MODES: omo-research/security-research`.
- To request a mode of a parent the agent already has preloaded (for example `omo-programming` for `omo-implementer`), write the `MODES:` line and do not repeat the parent in `LOAD_SKILLS`. With nothing else to load, write `LOAD_SKILLS: none` plus the `MODES:` line.
- A `MODES:` line follows the same Who rules as `LOAD_SKILLS`: the parent of a `main-only` row or an `omo-implementer only` row is denied for a worker that may not load it. The `main-only` modes `ultraresearch` and `tech-debt-audit` of `omo-research` are not run by a worker; it returns the steps the caller must run.
- Workers also read a mode on its trigger without a `MODES:` line: when the task matches a mode's trigger words in the table and its agent definition lists that mode, the worker reads `modes/<mode>/MODE.md` itself. Name the mode in `MODES:` anyway when you know the task needs it.

## Who column

- `main-only`: the main context runs it as a workflow or entry point. Never put it in `LOAD_SKILLS`.
- `both`: the main context may run it as a workflow; a worker uses its method only when named in `LOAD_SKILLS`.
- `worker`: a method a worker may load; the main context may also load it.

## Catalog

| Skill | Who | When |
|---|---|---|
| `omo-ultrawork` | main-only | The user says ulw or ultrawork and wants plan, parallel waves, and real-surface verification. Modes: `ulw-execute` (ulw execute, run a written omo plan wave by wave), `mass-ulw` (mass ulw, mulw, fan-out where some tasks wait on others) |
| `omo-ralph-loop` | main-only | The user wants a goal loop or durable, checkpointed execution with bounded retries |
| `omo-orchestrate` | main-only | Complex multi-step work needs intent classification, routing, delegation, and a handoff |
| `omo-plan` | main-only | The user asks for a plan, or before the first edit of a change request or GitHub issue. Modes: `start-work` (kick off non-trivial work with context, plan, evidence targets, and handoff setup), `hyperplan` (hyperplan, hpp, adversarial plan for hard or high-risk work) |
| `omo-review` | main-only | Local changes need review: after editing 2+ files or before calling work done. Modes: `review-work` (final review gate for controllers returning APPROVE, REQUEST_CHANGES, or INCONCLUSIVE), `review-loop` (implement plus review fix loop with a final gate), `pre-publish-review` (pre-publish or release review) |
| `omo-implement` | main-only | A non-trivial change request needs exploration, a risk map, minimal edits, and test-first |
| `omo-work-with-pr` | main-only | A change is being prepared for a PR, or PR review threads need answers. Mode: `github-triage` (triage GitHub issues or PRs) |
| `omo-git-master` | main-only | A task needs a commit, rebase, squash, or a git-history answer (who wrote, when was X added) |
| `omo-init-deep` | main-only | The user asks to generate or maintain a hierarchical Claude Code rule set for a worktree |
| `omo-frontend` | both | `omo-implementer only` (unrestricted Bash): The task touches pages, components, styling, layout, motion, tokens, or themes |
| `omo-remove-ai-slop` | both | The task is to clean up AI-generated patterns in recent changes (deslop) |
| `omo-guardrails` | worker | Safety rules are needed beyond the preloaded set: anti-duplication, context guard, circuit breaker, error recovery (agents without preloaded guardrails, such as omo-researcher and omo-planner) |
| `omo-programming` | both | `omo-implementer only` (unrestricted Bash): the task edits `.py`, `.rs`, `.ts`, or `.go` files and the agent has no preloaded programming policy. Modes: `debugging` (crash, silent failure, hang, wrong response, memory leak, async misbehavior), `refactor` (refactor, simplify, extract, restructure, modernize), `remove-deadcode` (dead, unused, unreachable code) |
| `omo-test-design` | worker | A task needs tests and the cases are not obvious (several conditions, boundaries, or states) |
| `omo-visual-qa` | both | Any UI build or change, or a question whether a page, component, or TUI looks right, needs fresh visual evidence. Mode: `visualize` (build or create a chart, table, diagram, or HTML/SVG visualization) |
| `omo-ast-grep` | worker | The task searches by syntax shape or runs a codemod or YAML lint rule across files |
| `omo-research` | both | A question needs codebase structure, existing patterns, library references, or bug hypotheses before anything is decided. Modes: `ultraresearch` (exhaustive or saturation research, ulw research; main-only), `tech-debt-audit` (tech debt, debt audit, code health; main-only), `security-research` (security review, vulnerability research, exploitability, threat model), `coding-agent-sessions` (past sessions, transcripts, subagent runs), `get-unpublished-changes` (changes since the last release, unpublished changes, changelog) |
| `omo-handoff` | worker | `omo-implementer only` (launcher `Bash(orca:*)`): The task appends to the task-slug ledger or writes a brief to continue in a fresh session |
