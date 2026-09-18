# omo-orchestrator

OMO-inspired Claude Code orchestration plugin. It packages portable skills and agents for situation-led intent routing, decision-complete planning, dependency-aware execution, parallel research, real-surface QA, independent review gates, safety guardrails, and focused specialist workflows.

This plugin is content-only. It does not install scripts, hooks, MCP servers, provider routing, token storage, package manifests, or OpenCode runtime internals.

## Install

```text
/plugin marketplace add AniP-gt/claude-plugins
/plugin install omo-orchestrator@hidetsugu-miya
```

Restart Claude Code after installation.

## Included Skills

- `omo-orchestrate`: main workflow for complex multi-step work.
- `omo-plan`: file-level planning with an approval brief before the executable plan, dependency matrix, QA scenarios, blockers, and verification commands. Approval writes the plan only. It does not authorize implementation.
- `omo-implement`: planned implementation with exploration, minimal edits, review-fix iteration, real-surface QA, and validation.
- `omo-research`: read-only local/codebase research workflow.
- `omo-review`: PR-style security, robustness, quality, goal-alignment, and test-coverage review gate.
- `omo-guardrails`: context, duplication, circuit-breaker, error-recovery, and handoff safety rules.
- `omo-hyperplan`: adversarial planning for hard, risky, or ambiguous work.
- `omo-ralph-loop`: manual continuation loop for iterative fix, review, validation, and handoff.
- `omo-handoff`: manual durable handoff workflow for a task-linked append-only phase ledger.

## Specialized Skills

These are LazyCodex-inspired Claude Code translations. They are content-only prompts, not runtime hooks or automation.

- `omo-programming`: implementation policy for type safety, minimal diffs, tests, diagnostics, and honest validation.
- `omo-start-work`: kickoff workflow for non-trivial tasks, context gathering, plans, evidence targets, and handoff setup, with manual TodoWrite and append-only ledger equivalence at phase boundaries.
- `omo-ultrawork`: high-throughput parallel work mode with independent waves, bounded follow-up, evidence ledger, and manual QA gate.
- `omo-review-work`: post-implementation review gate with evidence-based `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` outcomes.
- `omo-debugging`: hypothesis-driven debugging with reproduction first, root cause proof, failing validation, minimal fix, and verification.
- `omo-refactor`: safe refactoring with behavior lock first, caller and callee inventory, small steps, and drift checks.
- `omo-remove-ai-slop`: regression-first cleanup for AI-generated comments, complexity, duplication, and weak abstractions.
- `omo-ultraresearch`: read-only research mode with a source matrix, evidence thresholds, bounded lead expansion, convergence, non-goals, and stop conditions.
- `omo-coding-agent-sessions`: read-only local session investigation that keeps transcript evidence separate from accounting metadata, inspects linked child sessions, and records evidence gaps.
- `omo-visual-qa`: manual rendered-surface QA for browser pages and terminal TUIs, requiring fresh visual evidence and an `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` verdict.
- `omo-get-unpublished-changes`: diff-based release impact analysis against a published or agreed baseline.
- `omo-pre-publish-review`: release gate for versioning, packaging, docs, validation, and security risk.
- `omo-work-with-pr`: end-to-end PR lifecycle workflow from issue understanding through review and validation.
- `omo-security-research`: exploitability-first security research with threat model, evidence, and severity calibration.
- `omo-github-triage`: issue and PR triage workflow for classification, priority, evidence, and next action.
- `omo-remove-deadcode`: deletion-safe dead-code cleanup with reference checks and zero-false-positive discipline.
- `omo-git-master`: git workflow for atomic commits, rebase and squash, and history archaeology. Detects commit style and language from existing history instead of assuming a convention.
- `omo-init-deep`: explicit, content-only generation and maintenance of a hierarchical Claude Code rule set for a Git worktree.

## OMO Init Deep

Version 0.11.0 adds `omo-init-deep`. Invoke it explicitly when a repository needs a generated, evidence-based Claude Code rule set:

