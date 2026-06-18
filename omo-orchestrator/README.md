# omo-orchestrator

OMO-inspired Claude Code orchestration plugin. It packages portable skills and agents for intent routing, file-level planning, TDD-oriented implementation, parallel research, review gates, and safety guardrails.

This plugin is content-only. It does not install scripts, MCP servers, hooks, provider routing, token storage, or OpenCode runtime internals.

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

## Included Agents

- `omo-coordinator`: intent routing, delegation, state tracking, and completion checks.
- `omo-planner`: executable plans, blocker discovery, and plan review.
- `omo-implementer`: deep executor for minimal verified changes.
- `omo-researcher`: read-only code and reference investigator.
- `omo-reviewer`: independent reviewer for risk, quality, and scope control.

## Recommended Workflow

Use `/omo-orchestrate` for work that touches 2+ files, changes public/API/CLI behavior, affects data flow, or needs review before handoff. The workflow classifies intent, gathers context, plans concrete work, delegates or executes the smallest safe steps, runs review-fix loops, verifies results, and records handoff state when work spans sessions or agents.

Background agents are advisory, not blocking. Wait for one bounded follow-up when a delegated agent stalls, returns no usable output, or repeats the same result. If it still does not produce usable evidence, continue with available findings, record the agent as stalled or blocked, and escalate only when the missing evidence is critical.

For implementation tasks, prefer `/omo-plan` before editing and `/omo-review` before final handoff. A final review should produce either `APPROVE` or `REQUEST_CHANGES`; blocking findings feed the next fix pass.

## Planning And Review Gates

- Plans should include TL;DR, dependencies, QA scenarios, gap classification, and verification strategy.
- Significant implementation should pass an implement-review-fix loop before final handoff.
- PR-style review should be evidence-first: understand changed files, verify uncertain findings against the codebase, and record verified non-issues separately from findings.
- If the same blocker survives a bounded retry budget, stop, record the exact blocker, and continue with partial findings or ask one precise question.

## Ultrawork Pattern

1. Split independent research and review work into parallel agents with a bounded follow-up window; never wait indefinitely for background results.
2. Give each agent a single goal and a concrete output format.
3. Share state through handoff files, not hidden memory.
4. Avoid duplicate searches once a specialist is investigating that area.
5. Converge with tests, diagnostics, build checks, and manual QA where applicable.

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
