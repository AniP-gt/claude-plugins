# Skill Catalog

Controllers choose the `LOAD_SKILLS` line of every delegation prompt from this table. A worker loads the dispatch's `LOAD_SKILLS` first, and may load another `worker` or `both` skill when its trigger appears.

## How to choose LOAD_SKILLS

- Gated workers: `omo-implementer`, `omo-researcher`, `omo-reviewer`, `omo-planner`. Every dispatch to one of them carries a `LOAD_SKILLS:` line, and the `hooks/load-skills-gate.mjs` PreToolUse hook denies a dispatch without it.
- On every dispatch to a gated worker, evaluate every row of the table against the task. Do not skim for the obvious one.
- Include a skill when in doubt. A skill that turns out unneeded costs a few lines of context; a missing one costs a wrong or unverified result.
- Write `LOAD_SKILLS: none` explicitly when no row applies. An absent line is a violation, `none` is an answer.
- Never name a `main-only` skill. Those are workflows the main context runs by itself; a worker cannot dispatch further workers. Use `worker` and `both` rows only.
- Skills preloaded by the agent definition's `skills:` field are already in the worker's context. Do not repeat them in `LOAD_SKILLS`: `omo-implementer` has `omo-guardrails` and `omo-programming`; `omo-reviewer` has `omo-guardrails`; `omo-researcher` has `omo-research`.
- Skills a read-only agent (`omo-researcher`, `omo-reviewer`, `omo-planner`) may load pre-approve no Bash, except that `omo-research` allows only `node "${CLAUDE_PLUGIN_ROOT}/scripts/impact.mjs"` (writes no files; the whole path sits before the pattern's first `*`) and `omo-ast-grep` allows the `ast-grep` CLI (whose `--update-all` rewrites files, the same reach as its Edit pre-approval). Rows marked `omo-implementer only` (`omo-programming`, `omo-debugging`, `omo-refactor`, `omo-frontend`, `omo-remove-deadcode`, `omo-handoff`) pre-approve unrestricted Bash or a launcher, and a skill's `allowed-tools` grant applies inside the sub-agent that loads it, so the gate denies them in a `LOAD_SKILLS` sent to any worker other than `omo-implementer`. Read-only git needs no rule because Claude Code allows it without a prompt by default, and an explicit git rule would also allow `--output=<path>` file writes. A permission pattern is narrowed only by the text before its first `*` (https://code.claude.com/docs/en/permissions, Wildcard patterns), so never add an interpreter pattern such as `Bash(node *x*)`.
- Sub-agents already receive `CLAUDE.md`, so project rules need no `LOAD_SKILLS` entry.
- Format: `LOAD_SKILLS: [omo-test-design, omo-ast-grep]` or `LOAD_SKILLS: none`.

## Who column

- `main-only`: the main context runs it as a workflow or entry point. Never put it in `LOAD_SKILLS`.
- `both`: the main context may run it as a workflow; a worker uses its method only when named in `LOAD_SKILLS`.
- `worker`: a method a worker may load; the main context may also load it.

## Catalog

| Skill | Who | When |
|---|---|---|
| `omo-ultrawork` | main-only | The user says ulw or ultrawork and wants plan, parallel waves, and real-surface verification |
| `omo-ulw-execute` | main-only | The user says ulw execute or asks to run a written omo plan wave by wave |
| `omo-mass-ulw` | main-only | The user says mass ulw / mulw or asks for fan-out work where some tasks wait on others |
| `omo-review-loop` | main-only | The user wants implement plus review with a fix loop and a final gate |
| `omo-ralph-loop` | main-only | The user wants a goal loop or durable, checkpointed execution with bounded retries |
| `omo-orchestrate` | main-only | Complex multi-step work needs intent classification, routing, delegation, and a handoff |
| `omo-plan` | main-only | The user asks for a plan, or before the first edit of a change request or GitHub issue |
| `omo-hyperplan` | main-only | The user says hyperplan or hpp, or hard, high-risk work needs an adversarial plan |
| `omo-review` | main-only | Local changes need review: after editing 2+ files or before calling work done |
| `omo-review-work` | main-only | A controller needs the final review gate returning APPROVE, REQUEST_CHANGES, or INCONCLUSIVE |
| `omo-start-work` | main-only | Non-trivial work needs a kickoff with context, plan, evidence targets, and handoff setup |
| `omo-pre-publish-review` | main-only | The user explicitly asks for a pre-publish or release review |
| `omo-implement` | main-only | A non-trivial change request needs exploration, a risk map, minimal edits, and test-first |
| `omo-work-with-pr` | main-only | A change is being prepared for a PR, or PR review threads need answers |
| `omo-git-master` | main-only | A task needs a commit, rebase, squash, or a git-history answer (who wrote, when was X added) |
| `omo-github-triage` | main-only | The user asks to triage GitHub issues or PRs |
| `omo-init-deep` | main-only | The user asks to generate or maintain a hierarchical Claude Code rule set for a worktree |
| `omo-lsp-setup` | main-only | A project needs a language server, or a "no LSP server configured" error appears |
| `omo-ultraresearch` | main-only | The user asks for exhaustive or saturation research on a decision-critical question |
| `omo-tech-debt-audit` | main-only | The user asks about tech debt, a debt audit, or code health |
| `omo-debugging` | both | `omo-implementer only` (unrestricted Bash): A crash, silent failure, hang, wrong response, memory leak, or async misbehavior needs a root cause |
| `omo-refactor` | both | `omo-implementer only` (unrestricted Bash): The task is to refactor, simplify, extract, restructure, or modernize code without changing behavior |
| `omo-frontend` | both | `omo-implementer only` (unrestricted Bash): The task touches pages, components, styling, layout, motion, tokens, or themes |
| `omo-remove-deadcode` | both | `omo-implementer only` (unrestricted Bash): The task is to remove dead, unused, or unreachable code |
| `omo-remove-ai-slop` | both | The task is to clean up AI-generated patterns in recent changes (deslop) |
| `omo-security-research` | both | The task is a security review, vulnerability research, exploitability audit, or threat model validation |
| `omo-visualize` | both | The task builds a standalone HTML or SVG chart, table, or diagram, or one inside an existing UI |
| `omo-guardrails` | worker | Safety rules are needed beyond the preloaded set: anti-duplication, context guard, circuit breaker, error recovery (agents without preloaded guardrails, such as omo-researcher and omo-planner) |
| `omo-programming` | worker | `omo-implementer only` (unrestricted Bash): the task edits `.py`, `.rs`, `.ts`, or `.go` files and the agent has no preloaded programming policy |
| `omo-test-design` | worker | A task needs tests and the cases are not obvious (several conditions, boundaries, or states) |
| `omo-visual-qa` | worker | Any UI build or change, or a question whether a page, component, or TUI looks right, needs fresh visual evidence |
| `omo-ast-grep` | worker | The task searches by syntax shape or runs a codemod or YAML lint rule across files |
| `omo-research` | worker | A question needs codebase structure, existing patterns, library references, or bug hypotheses before anything is decided |
| `omo-coding-agent-sessions` | worker | The task needs to find or search past coding-agent sessions, transcripts, or subagent runs |
| `omo-get-unpublished-changes` | worker | The task needs what changed since the last release, unpublished changes classified by risk, or a changelog |
| `omo-handoff` | worker | `omo-implementer only` (launcher `Bash(orca:*)`): The task appends to the task-slug ledger or writes a brief to continue in a fresh session |