```text
/omo-init-deep
/omo-init-deep --create-new
/omo-init-deep --committed
/omo-init-deep --max-depth=2
/omo-init-deep --create-new --committed --max-depth=2
```

Version 0.12.0 refines the procedure with six evidence lanes and one metadata inventory, capped at a maximum of ten lanes and 120 content reads. LSP and ast-grep have complementary roles, with unavailable metrics left unmeasured. Codegraph-to-ast-grep alignment follows upstream init-deep source change `8512ef8f6a4ea97d737007ca045755428be8ad91`; the latest description is `279017261f8e4cec26a02b796fff72d2e0648f0d`. Schema-1 manifests from 0.11.0 and 0.12.0 are accepted, but 0.11.0 manifests upgrade only on approved writes.

Without a mode flag, it uses local update mode. `--create-new` rebuilds the skill-owned output set after approved conflict resolution and deletions. `--committed` makes those same outputs eligible to be tracked. It never stages, commits, untracks, or otherwise changes the Git index. When omitted, `--max-depth` defaults to `3`; `--max-depth=N` accepts a non-negative base-10 integer, and `0` permits only the root rule.

The skill owns only these repository paths:

```text
.claude/rules/omo-init-deep/
.claude/omo/init-deep.json
```

In local mode, it manages only this exact block in the repository's Git-resolved `info/exclude` file, never `.gitignore`:

```gitignore
# >>> omo-init-deep managed >>>
/.claude/rules/omo-init-deep/
/.claude/omo/init-deep.json
# <<< omo-init-deep managed <<<
```

It finds that file through `git rev-parse --git-path info/exclude`, which matters for linked worktrees. Adding or normalizing the local block always needs explicit confirmation. In committed mode, the generated rules and manifest are eligible to track only after the exact managed block is removed with separate explicit confirmation. The skill preserves all bytes outside that block, never substitutes `.gitignore`, and does not automatically commit anything.

Before changing files, it previews the mode, depth, generated candidates, conflicts, tracked-file warnings, deletions, and exclude action. Explicit confirmation is also required to delete a manifest-owned output or overwrite a file whose recorded hash differs. Future `schemaVersion > 1` aborts read-only without replacement. Malformed JSON, an absent or invalid schema, or a structurally invalid schema-1 manifest require read-only reconciliation and explicit replacement confirmation. When regenerating output in another worktree, resolve its `info/exclude` path again rather than assuming the prior worktree's Git administrative path applies. Git ignores are a convenience for local output, not a security boundary.

This remains a content-only procedure. It does not add scripts, hooks, MCP servers, daemons, watchers, startup refresh, automatic continuation, atomic writes, or automatic Git operations. Generated rules are project guidance, not enforcement. After a run, inspect `/context` or `InstructionsLoaded` when available. Ignored-rule loading is not guaranteed, and child rules are scoped rather than eagerly loaded.

## Included Agents

- `omo-coordinator`: intent routing, delegation, state tracking, and completion checks. Uses `model: opus` because orchestration quality is high leverage.
- `omo-planner`: executable plans, blocker discovery, and plan review. Uses `model: opus` because planning quality is high leverage.
- `omo-implementer`: deep executor for minimal verified changes. Uses `model: opus`.
- `omo-researcher`: the Explore equivalent for read-only local code and external reference investigation, with evidence labels and access limits disclosed. Uses `model: haiku`.
- `omo-reviewer`: the Momus-style independent reviewer for risk, quality, and scope control. Uses `model: opus`.
- `omo-oracle`: read-only strategic advisor for architecture decisions, debugging that has already failed repeatedly, post-implementation self-review, and security or performance tradeoffs. Gives one recommendation with an effort estimate. Uses `model: fable` because the consultation is the deliverable and reasoning depth is the whole point.
- `omo-metis`: read-only pre-planning consultant. Classifies intent, surfaces ambiguity and hidden assumptions, and emits directives before planning starts. Uses `model: opus`.
- `omo-librarian`: read-only external source researcher for unfamiliar libraries and dependency history. Requires permalinks or versioned documentation URLs for every claim. Uses `model: sonnet`.
- `omo-media-reader`: read-only interpreter for PDFs, images, and diagrams. Extracts only what was asked so the caller never loads the raw file. Uses `model: opus`.

