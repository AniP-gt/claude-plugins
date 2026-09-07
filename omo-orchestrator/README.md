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
- `omo-hyperplan`: adversarial planning for hard, risky, or ambiguous work.
- `omo-ralph-loop`: manual continuation loop for iterative fix, review, validation, and handoff.
- `omo-handoff`: manual durable handoff workflow for a task-linked append-only phase ledger.

## Specialized Skills

These are LazyCodex-inspired Claude Code translations. They are content-only prompts, not runtime hooks or automation.

- `omo-programming`: implementation policy for type safety, minimal diffs, tests, diagnostics, and honest validation.
- `omo-start-work`: kickoff workflow for non-trivial tasks, context gathering, plans, evidence targets, and handoff setup.
- `omo-ultrawork`: high-throughput parallel work mode with independent waves, bounded follow-up, evidence ledger, and manual QA gate.
- `omo-review-work`: post-implementation review gate with evidence-based `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` outcomes.
- `omo-debugging`: hypothesis-driven debugging with reproduction first, root cause proof, failing validation, minimal fix, and verification.
- `omo-refactor`: safe refactoring with behavior lock first, caller and callee inventory, small steps, and drift checks.
- `omo-remove-ai-slop`: regression-first cleanup for AI-generated comments, complexity, duplication, and weak abstractions.
- `omo-ultraresearch`: exhaustive read-only research mode with source matrix, evidence thresholds, non-goals, and stop conditions.
- `omo-get-unpublished-changes`: diff-based release impact analysis against a published or agreed baseline.
- `omo-pre-publish-review`: release gate for versioning, packaging, docs, validation, and security risk.
- `omo-work-with-pr`: end-to-end PR lifecycle workflow from issue understanding through review and validation.
- `omo-security-research`: exploitability-first security research with threat model, evidence, and severity calibration.
- `omo-github-triage`: issue and PR triage workflow for classification, priority, evidence, and next action.
- `omo-remove-deadcode`: deletion-safe dead-code cleanup with reference checks and zero-false-positive discipline.
- `omo-git-master`: git workflow for atomic commits, rebase and squash, and history archaeology. Detects commit style and language from existing history instead of assuming a convention.

## Included Agents

- `omo-coordinator`: intent routing, delegation, state tracking, and completion checks. Not pinned to Haiku because orchestration quality is high leverage.
- `omo-planner`: executable plans, blocker discovery, and plan review. Not pinned to Haiku because planning quality is high leverage.
- `omo-implementer`: deep executor for minimal verified changes.
- `omo-researcher`: the Explore equivalent for read-only local code and external reference investigation, with evidence labels and access limits disclosed. Uses `model: haiku`.
- `omo-reviewer`: the Momus-style independent reviewer for risk, quality, and scope control.
- `omo-oracle`: read-only strategic advisor for architecture decisions, debugging that has already failed repeatedly, post-implementation self-review, and security or performance tradeoffs. Gives one recommendation with an effort estimate.
- `omo-metis`: read-only pre-planning consultant. Classifies intent, surfaces ambiguity and hidden assumptions, and emits directives before planning starts.
- `omo-librarian`: read-only external source researcher for unfamiliar libraries and dependency history. Requires permalinks or versioned documentation URLs for every claim.
- `omo-media-reader`: read-only interpreter for PDFs, images, and diagrams. Extracts only what was asked so the caller never loads the raw file.

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

## Main Context Orchestration-Only Policy

When using OMO as the work controller, the main context is restricted to orchestration. It should classify intent, maintain todos or handoff state, dispatch sub-agents, read enough evidence to verify delegated results, synthesize findings, ask the user for missing decisions, and produce the final handoff.

The main context must not directly implement, edit files, run task commands, perform owned investigation, perform owned review, or apply fixes. Those phases belong to the appropriate sub-agent: planner, researcher, implementer, reviewer, or a specialized workflow agent. This is a prompt-level and tool-allowlist policy, not hidden runtime enforcement.

Examples:

- Aggregator model -> `omo-coordinator` plus `omo-orchestrate` route work, merge evidence, and decide whether to continue, review, or stop.
- Ultrawork -> explicit parallel waves, bounded follow-up, evidence-first outputs, and no duplicate searches once an owner is assigned.
- Continuation and handoff -> manual, durable handoff notes with current state, blockers, validation, and next exact action.
- Review gates -> `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`, with confirmed blockers fed back into the next fix pass.
- Release and PR lifecycle -> unpublished-change analysis, pre-publish review, PR handoff, and version-impact checks.
- Ralph loop and continuation -> explicit completion promises, iteration ledgers, and recovery handoffs.
- LSP, rules, and comment-checker ideas -> manual equivalents: read project rules, run diagnostics or targeted checks when available, and keep findings tied to file-level evidence.

## What Was Translated From LazyCodex

- Evidence-first orchestration instead of opinion-first summaries.
- Bounded delegation, so background research or review cannot stall work forever.
- Strong continuation rules for long tasks, compacted sessions, and multi-agent handoff.
- Review as a real gate, not a cosmetic final step.
- Adversarial planning, release gates, security research, PR lifecycle, and deletion-safe cleanup as prompt-level workflows.
- Claude Code compatibility language instead of Codex or OpenCode runtime assumptions.

