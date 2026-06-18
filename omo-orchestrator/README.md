# omo-orchestrator

OMO-inspired Claude Code orchestration plugin. It packages portable skills and agents for intent routing, file-level planning, TDD-oriented implementation, parallel research, review gates, safety guardrails, and focused specialist workflows.

This plugin is content-only. It does not install scripts, hooks, MCP servers, provider routing, token storage, package manifests, or OpenCode runtime internals.

## Install

```text
/plugin marketplace add AniP-gt/claude-plugins
/plugin install omo-orchestrator@hidetsugu-miya
```

Restart Claude Code after installation.

## Included Skills

- `omo-orchestrate`: main workflow for complex multi-step work.
- `omo-plan`: file-level planning with dependency matrix, QA scenarios, blockers, and verification commands.
- `omo-implement`: autonomous implementation loop with exploration, minimal edits, review-fix iteration, and validation.
- `omo-research`: read-only local/codebase research workflow.
- `omo-review`: PR-style security, robustness, quality, goal-alignment, and test-coverage review gate.
- `omo-guardrails`: context, duplication, circuit-breaker, error-recovery, and handoff safety rules.

## Specialized Skills

These are LazyCodex-inspired Claude Code translations. They are content-only prompts, not runtime hooks or automation.

- `omo-programming`: implementation policy for type safety, minimal diffs, tests, diagnostics, and honest validation.
- `omo-start-work`: kickoff workflow for non-trivial tasks, context gathering, plans, evidence targets, and handoff setup.
- `omo-ultrawork`: high-throughput parallel work mode with independent waves, bounded follow-up, evidence ledger, and manual QA gate.
- `omo-review-work`: post-implementation review gate with multi-angle findings and `PASS`, `FAIL`, or `INCONCLUSIVE`.
- `omo-debugging`: hypothesis-driven debugging with reproduction first, root cause proof, failing validation, minimal fix, and verification.
- `omo-refactor`: safe refactoring with behavior lock first, caller and callee inventory, small steps, and drift checks.
- `omo-remove-ai-slop`: regression-first cleanup for AI-generated comments, complexity, duplication, and weak abstractions.
- `omo-ultraresearch`: exhaustive read-only research mode with source matrix, evidence thresholds, non-goals, and stop conditions.

## Included Agents

- `omo-coordinator`: intent routing, delegation, state tracking, and completion checks. Not pinned to Haiku because orchestration quality is high leverage.
- `omo-planner`: executable plans, blocker discovery, and plan review. Not pinned to Haiku because planning quality is high leverage.
- `omo-implementer`: deep executor for minimal verified changes.
- `omo-researcher`: read-only code and reference investigator. Uses `model: haiku`.
- `omo-reviewer`: independent reviewer for risk, quality, and scope control.

## Model Guidance

Agent model hints are enforced through agent frontmatter where Claude Code supports it. Skills are prompt content, so their model guidance is advisory unless a caller chooses the model explicitly.

Haiku is appropriate for low-risk, mechanical work: read-only code investigation, simple git or CLI operations, metadata checks, and narrow documentation lookups. It is not the default for planning, orchestration, implementation, or skeptical review.

Haiku is sufficient for routine use of these prompt-only skills when the task is narrow and evidence-based:

- `omo-guardrails`
- `omo-programming`
- `omo-research`
- `omo-start-work`
- `omo-ultraresearch`

Use a stronger model for orchestration, planning, high-risk implementation, skeptical review, hard debugging, broad refactors, or ambiguous product decisions.

## Claude Code Adaptation Scope

This plugin adapts useful LazyCodex OMO ideas into Claude Code prompts only. It keeps the OMO shape, but translates runtime-driven behavior into manual skill and agent behavior that works in a local Claude Code session.

Examples:

- Aggregator model -> `omo-coordinator` plus `omo-orchestrate` route work, merge evidence, and decide whether to continue, review, or stop.
- Ultrawork -> explicit parallel waves, bounded follow-up, evidence-first outputs, and no duplicate searches once an owner is assigned.
- Continuation and handoff -> durable handoff notes with current state, blockers, validation, and next exact action.
- Review gates -> `APPROVE` or `REQUEST_CHANGES`, with confirmed blockers fed back into the next fix pass.
- LSP, rules, and comment-checker ideas -> manual equivalents: read project rules, run diagnostics or targeted checks when available, and keep findings tied to file-level evidence.

## What Was Translated From LazyCodex