## Model Guidance

Agent model hints are enforced through agent frontmatter where Claude Code supports it. Skills are prompt content, so their model guidance is advisory unless a caller chooses the model explicitly.

Haiku is appropriate for low-risk, mechanical work: read-only code investigation, simple git or CLI operations, metadata checks, and narrow documentation lookups. It is not the default for planning, orchestration, implementation, or skeptical review.

Haiku is sufficient for routine use of these prompt-only skills when the task is narrow and evidence-based:

- `omo-guardrails`
- `omo-programming`
- `omo-research`
- `omo-start-work`
- `omo-ultraresearch`
- `omo-coding-agent-sessions`
- `omo-visual-qa`

Use a stronger model for orchestration, planning, high-risk implementation, skeptical review, hard debugging, broad refactors, or ambiguous product decisions.

## Claude Code Adaptation Scope

This plugin adapts useful LazyCodex OMO ideas into Claude Code prompts only. It keeps the OMO shape, but translates runtime-driven behavior into manual skill and agent behavior that works in a local Claude Code session.

### Upstream Snapshot

The portable contracts in version 0.10.0 were refreshed against `oh-my-openagent` commit `89321658864550ddee6e6fb88cbf0cc1ec425169`. The refresh carries planning intent routing and approval gates, dependency-aware parallel waves, bounded follow-up and research-lead convergence, discovered-work discipline, evidence-led handoffs with manual TodoWrite and ledger equivalence, session transcript and accounting distinctions, real-surface visual QA with fresh evidence, one independent final reviewer, adversarial plan distillation, exploitability-first security research, and release ownership gates.

This is a Claude-compatible adaptation, not runtime parity. The plugin retains only behavior that can be expressed as visible Claude Code prompt contracts and tool semantics.

## Main Context Orchestration-Only Policy

When using OMO as the work controller, the main context is restricted to orchestration. It should classify intent, maintain todos or handoff state, dispatch sub-agents, read enough evidence to verify delegated results, synthesize findings, ask the user for missing decisions, and produce the final handoff.

The main context must not directly implement, edit files, run task commands, perform owned investigation, perform owned review, or apply fixes. Those phases belong to the appropriate sub-agent: planner, researcher, implementer, reviewer, or a specialized workflow agent. This is a prompt-level and tool-allowlist policy, not hidden runtime enforcement.

Examples:

- Aggregator model -> `omo-coordinator` plus `omo-orchestrate` route work, merge evidence, and decide whether to continue, review, or stop.
- Ultrawork -> explicit parallel waves, bounded follow-up, evidence-first outputs, and no duplicate searches once an owner is assigned.
- Planning -> classify outcome clarity, research defaults for unclear goals, and ask only for irreducible owner decisions before a plan approval brief.
- Session investigation -> inspect raw transcript artifacts and linked child sessions, while reporting usage, token, model, time, and cost fields as accounting metadata rather than transcript content.
- Visual QA -> drive the real rendered surface, capture fresh visual evidence for the final tree, and return `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`.
- Dependency routing -> fan out independent lanes while serializing shared state, same-file writes, shared contracts, and named predecessors.
- Discovered work -> report out-of-scope findings, then record and scope required follow-up before assigning it. Do not silently expand or defer the request.
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
- No OpenCode-only hooks, `team_*` APIs, Boulder state, workflow DAG APIs, worktree lifecycle promises, injected notifications, or runtime continuation.
- No bundled MCP servers, no `.mcp.json`, and no automatic provider or tool routing.
- No bundled helpers, provider-specific model routing, native installers, telemetry, package-local scripts, package manager setup, or executable loop runner.
- No browser automation, runtime session indexing, hooks, or automatic continuation for the session-investigation and visual-QA workflows.
- No automatic LSP injection, comment scanner, or rules engine. The skills describe how to do those checks manually with normal Claude Code tools.
- No hidden runtime hooks behind the specialized skills. They remain prompt-only guidance.
- No provider fallback, task engine, MCP runtime, automatic Ralph loop, background continuation, GitHub mutation, publishing, or release execution. The related skills provide operator checklists and handoff contracts only.
- Separate specialist aliases and `stop-continuation` are deferred. They add no distinct content-only benefit or imply runtime control outside this plugin's scope.