## What Is Deliberately Not Ported

- No runtime hooks such as SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PostCompact, SubagentStop, or Stop.
- No bundled MCP servers, no `.mcp.json`, and no automatic provider or tool routing.
- No scripts, no telemetry, no package manager setup, and no executable loop runner.
- No automatic LSP injection, comment scanner, or rules engine. The skills describe how to do those checks manually with normal Claude Code tools.
- No hidden runtime hooks behind the specialized skills. They remain prompt-only guidance.
- No provider fallback, task engine, MCP runtime, automatic Ralph loop, background continuation, GitHub mutation, publishing, or release execution. The related skills provide operator checklists and handoff contracts only.
- Separate specialist aliases, `init-deep`, and `stop-continuation` are deferred. They add no distinct content-only benefit or imply runtime control outside this plugin's scope.

## Optional Future Runtime Mapping

If a future version ever gains runtime pieces, keep them optional and separate from this plugin's current content-only scope.

- Hooks could mirror the current handoff and continuation prompts.
- MCP servers could backfill documentation, code search, or diagnostics that the prompts currently treat as manual checks.
- Review automation could mirror the existing `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` gate instead of replacing it with opaque summaries.
- Loop automation could mirror the `omo-ralph-loop` completion promise and iteration ledger, but must remain opt-in and visible.

## Recommended Workflow

Use `/omo-orchestrate` for work that touches 2+ files, changes public/API/CLI behavior, affects data flow, or needs review before handoff. The workflow classifies intent, gathers context for routing, plans concrete work, delegates the smallest safe steps to sub-agents, runs review-fix loops through sub-agents, verifies delegated evidence, and records handoff state when work spans sessions or agents.

Background agents are advisory, not blocking. Wait for one bounded follow-up when a delegated agent stalls, returns no usable output, or repeats the same result. If it still does not produce usable evidence, continue with available findings, record the agent as stalled or blocked, and escalate only when the missing evidence is critical.

For implementation tasks, prefer `/omo-plan` before editing and `/omo-review` before final handoff. The mandatory final gate returns `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`. Only `APPROVE` permits completion. `REQUEST_CHANGES` feeds a bounded fix and re-review; `INCONCLUSIVE` blocks completion until the missing evidence or decision is recorded and resolved.

For release or PR work, run `/omo-get-unpublished-changes` before `/omo-pre-publish-review`, then use `/omo-work-with-pr` to prepare the handoff or reviewer response. Publishing, pushing, merging, and external comments remain user-approved actions.

## Planning And Review Gates

- Plans should include TL;DR, dependencies, QA scenarios, gap classification, and verification strategy.
- Every plan must define executable QA scenarios with a tool or surface, concrete commands or steps, a pass or fail assertion, and an evidence location. Abstract checks such as "verify it works" are blocking plan-quality findings.
- Significant implementation should pass an implement-review-fix loop before final handoff.
- Hard or risky plans should pass `/omo-hyperplan` before implementation.
- Release candidates should pass unpublished-change analysis and pre-publish review before publishing.
- PR-style review should be evidence-first: understand changed files, verify uncertain findings against the codebase, and record verified non-issues separately from findings.
- If the same blocker survives a bounded retry budget, stop, record the exact blocker, and continue with partial findings or ask one precise question.

## Manual Handoffs

For multi-phase work, use `/omo-handoff` to create and maintain `.claude/omo/handoffs/<task-slug>.md`. The ledger has immutable task metadata and append-only phase entries for dependencies, evidence, QA results, retries, gate state, blockers, and one next exact action.

The handoff is manual. No hook creates it, no process updates it, and no later session resumes it automatically. A later operator reads the full ledger and manually takes the recorded next action.

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

Use a version-independent semantic check after editing:

```bash
node - <<'NODE'
const fs = require('node:fs');
const read = (path) => fs.readFileSync(path, 'utf8');
const required = [
  'content-only',
  'omo-handoff',
  '.claude/omo/handoffs/<task-slug>.md',
  'APPROVE',
  'REQUEST_CHANGES',
  'INCONCLUSIVE',
  'Only `APPROVE` permits completion',
  'tool or surface',
  'concrete commands or steps',
  'evidence location',
  'the Explore equivalent',
  'the Momus-style independent reviewer',
  '`omo-oracle`',
  '`omo-metis`',
  '`omo-librarian`',
  '`omo-media-reader`',
  '`omo-git-master`',
  'Separate specialist aliases, `init-deep`, and `stop-continuation` are deferred',
  'No provider fallback, task engine, MCP runtime, automatic Ralph loop, background continuation'
];
const readme = read('omo-orchestrator/README.md');
const missing = required.filter((text) => !readme.includes(text));
const legacyOutcomes = readme.includes('`P' + 'ASS`') || readme.includes('`F' + 'AIL`');
if (missing.length || legacyOutcomes) {
  throw new Error(`README semantic validation failed: missing=${missing.join(', ') || 'none'} legacyOutcomes=${legacyOutcomes}`);
}
console.log('README semantic validation passed');
NODE
```