- Evidence-first orchestration instead of opinion-first summaries.
- Bounded delegation, so background research or review cannot stall work forever.
- Strong continuation rules for long tasks, compacted sessions, and multi-agent handoff.
- Review as a real gate, not a cosmetic final step.
- Claude Code compatibility language instead of Codex or OpenCode runtime assumptions.

## What Is Deliberately Not Ported

- No runtime hooks such as SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostCompact, SubagentStop, or Stop.
- No bundled MCP servers, no `.mcp.json`, and no automatic provider or tool routing.
- No scripts, no telemetry, no package manager setup, and no executable loop runner.
- No automatic LSP injection, comment scanner, or rules engine. The skills describe how to do those checks manually with normal Claude Code tools.
- No hidden runtime hooks behind the specialized skills. They remain prompt-only guidance.

## Optional Future Runtime Mapping

If a future version ever gains runtime pieces, keep them optional and separate from this plugin's current content-only scope.

- Hooks could mirror the current handoff and continuation prompts.
- MCP servers could backfill documentation, code search, or diagnostics that the prompts currently treat as manual checks.
- Review automation could mirror the existing `APPROVE` or `REQUEST_CHANGES` gate instead of replacing it with opaque summaries.

## Recommended Workflow

Use `/omo-orchestrate` for work that touches 2+ files, changes public/API/CLI behavior, affects data flow, or needs review before handoff. The workflow classifies intent, gathers context, plans concrete work, delegates or executes the smallest safe steps, runs review-fix loops, verifies results, and records handoff state when work spans sessions or agents.

Background agents are advisory, not blocking. Wait for one bounded follow-up when a delegated agent stalls, returns no usable output, or repeats the same result. If it still does not produce usable evidence, continue with available findings, record the agent as stalled or blocked, and escalate only when the missing evidence is critical.

For implementation tasks, prefer `/omo-plan` before editing and `/omo-review` before final handoff. A final review should produce either `APPROVE` or `REQUEST_CHANGES`; blocking findings feed the next fix pass.

## Planning And Review Gates

- Plans should include TL;DR, dependencies, QA scenarios, gap classification, and verification strategy.
- Significant implementation should pass an implement-review-fix loop before final handoff.
- PR-style review should be evidence-first: understand changed files, verify uncertain findings against the codebase, and record verified non-issues separately from findings.
- If the same blocker survives a bounded retry budget, stop, record the exact blocker, and continue with partial findings or ask one precise question.

## Claude Code Compatibility Notes

- Treat Claude Code tools as the execution layer. The plugin text should tell the operator what to check, not assume hidden runtime automation.
- When the original OMO flow mentions hooks or MCP-only capabilities, translate them into manual steps, explicit checkpoints, or optional future mapping.
- Keep outputs grounded in file paths, symbols, test names, diagnostics, and command results. Avoid unsupported claims such as "auto-verified" unless the current session actually ran that check.

## Ultrawork Pattern

1. Split independent research and review work into parallel agents with a bounded follow-up window; never wait indefinitely for background results.
2. Give each agent a single goal and a concrete output format.
3. Require evidence in every agent return: paths, symbols, tests, commands, or quoted file lines.
4. Share state through handoff files, not hidden memory.
5. Avoid duplicate searches once a specialist is investigating that area.
6. Converge with tests, diagnostics, build checks, and manual QA where applicable.

## TDD-Oriented Pattern

1. Define expected behavior and acceptance checks first.
2. Add or identify the failing test or validation target when the codebase supports it.
3. Implement the minimal change needed to pass.
4. Run targeted checks, then widen to build or broader test suites.
5. Do not weaken tests or add speculative compatibility paths.

## Security And Privacy Boundaries

- No scripts are included.
- No network access or credentials are configured by this plugin.
- No session history, private transcripts, or OAuth tokens are copied.
- Agents that are meant to research or review should stay read-only unless a user explicitly asks for implementation.
- Handoff files should not include secrets or private data beyond what the current task requires.

## Validation

```bash
claude plugin validate ./omo-orchestrator
claude plugin validate .
```

Also verify that `.claude-plugin/marketplace.json` and this plugin's `plugin.json` use the same version.

For content review, inspect these files after editing:

```bash
grep -n "0.3.2\|content-only\|PASS\|FAIL\|INCONCLUSIVE\|bounded\|model: haiku" omo-orchestrator/README.md omo-orchestrator/.claude-plugin/plugin.json .claude-plugin/marketplace.json omo-orchestrator/skills/*/SKILL.md omo-orchestrator/agents/*.md omo-orchestrator/skills/omo-orchestrate/references/*.md
```