## Optional Future Runtime Mapping

If a future version ever gains runtime pieces, keep them optional and separate from this plugin's current content-only scope.

- Hooks could mirror the current handoff and continuation prompts.
- MCP servers could backfill documentation, code search, or diagnostics that the prompts currently treat as manual checks.
- Review automation could mirror the existing `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` gate instead of replacing it with opaque summaries.
- Loop automation could mirror the `omo-ralph-loop` completion promise and iteration ledger, but must remain opt-in and visible.

## Recommended Workflow

Use `/omo-orchestrate` for work that touches 2+ files, changes public/API/CLI behavior, affects data flow, or needs review before handoff. The workflow classifies intent, gathers context for routing, plans concrete work, delegates the smallest safe steps to sub-agents, runs dependency-aware waves, runs review-fix loops through sub-agents, verifies delegated evidence, and records handoff state when work spans sessions or agents.

Background agents are advisory, not blocking. Wait for one bounded follow-up when a delegated agent stalls, returns no usable output, or repeats the same result. If it still does not produce usable evidence, continue with available findings, record the agent as stalled or blocked, and escalate only when the missing evidence is critical.

For implementation tasks, prefer `/omo-plan` before editing and `/omo-review` before final handoff. The mandatory final gate returns `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`. Only `APPROVE` permits completion. `REQUEST_CHANGES` feeds a bounded fix and re-review; `INCONCLUSIVE` blocks completion until the missing evidence or decision is recorded and resolved.

For release or PR work, run `/omo-get-unpublished-changes` before `/omo-pre-publish-review`, then use `/omo-work-with-pr` to prepare the handoff or reviewer response. Publishing, pushing, merging, and external comments remain user-approved actions.

## Planning And Review Gates

- `omo-plan` classifies the requested outcome as `CLEAR` or `UNCLEAR`. Clear plans ask only for irreducible owner decisions. Unclear plans research and announce practical defaults before the approval brief. Plan approval never authorizes implementation.
- `omo-ultraresearch` expands only leads with stated decision impact, source, owner, and bounded budget. Research converges when the evidence threshold is met, remaining leads are non-material, or further searches repeat known evidence.
- `omo-start-work` treats manual TodoWrite state and the latest append-only ledger entry as equivalent views of the same work state. Compare them before dispatch, handoff, retry, review, and completion; correct disagreement with the current TodoWrite item and a new ledger entry, never by rewriting history.
- Plans should include TL;DR, dependencies, QA scenarios, gap classification, and verification strategy.
- Every parallel wave must state why its lanes are independent. Same-file writes, shared contracts, mutable state, and named predecessors serialize.
- Every plan must define executable QA scenarios with a tool or surface, concrete commands or steps, a pass or fail assertion, and an evidence location. Abstract checks such as "verify it works" are blocking plan-quality findings.
- Significant implementation should pass an implement-review-fix loop before final handoff.
- Hard or risky plans should pass `/omo-hyperplan` before implementation.
- Release candidates should pass unpublished-change analysis and pre-publish review before publishing.
- PR-style review should be evidence-first: understand changed files, verify uncertain findings against the codebase, and record verified non-issues separately from findings.
- `omo-review-work` uses two lanes: real-surface QA against the final tree, then exactly one independent read-only final reviewer. A failed QA row returns `REQUEST_CHANGES`; missing reviewer evidence is `INCONCLUSIVE`.
- If the same blocker survives a bounded retry budget, stop, record the exact blocker, and continue with partial findings or ask one precise question.

## Manual Handoffs

For multi-phase work, use `/omo-handoff` to create and maintain `.claude/omo/handoffs/<task-slug>.md`. The ledger has immutable task metadata and append-only phase entries for dependencies, evidence, QA results, retries, gate state, blockers, and one next exact action.

The handoff is manual. No hook creates it, no process updates it, and no later session resumes it automatically. A later operator reads the full ledger and manually takes the recorded next action.

## Claude Code Compatibility Notes

- Treat Claude Code tools as the execution layer. The plugin text should tell the operator what to check, not assume hidden runtime automation.
- When the original OMO flow mentions hooks or MCP-only capabilities, translate them into manual steps, explicit checkpoints, or optional future mapping.
- Keep outputs grounded in file paths, symbols, test names, diagnostics, and command results. Avoid unsupported claims such as "auto-verified" unless the current session actually ran that check.

## Ultrawork Pattern

1. Size work as `LIGHT` or `HEAVY`, and only increase rigor when risk increases.
2. Split only independent research, implementation, or review work into parallel agents with a bounded follow-up window; never wait indefinitely for background results.
3. Give each agent a single goal, dependency boundary, success criteria, and concrete output format.
4. Require evidence in every agent return: paths, symbols, tests, commands, real-surface artifacts, or quoted file lines.
5. Share state through handoff files, not hidden memory, and add required discovered work to the plan before dispatching it.
6. Converge with tests, diagnostics, build checks, real-surface QA, and independent review when the change is heavy or release, security, persistence, public-behavior, or data-flow work.

## TDD-Oriented Pattern

1. Define expected behavior and acceptance checks first.
2. Add or identify the failing test or validation target when the codebase supports it.
3. Implement the minimal change needed to pass.
4. Run targeted checks, then widen to build or broader test suites.
5. Do not weaken tests or add speculative compatibility paths.

## Security And Privacy Boundaries

- No scripts are included.
- No bundled helpers are included.
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
  '`omo-coding-agent-sessions`',
  '`omo-visual-qa`',
  '`omo-init-deep`',
  '/omo-init-deep --create-new',
  '/omo-init-deep --committed',
  '/omo-init-deep --max-depth=2',
  'When omitted, `--max-depth` defaults to `3`',
  '.claude/rules/omo-init-deep/',
  '.claude/omo/init-deep.json',
  'git rev-parse --git-path info/exclude',
  'explicit confirmation',
  'Future `schemaVersion > 1` aborts read-only without replacement',
  'Malformed JSON, an absent or invalid schema, or a structurally invalid schema-1 manifest require read-only reconciliation and explicit replacement confirmation',
  'resolve its `info/exclude` path again',
  'Ignored-rule loading is not guaranteed',
  'does not automatically commit anything',
  'six evidence lanes',
  'one metadata inventory',
  'maximum of ten lanes',
  '120 content reads',
  'LSP and ast-grep have complementary roles',
  'unavailable metrics left unmeasured',
  '8512ef8f6a4ea97d737007ca045755428be8ad91',
  '279017261f8e4cec26a02b796fff72d2e0648f0d',
  'Schema-1 manifests from 0.11.0 and 0.12.0 are accepted',
  '0.11.0 manifests upgrade only on approved writes',
  '89321658864550ddee6e6fb88cbf0cc1ec425169',
  'Approval writes the plan only. It does not authorize implementation.',
  'bounded lead expansion',
  'Research converges',
  'manual TodoWrite state and the latest append-only ledger entry as equivalent views of the same work state',
  'transcript evidence',
  'accounting metadata',
  'linked child sessions',
  'fresh visual evidence for the final tree',
  'No bundled helpers',
  'Separate specialist aliases and `stop-continuation` are deferred',
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
