# omo-orchestrator

OMO-inspired Claude Code orchestration plugin. It packages portable skills and agents for situation-led intent routing, decision-complete planning, dependency-aware execution, parallel research, real-surface QA, independent review gates, safety guardrails, and focused specialist workflows.

This plugin is content-only apart from four small guidance hooks (see [Ulw Keyword Trigger](#ulw-keyword-trigger), [Pre-flight And Review Gate](#pre-flight-and-review-gate), and the JSON argument recovery hook) and one read-only helper script, `scripts/impact.mjs` (see [Impact Script](#impact-script)). It does not install other scripts or hooks, MCP servers, provider routing, token storage, package manifests, or OpenCode runtime internals. Local Git operations are governed by `omo-git-master`. GitHub actions, including publish, push, PR merge, and remote comments, are outside these skills; an external operator performs them only with the required explicit permission. The skills prepare local artifacts and handoffs only.

## Install

```text
/plugin marketplace add AniP-gt/claude-plugins
/plugin install omo-orchestrator@AniP-gt
```

Restart Claude Code after installation.

Version 1.26.0 refreshes portable planning and execution contracts against upstream `5943705430de7879690923a61b6ca5b94d282783` (5.1.27). Approval and authorization questions stay in the main session; missing or timed-out answers leave dependent work pending. Existing explicit authorization is reused. Claude Code uses `AskUserQuestion` or a chat fallback, without Senpi-specific tool parameters. Runtime changes to task cancellation, memory locks, side panels, provider routing, and installers are not ported. Evaluation evidence is recorded in `docs/reports/2026-10-09-omo-upstream-refresh/`.

## Included Skills

- `omo-orchestrate`: main workflow for complex multi-step work.
- `omo-plan`: file-level planning with an approval brief before the executable plan, dependency matrix, QA scenarios, blockers, and verification commands. Approval writes the plan only. It does not authorize implementation.
- `omo-implement`: one scoped implementation/fix pass with exploration, minimal edits, real-surface QA, and validation; further passes belong to Ralph.
- `omo-research`: read-only local/codebase research workflow.
- `omo-review`: PR-style security, robustness, quality, goal-alignment, and test-coverage review gate.
- `omo-guardrails`: context, duplication, circuit-breaker, error-recovery, and handoff safety rules.
- `omo-hyperplan`: adversarial planning for hard, risky, or ambiguous work.
- `omo-ralph-loop`: sole manual continuation controller for implementation, repair, review, validation, and handoff; one shared default budget of 20 iterations.
- `omo-handoff`: manual durable handoff workflow for a task-linked append-only phase ledger, plus a short fresh-session brief (decisions changed, code state, failed directions, unverified items) that can start the next Claude session through the Orca CLI.

## Specialized Skills

These are LazyCodex-inspired Claude Code translations. They are content-only prompts, not runtime hooks or automation.

- `omo-programming`: implementation policy for type safety, minimal diffs, tests, diagnostics, and honest validation.
- `omo-start-work`: kickoff workflow for non-trivial tasks, context gathering, plans, evidence targets, and handoff setup, with manual TodoWrite and append-only ledger equivalence at phase boundaries.
- `omo-ultrawork`: ultrawork (`ulw`) mode ported from the upstream ultrawork directive: `ULTRAWORK MODE ENABLED!` bootstrap, binding goal block, skill survey, mandatory planner for non-trivial work, delegate-by-default, scenario contract, durable notepad, manual QA mandate, reviewer gate, and zero-tolerance completion rules.
- `omo-review-work`: post-implementation review gate with evidence-based `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` outcomes.
- `omo-debugging`: hypothesis-driven debugging with reproduction first, root cause proof, failing validation, minimal fix, and verification.
- `omo-refactor`: safe refactoring with behavior lock first, caller and callee inventory, small steps, and drift checks.
- `omo-remove-ai-slop`: regression-first cleanup for AI-generated comments, complexity, duplication, and weak abstractions.
- `omo-ultraresearch`: read-only research mode with a source matrix, evidence thresholds, bounded lead expansion, convergence, non-goals, and stop conditions.
- `omo-coding-agent-sessions`: read-only local session investigation that keeps transcript evidence separate from accounting metadata, inspects linked child sessions, and records evidence gaps.
- `omo-visual-qa`: manual rendered-surface QA for browser pages and terminal TUIs, requiring fresh visual evidence and an `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` verdict.
- `omo-visualize`: traceable standalone HTML/SVG charts, tables, and diagrams with self-contained assets, readable static content, explicit empty/error states, and rendered QA; existing application charts retain the frontend design-system gate.
- `omo-get-unpublished-changes`: diff-based release impact analysis against a published or agreed baseline.
- `omo-pre-publish-review`: release gate for versioning, packaging, docs, validation, and security risk.
- `omo-work-with-pr`: end-to-end PR lifecycle workflow from issue understanding through review and validation.
- `omo-security-research`: exploitability-first security research with threat model, evidence, and severity calibration.
- `omo-github-triage`: issue and PR triage workflow for classification, priority, evidence, and next action.
- `omo-remove-deadcode`: deletion-safe dead-code cleanup with reference checks and zero-false-positive discipline.
- `omo-git-master`: git workflow for atomic commits, rebase and squash, and history archaeology. Detects commit style and language from existing history instead of assuming a convention.
- `omo-init-deep`: explicit, content-only generation and maintenance of a hierarchical Claude Code rule set for a Git worktree.
- `omo-ulw-execute`: runs a written plan wave by wave through sub-agents with an evidence ledger, independently verified done claims, and a final `omo-review-work` gate. The orchestrator never implements. Ported from upstream `ulw-execute`.
- `omo-mass-ulw`: splits a large job into a dependency-ordered task graph and runs every ready wave in parallel, with bounded retry and amend recovery and a final review gate. The `Workflow` tool is used only when the user's own words ask for it. Ported from upstream `mass-ulw`.
- `omo-tech-debt-audit`: read-only, file-cited technical debt audit across 9 dimensions with severity, effort, and prioritized fixes, written to `TECH_DEBT_AUDIT.md`. Ported from upstream `tech-debt-audit`.
- `omo-ast-grep`: search and rewrite code by AST shape with the ast-grep CLI, preview-first rewrites, and YAML rules. Never auto-installs. Ported from upstream `ast-grep` (MIT, license kept in the skill directory).
- `omo-frontend`: UI and UX work plus the design-system workflow (analyze the existing system, build tokens if missing, implement through `omo-implementer` with a token-level brief, verify with `omo-visual-qa`). Merges the former personal `frontend-ui-ux` and `visual-engineering` skills with portable ideas from upstream `frontend`.
- `omo-review-loop`: implement-review-fix loop. `omo-implementer` builds, parallel `omo-reviewer` lanes review by dimension (security, robustness, quality, alignment, evidence gate, optional Copilot CLI), a synthesis judge splits findings into AUTO_FIX and ASK_USER, and the final `omo-review-work` gate (plus `self-review` when installed) returns a verdict to Ralph. All implementation, feedback, QA repair, and gate retries share Ralph's default 20-iteration budget; only independent final APPROVE completes the task. Rebuilt from the personal `implementation-review-loop` skill.
- `omo-lsp-setup`: detects which language servers a project needs, proposes install commands, wires a Claude Code LSP plugin, and verifies the server answers. Never installs without asking. Ported from upstream `lsp-setup`.

## OMO Init Deep

Version 0.11.0 adds `omo-init-deep`. Invoke it explicitly when a repository needs a generated, evidence-based Claude Code rule set:

```text
/omo-init-deep
/omo-init-deep --create-new
/omo-init-deep --committed
/omo-init-deep --max-depth=2
/omo-init-deep --create-new --committed --max-depth=2
```

Version 0.12.0 refines the procedure with six evidence lanes and one metadata inventory, capped at a maximum of ten lanes and 120 content reads. LSP and ast-grep have complementary roles, with unavailable metrics left unmeasured. Codegraph-to-ast-grep alignment follows upstream init-deep source change `8512ef8f6a4ea97d737007ca045755428be8ad91`; the latest description is `279017261f8e4cec26a02b796fff72d2e0648f0d`. Schema-1 manifests from 0.11.0, 0.12.0, and 1.0.0 are accepted, and 0.11.0 and 0.12.0 manifests upgrade to 1.0.0 only on approved writes.

Version 1.0.0 replaces the retired `omo-metis` pre-planning agent with canonical `omo-plan-consultant` and adds `omo-plan-reviewer`. Planning now names affected users, records `IS-*` ideal-state rows and `GAP-*` shortfalls, closes each gap with a task, and maps each ideal state to task, QA, and evidence. It remains a prompt-only update with no runtime automation.

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

## Consolidated Personal Workflows

Version 1.19.1 extends the reviewer checklist (`omo-review`, `omo-reviewer`). For a lock, guard, or uniqueness check that stops a duplicate run, the failure ledger asks whether the duplicate harms the downstream result at all, and reports a guard whose new wait timeout or skipped run loses work as costing more than it covers; another holder's hold time is read from the code it runs while holding the resource. A new concurrent-changes check lists other open PRs touching the same files (with a listing limit that covers every open PR, confirmed by the change under review appearing in its own result) and states conflicts, behavior once both land, contradicted premises, and a merge order.

Version 1.19.0 adapts upstream `visualize` at `c04544a95` (upstream 5.1.24) into `omo-visualize`. It preserves executable calculations, requires readable HTML/SVG without scripts or network assets, and routes final renders through `omo-visual-qa`. Standalone explanations use a local token set; charts inside applications still follow `omo-frontend`. No Senpi data engine, renderer, host theme, or inline-display capability is assumed.

It also translates upstream start-failure diagnosis and deferred revival into manual recovery checks: distinguish host refusal, timeout, and transport loss; verify child ownership and state before replacement; preserve unknown or foreign-owned children; count confirmed live capacity; and keep raw error payloads out of handoffs. No automatic revival or fixed Senpi concurrency cap is introduced.

Version 1.17.0 adds a failure ledger to the reviewer checklist (`omo-review`, `omo-reviewer`) for changes that fix a bug or add idempotency, locking, or transaction scope. The reviewer follows the downstream business result for delay and lost work, classifies each failure mode against the pre-change implementation as new, already present, or improved (already-present modes become out-of-scope notes and do not trigger a demand for a retry mechanism), grades frequency from the actual schedule, trigger, and concurrent actors, and checks any recovery claim in docs or comments against the code, including which inputs the next run processes. It remains a prompt-only update.

Version 1.16.0 makes the risk map cover shared locks and library assumptions. When a change starts taking a row lock, advisory lock, mutex, or unique slot, `omo-review` lists every other acquirer, how long each can hold it, and what happens when this code's acquisition times out or loses a deadlock, tracing the error through top-level handlers and retries to whoever redoes the skipped work; when nothing does, the row becomes an owner question rather than an automatic block. Checking only whether others wait on the change covers one direction of two. An option passed to change a library call's behavior must be backed by the library source or a run. `omo-implement` gives a new placeholder or adapter type a comment naming why it exists and one caller, and does not state lock hold times, run times, or failure-path outcomes without a measurement or test.

Version 1.15.1 clarifies `omo-review-work` evidence reuse: preserve valid QA rows, compare the tested state including uncommitted changes and runtime inputs, and rerun only affected or unproven rows. Missing evidence blocks reviewer dispatch and remains `INCONCLUSIVE`; a prior approval cannot approve a later edit. This adapts the portable evidence practices in local lazycodex snapshot `36ba46a3a88cad695df1248ca50286a19a033a8c` without changing this plugin's QA ownership or independent-review policy. Research and workflow replay results are recorded in `docs/reports/2026-10-07-lazycodex-refresh/` in the marketplace repository.

Version 1.15.0 adds source-informed component selection to `omo-frontend`: route by surface and tone, inspect at most two catalogs, check source/dependencies and current reuse terms, then pass the mechanism, token mapping, and missing accessibility or lifecycle behavior to the implementer. Existing local primitives need no external search. Product use and redistribution in a starter or component library are checked separately. Unavailable sources get an explicit local or original fallback, and fetched documentation cannot authorize commands or project-file uploads. The plugin still does not auto-install dependencies.

Version 1.4.0 folds the owner's former personal skills and agents into existing omo skills, so there is one place for each workflow. Only content the plugin lacked was merged, rewritten to use plugin agents only:

- `omo-guardrails`: circuit-breaker thresholds, error classification and escalation, context and handoff rules (`references/`).
- `omo-orchestrate` and `omo-coordinator`: intent routing map, ambiguity thresholds, codebase-state table, and the full delegation prompt template (`references/routing.md`, `references/delegation-prompt.md`).
- `omo-plan`, `omo-planner`, `omo-plan-consultant`, `omo-plan-reviewer`: optional six-lane rigorous plan review, `RISK_LEVEL` table, required F1 to F4 final verification wave, readiness checklist, and approval-biased reviewer framing (`references/rigorous-review.md`).
- `omo-implementer`, `omo-researcher`, `omo-reviewer`, `omo-debugging`: execution and final-report rules, search method, review checklist with severity scale, and multi-signal error analysis.
- `omo-handoff`, `omo-ralph-loop`, `omo-ultrawork`: resume summary, iteration guards with stuck detection, and implementer brief contract.
- `omo-get-unpublished-changes`, `omo-pre-publish-review`: baseline detection per ecosystem, report template, and three-layer parallel release review.
- `omo-remove-ai-slop`, `omo-programming`: comment pattern catalog and modular-code defaults that yield to project conventions.

Version 1.14.0 makes loops end on numbers and stop for the right reason. When a goal is a quantity ("reduce", "faster", "fewer"), `omo-ralph-loop` and `omo-ultrawork` define the metric command, a re-measured baseline, and a target before iteration 1, asking the user for the target when only a direction was given. They prefer deterministic measures such as counts and bytes over wall-clock time, compare timing only as same-machine medians beyond the baseline spread, log the value every iteration, and treat gaming the metric (rule or threshold changes, suppression, benchmark or test edits) as a defect. A stuck loop now classifies its cause before acting: missing context gets the missing spec or a pinning test, missing access stops at once and asks for that access, and work beyond reach consults `omo-oracle` once and hands off. `omo-plan` and `omo-planner` add a bounded exhaustive check for specs with interleaved shared state, role × action × state permissions, or interacting numeric constraints (model check, table test, solver, or property-based test, with a fallback when no tool is installed), prove the check can fail, and turn counterexamples into regression tests (`omo-plan/references/exhaustive-checks.md`).

Version 1.13.0 lets implementation skills enter ultrawork on their own judgment. When `omo-implement`, `omo-refactor`, `omo-debugging`, `omo-remove-ai-slop`, `omo-remove-deadcode`, or `omo-frontend` is invoked standalone, it sizes the task and escalates to `omo-ultrawork` when the change spans 3+ files or several surfaces, touches migration, performance, security, persistence, or public behavior, needs a multi-step plan, follows a failed attempt, or the user asked for rigor. Trivial, wording-only, and read-only tasks, and explicit requests for a light pass, stay in the original skill. A skill delegated by an active controller never escalates, so controllers do not nest. The rules live in `omo-ultrawork/references/auto-escalation.md`.

Version 1.12.0 runs an installed external review skill at every final gate, not only in `omo-review-loop`. `omo-ultrawork`, `omo-ulw-execute`, `omo-mass-ulw`, and direct `omo-ralph-loop` tasks now reuse the outer gate's external review: `self-review` in review-only mode when installed, else `review-pr` in LOCAL DIFF MODE, else a recorded skip, or the plan's `REVIEW_SKILL`. The built-in `omo-review-work` or `omo-reviewer` gate still always runs, and approval needs both. External `must` and `should` findings return to the Ralph loop as fix directives, so fixes keep one owner and one budget. The outer gate now reads the external report's `must` / `should` / `ask` sections instead of the old `Critical` label. The `ulw` keyword hook now ignores background task notifications and system reminders, so a sub-agent report that mentions `ultrawork` no longer starts the mode.

Version 1.11.0 adds three review and implementation rules. Review (`omo-review`, `omo-reviewer`) first checks the spec itself for contradictions and undefined cases, and builds a risk map for modified existing code: hidden reach such as indirect references, queued work, persisted data, and outside consumers, with the guardrail and business impact of each, plus the places a human should understand before merging. Tests follow the change scale: implementation and planning (`omo-implement`, `omo-implementer`, `omo-plan`, `omo-planner`, `omo-plan-consultant`) work test-first only when the change touches branching, calculations, state, data writes, parsing, contracts, or a bug fix, and skip TDD for wording, docs, renames, and config values.

Version 1.10.1 makes base-update routing run the Git safety assessment before local merge and conflict handling, and clarifies that `omo-git-master` owns local Git work while an external operator handles remote GitHub actions.

Version 1.10.0 makes PR follow-ups that bring in the base branch check what came with it. `omo-work-with-pr` diffs the merged base range for shared code that duplicates the branch's own logic (it recommends adopting it or not, with the reason, and does not move code unasked) and for base docs the branch now contradicts (fixed in the PR), and the done report states the result. `omo-git-master` routes conflict fixes and branch updates to its conflict steps and merges instead of rebasing once the branch is pushed. Final reports from `omo-implementer` and the `omo-review-loop` summary now open with the purpose, the design intent with rejected alternatives, and the verified outcome.

Version 1.9.0 adds scoped exploration, evidence invalidation with blast-radius completion, and pre-fix failure proof. Acceptance criteria now name the exact invocation, binary observable, and evidence; review rejects overfit or tautological tests; planning starts from fresh single-plan input; and prose and prompts receive semantic QA. `omo-visual-qa` now owns visual dimensions through capture-integrity, mode, motion, and checklist rules. Runtime-only hooks, task, thread, and gateway changes remain excluded.

Version 1.8.0 adds a follow-up section to `omo-work-with-pr`. Review responses, conflict resolution, and refactors added after a PR is opened are reviewed again on the cumulative branch diff; the PR body is compared against that diff for unexplained files, stale statements, and out-of-scope items that leave the protected user-visible behavior unclear; docs are re-checked; and runtime changes get a real-surface check. Replies follow the user's conversation language even when the delegated request is in another language. `hooks/json-error-recovery.mjs` no longer fires on successful `Agent` / `Task` calls, whose echoed prompts and transcripts often quote JSON error strings.

Version 1.7.0 adds review checks for invariant ownership, test-double realism, and blast radius to `omo-reviewer` and `omo-review`, so a class's own rule is enforced at its entry point, stubs do not hide call wiring, and changes to error types, detection scope, or out-of-diff callers are disclosed. On the implementation side, `omo-programming`, `omo-refactor`, and `omo-ultrawork` now require rules to be enforced by their owning class instead of a distributed mixin, a sweep of every invocation path when a precondition tightens, and manual QA that never triggers real external side effects. `omo-review` also maps findings onto the `omo-reviewer` severity scale, records non-approval outcomes in the reply when no ledger exists, and returns `REQUEST_CHANGES` rather than `INCONCLUSIVE` when confirmed blockers coexist with evidence gaps, while `omo-reviewer` treats a review of someone else's patch as mid-work analysis.

Version 1.6.0 unifies implementation/review continuation under `omo-ralph-loop`: one global iteration count, preserved resume state, and mandatory independent approval even for empty diffs or oracle disputes. Existing review artifact names remain readable; exhausted legacy runs require an explicit budget grant before continuing.

Version 1.5.0 continues this: `omo-frontend` is new, `omo-plan` gains a single-task task-file format (`references/task-file.md`), `omo-orchestrate` gains discovery of other agents' rule files (`references/project-rules.md`), and `omo-review-loop` checks earlier run artifacts before resuming, so a loop that stopped on a blocker is never resumed silently. A second hook, `hooks/json-error-recovery.mjs` (PostToolUse and PostToolUseFailure), tells Claude to fix malformed JSON tool arguments and retry once instead of repeating the same call.

## Ulw Keyword Trigger

Version 1.2.0 ports the upstream `ultrawork` UserPromptSubmit hook and the keyword rules from `docs/guide/keywords.md`. Put a keyword anywhere in a message and the hook injects an `<ultrawork-mode>` block that tells Claude to print `ULTRAWORK MODE ENABLED!`, open a binding `# Goal` block, and load the matching skill before any other work.

| Keyword | Skill loaded |
| --- | --- |
| `ulw` or `ultrawork` | `omo-ultrawork` |
| `ulw plan` | `omo-plan` |
| `ulw research` | `omo-ultraresearch` |
| `ulw loop` | `omo-ralph-loop` |
| `ulw execute` | `omo-ulw-execute` |
| `mass ulw` (also `ulw mass`, `mulw`) | `omo-mass-ulw`, or both skills when combined with another mode |

Text the user pasted (`<pasted_content>` blocks) is ignored, so a pasted report that mentions `ulw` does not start a mode. Detection rules match upstream: case does not matter; a space, a hyphen, or no gap all count (`ulw-plan`, `ulwplan`); only whole ASCII words count, so `ulwx` does nothing while `ulwで` still triggers; text inside `inline code` or a fenced code block is ignored. If the user is only discussing the keyword, the injected block tells Claude to carry on normally. Keywords combine: `mass ulw research` loads `omo-ultraresearch` together with `omo-mass-ulw`.

The hook is `hooks/hooks.json` plus `hooks/ulw-keyword.mjs`: a dependency-free Node script that reads the hook JSON from stdin, writes `hookSpecificOutput.additionalContext` only on a match, never touches the network or files, and exits 0 on any input. It needs `node` on `PATH`; without it the hook silently does nothing and `/omo-ultrawork` still works manually.

Quick check:

```bash
printf '%s' '{"hook_event_name":"UserPromptSubmit","prompt":"ulw fix the tests"}' | node omo-orchestrator/hooks/ulw-keyword.mjs
```

## Pre-flight And Review Gate

Version 1.20.0 adds two hooks so that hidden impact gets checked even when the user never asks for planning or review. Version 1.21.0 makes the gate read changed files from git instead of only the transcript.

- `hooks/preflight.mjs` (UserPromptSubmit): when a prompt asks for a code change (Japanese or English change verbs such as 実装, 修正, fix, add, refactor), it injects a short `<omo-preflight>` checklist: who else is affected, up to three undefined or contradictory cases, and a caller search for every existing unit about to change. Large or risky changes are pointed at `omo-implement`, which escalates to ultrawork. When a prompt asks for a review (レビュー, 監査, review, audit), it instead tells Claude to load `omo-review`, the single review entry, and to follow each changed value past the diff: who reads a status the change now writes, what the old failure path did, and whether a repeated call is safe. A model does not choose `omo-review` on its own for a plain review request, so this routing is what makes review requests use it. Prompts that name a reviewer (`review-pr`, `code-review`, `self-review`), slash commands, and prompts with a `ulw` keyword are left alone. Version 1.25.0 adds a third route, checked first: when the prompt carries a link to a PR review thread (`/pull/<n>#discussion_r<id>`, `#pullrequestreview-<id>`) or a review thread id (`PRRT_...`), even inside pasted content, it points Claude at the follow-up section of `omo-work-with-pr` and asks for an `omo-review` run on the whole branch diff, one reply draft per handled comment, and a PR body draft before the work is called done. Review tools hand over the comments to address as a paste, and fixes made that way used to end with "should I also review, update the body, or reply?". Apart from that route, text inside code spans, injected system or task blocks, and pasted content (`<pasted_content>`) is ignored. Pasted content still counts as user input for turn tracking. Tests: `node --test omo-orchestrator/hooks/pasted.test.mjs`.
- `hooks/review-gate.mjs` (Stop): when the current turn changed 2 or more files inside the working directory and no review skill or reviewer, oracle, or security-check agent ran after the last edit, it blocks the stop once. The reason asks Claude for a light review: a risk map of hidden reach for modified units, undefined cases, and the checks actually run, with `omo-review` for 3+ files, public or CLI behavior, persistence, or security. The follow-up stop carries `stop_hook_active` and always passes, so the gate cannot loop. A background task notification continues the same turn and stops again without that flag; the gate then passes as long as its own feedback already follows the last edit, so it asks once per edit. A `!` shell command the user runs also continues the turn, since it fires no prompt hook and the snapshot stays at the last prompt. Files under `.claude/omo/` and outside the working directory do not count.
- `hooks/turn-snapshot.mjs`: on every user prompt, `preflight.mjs` records the git state (HEAD plus a hash of each already-changed file) under `$TMPDIR/omo-orchestrator/turns/`. The gate compares the tree against it, so edits made through Bash, scripts, or sub-agents count, a file that was already dirty counts only when the turn changed it again, and commits made during the turn still count. Background task notifications do not start a new snapshot. Outside a git work tree the gate falls back to the transcript's Edit and Write calls.

Limits: a review that runs while edits are still coming from Bash counts until the next transcript-visible edit. The gate's own feedback counts the same way, so edits made after it through Bash or a sub-agent other than an implementer or builder are not asked about again in that turn.

Settings (environment variables):

- `OMO_PREFLIGHT=off`: disable the pre-flight checklist.
- `OMO_REVIEW_GATE=off`: disable the review gate.
- `OMO_REVIEW_GATE_MIN_FILES=<n>`: number of edited files that triggers the gate (default 2).
- `OMO_SNAPSHOT_DIR=<dir>`: where turn snapshots are kept (default `$TMPDIR/omo-orchestrator`).

The scripts are dependency-free Node, never touch the network, write only the snapshot file, run git read-only commands with a 2-second timeout, and exit 0 on any input.

Quick check:

```bash
printf '%s' '{"hook_event_name":"UserPromptSubmit","prompt":"fix the retry logic"}' | node omo-orchestrator/hooks/preflight.mjs
```

## Impact Script

Version 1.23.0 adds `scripts/impact.mjs`, a dependency-free Node script that answers "who references this, and which tests cover it" in a few lines. It runs `git grep -w -F --untracked` from the repository root, without a shell, and never writes files. Tests: `node --test omo-orchestrator/scripts/impact.test.mjs`.

```bash
node omo-orchestrator/scripts/impact.mjs --symbol saveSnapshot   # callers and tests of a symbol
node omo-orchestrator/scripts/impact.mjs --file src/auth/login.ts  # files that mention the module name
node omo-orchestrator/scripts/impact.mjs --base main               # every changed code file against main
```

A chain of Grep and Read calls puts every match into the conversation, and those bytes are resent on every later turn. The script returns counts, `path (n: L10,L22)` entries, and test files, capped by `--limit` (default 15). It matches words, not a call graph: dynamic access and names built at runtime still need Grep or LSP references, and literal text such as messages belongs to Grep. The pre-flight hook, `omo-research`, and `omo-researcher` point to it for caller and impact questions. Version 1.23.0 also adds the `omo-handoff` fresh-session brief and an Orca CLI launch for the next session.

## Single Review Entry

Version 1.21.0 makes `omo-review` the one place to ask for a review. It runs two lanes in parallel on the same frozen tree: an `omo-reviewer` agent with the omo review areas (or `omo-review-work` when real-surface QA evidence is needed), and the `self-review` skill in review-only mode through a sub-agent when that skill is installed. The stricter verdict decides, and fixes happen after both return. Version 1.24.0 changes the standalone `omo-review` order: the `omo-reviewer` lane runs first on the unchanged tree, then an `omo-external-reviewer` agent runs `self-review` in its normal mode, which fixes the findings (including the omo lane's, passed as focus notes) and re-reviews. Controller final gates keep `self-review` in review-only mode with `--dry-run`, because Ralph owns fixes there. omo no longer runs `review-pr` at all: it is for GitHub PRs, and only the user invokes it. A plan can still skip `self-review` with `REVIEW_SKILL: none`. `omo-review-work` is now an internal gate stage (`user-invocable: false`), and `omo-review-loop` stays the entry for implement-plus-review loops.

Every final gate in the controllers (`omo-review-loop`, `omo-ultrawork`, `omo-ulw-execute`, `omo-mass-ulw`, `omo-ralph-loop`) now always runs `self-review` alongside `omo-review-work` or `omo-reviewer`. `review-pr` is no longer a fallback when `self-review` is missing. From 1.21.0 to 1.23.x it ran only when the user asked for it, as an extra lane; 1.24.0 removed that lane.

## Evals

`evals/` holds `claude plugin eval` cases that measure whether the plugin finds impact the user did not ask about. Each case builds a small git repository with a scaffold script, and LLM graders check one hidden concern each.

- `hidden-impact-rename` (implementation): a one-line request to rename a setting key. The key is also reached through names that `grep` for the key misses (an environment variable derived from it, a snake_case CSV import column), plus stored data and a public API field.
- `design-merge-users` (design): add a function that merges users with the same email. Emails differ in case and whitespace, several users have no email, and orders point at user ids.
- `review-retry-change` (review): review a commit that adds retries to a billing job. The payment client can time out after capturing a charge, and the scheduler only bills `pending` invoices, so marking one `failed` drops it for good.

```bash
cd omo-orchestrator
claude plugin eval . --scaffold --trust-plugin --no-publish --threshold 0 \
  --model claude-sonnet-5-5 --allow-tools Bash Edit Write
```

The run compares the plugin against a no-plugin baseline by default. Results go to `evals/results/` (git-ignored). To see what one hook contributes, copy the plugin, remove that hook from the copy's `hooks/hooks.json` (or prefix the command with `OMO_PREFLIGHT=off`), and run the copy with `--ablation none`.

## Included Agents

- `omo-coordinator`: intent routing, delegation, state tracking, and completion checks. Uses `model: opus`, `effort: medium` because orchestration quality is high leverage.
- `omo-planner`: executable plans, affected-user ideal states, gap closure, blockers, and QA mappings. Uses `model: opus`, `effort: medium` because planning quality is high leverage.
- `omo-implementer`: deep executor for minimal verified changes. Uses `model: sonnet`, `effort: high`; callers pass `model: opus` for multi-file work with a real integration surface.
- `omo-researcher`: the Explore equivalent for read-only codebase investigation, with evidence labels and access limits disclosed. External library, upstream source, and dependency-history questions go to `omo-librarian`. Uses `model: haiku`, `effort: low`; callers pass `model: sonnet` when the task needs bug hypotheses rather than location.
- `omo-plan-consultant`: read-only pre-planning consultant for intent classification, exploration, affected-user ideal-state gaps, and planning directives. Uses `model: sonnet`, `effort: high`.
- `omo-plan-reviewer`: read-only plan executability reviewer with an approval-biased `OKAY` or `REJECT` verdict. Uses `model: sonnet`, `effort: medium`.
- `omo-reviewer`: independent implementation and PR-style reviewer for risk, quality, and scope control. Its lifecycle remains `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`. Uses `model: opus`, `effort: medium`. In `omo-review-loop`, the alignment, quality, and evidence-gate lanes override it to `model: sonnet`; the security and robustness lanes and the final gate stay on Opus.
- `omo-oracle`: read-only strategic advisor for architecture decisions, debugging that has already failed repeatedly, post-implementation self-review, and security or performance tradeoffs. Gives one recommendation with an effort estimate. Uses `model: fable`, `effort: high` because the consultation is the deliverable and reasoning depth is the whole point. If Fable refuses (for example on a security topic), the caller re-runs the consult once with `model: opus`.
- `omo-librarian`: read-only external source researcher for unfamiliar libraries and dependency history. Requires permalinks or versioned documentation URLs for every claim. Uses `model: sonnet`, `effort: medium`.
- `omo-external-reviewer`: runs the installed `self-review` skill with the caller's contract, without preloading any skill, and returns the verdict, findings verbatim, report path, and changed files (by content hash, checked against the skill's fix log). In fix mode it reports the re-review verdict and allows edits only to files in the diff and new tests; in both modes it never commits, pushes, stashes, switches branches, or posts. It inherits the caller's model, `effort: medium`. `omo-review` and the controller final gates dispatch it in place of a general-purpose agent.
- `omo-media-reader`: read-only interpreter for PDFs, images, and diagrams. Extracts only what was asked so the caller never loads the raw file. Uses `model: sonnet`, `effort: medium`; callers pass `model: opus` for dense charts or diagrams.

## Model Guidance

Agent model hints are enforced through agent frontmatter where Claude Code supports it. Skills are prompt content, so their model guidance is advisory unless a caller chooses the model explicitly.

Pick the cheapest tier that can do the job, and escalate with a one-line reason:

- **Haiku**: low-risk, mechanical work. Read-only code location, simple git or CLI operations, metadata checks, and narrow documentation lookups. Not for planning, orchestration, implementation, or skeptical review.
- **Sonnet**: the default workhorse. Implementation, external research, plan review, media extraction, and the lower-risk review lanes. Cap effort at `xhigh`; at `max` Sonnet can over-delegate and score worse.
- **Opus** (`effort: medium`): judgment and integration. Orchestration, planning, security and robustness review, the final review gate, and multi-file implementation with a real integration surface.
- **Fable** (`effort: high`): the high-stakes consult. `omo-oracle` only, for architecture decisions and debugging that has already failed repeatedly. Fall back to Opus on a refusal.

Override the frontmatter per call with the Agent tool's `model` parameter when a task is clearly above or below the agent's default.

Haiku is sufficient for routine use of these prompt-only skills when the task is narrow and evidence-based:

- `omo-guardrails`
- `omo-programming`
- `omo-research`
- `omo-start-work`
- `omo-coding-agent-sessions`

Use Sonnet or stronger for `omo-ultraresearch` (decision-critical research) and `omo-visual-qa` (visual judgment).

## Claude Code Adaptation Scope

This plugin adapts useful LazyCodex OMO ideas into Claude Code prompts only. It keeps the OMO shape, but translates runtime-driven behavior into manual skill and agent behavior that works in a local Claude Code session.

### Upstream Snapshot

The portable contracts in version 1.0.0 were refreshed against `oh-my-openagent` commit `0c76f2d9838a664884739877da1692aa754eab1a`. Version 1.2.0 re-checked `3d8cf52b673fcbf4dd9d34361a273b791a19c2e5` (upstream `dev`, OmO 5.1.4): skill and prompt bodies were unchanged apart from `argument-hint` additions, so the refresh adds the ultrawork directive to `omo-ultrawork`, ports the `ulw` keyword hook, and ports the previously unported upstream skills `ulw-execute`, `mass-ulw`, `tech-debt-audit`, `ast-grep`, and `lsp-setup`. Runtime-bound upstream skills (browser automation, team mode, DAG library, onboarding, publish) remain out of scope. The refresh carries planning intent routing, affected-user ideal-state and gap mapping, plan executability review, dependency-aware parallel waves, bounded follow-up and research-lead convergence, discovered-work discipline, evidence-led handoffs with manual TodoWrite and ledger equivalence, session transcript and accounting distinctions, real-surface visual QA with fresh evidence, one independent final reviewer, adversarial plan distillation, exploitability-first security research, and release ownership gates.

Version 1.9.0 compares the portable prompt contracts against `oh-my-openagent` commit `b9463e692f93aa49bb10d306c0c6f1ade54f7840`. Runtime-only hooks, task, thread, and gateway changes remain excluded.

Version 1.15.0 re-checks `d55d03485041170e6bcb4cb6ba4365d1a18afbd0` (upstream `dev`, package version 5.1.21). It adapts the new frontend catalog exploration and reuse checks. The model-specific Astra ultrawork/DAG verification directives and task, gateway, memory, and installer changes remain runtime-specific and are not ported. Catalog names are discovery starting points; their current licenses must be inspected at use time. The evaluation protocol and results are in `docs/reports/2026-10-07-omo-upstream-refresh/` in the marketplace repository.

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

- No runtime hooks such as SessionStart, PreToolUse, PostCompact, SubagentStop, or Stop. The only hooks are the UserPromptSubmit `ulw` keyword trigger and the PostToolUse / PostToolUseFailure JSON argument recovery hint; both only inject guidance text.
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

For implementation tasks, prefer `/omo-plan` before editing and `/omo-review` before final handoff. Initialize or reuse `/omo-ralph-loop` as the sole implementation/review controller; every repair pass reserves the next shared iteration before editing. The mandatory final gate returns `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`. Only `APPROVE` permits completion. `REQUEST_CHANGES` returns to the same Ralph budget for a fix and re-review; `INCONCLUSIVE` blocks completion until the missing evidence or decision is recorded and resolved. Bounded local tool recovery never grants another implementation/review budget.

For release or PR work, run `/omo-get-unpublished-changes` before `/omo-pre-publish-review`, then use `/omo-work-with-pr` to prepare a local handoff or reviewer-response artifact. GitHub changes and every publish, push, merge, or remote comment are outside these content-only skills and require an external operator with explicit permission for the specific action.

## Planning And Review Gates

- `omo-plan-consultant` classifies intent, explores before asking, and records affected users, concrete `IS-*` ideal states, and `GAP-*` shortfalls. `omo-planner` then creates one plan that closes every gap and maps every ideal state to a task, executable QA scenario, and evidence location. Clear plans ask only for irreducible owner decisions. Unclear plans research and announce practical defaults before the approval brief. Plan approval never authorizes implementation.
- `omo-plan-reviewer` checks plan references, task startability, QA executability, ideal-state coverage, and gap closure. It returns `OKAY` by default and `REJECT` only for verified blockers. It is not a substitute for `omo-reviewer`.
- `omo-ultraresearch` expands only leads with stated decision impact, source, owner, and bounded budget. Research converges when the evidence threshold is met, remaining leads are non-material, or further searches repeat known evidence.
- `omo-start-work` treats manual TodoWrite state and the latest append-only ledger entry as equivalent views of the same work state. Compare them before dispatch, handoff, retry, review, and completion; correct disagreement with the current TodoWrite item and a new ledger entry, never by rewriting history.
- Plans should include TL;DR, affected users, `IS-*` and `GAP-*` rows, dependencies, QA scenarios, task closure, gap classification, and verification strategy.
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

## Planning Role Migration

Version 1.0.0 adopts the canonical names: `omo-plan-consultant` for pre-planning analysis and `omo-plan-reviewer` for plan executability review. The retired `omo-metis` agent is removed and has no compatibility alias.

OpenCode has legacy metis and momus names in its own adapter. They are not aliases in this Claude Code plugin. Use `omo-plan-consultant` and `omo-plan-reviewer` for planning, then use `omo-reviewer` only for implementation or PR-style review.

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

- The only scripts are `hooks/ulw-keyword.mjs` and `hooks/json-error-recovery.mjs`, which read stdin and write stdout only.
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
  'omo-plan-consultant',
  'omo-plan-reviewer',
  'Affected users',
  '`IS-*`',
  '`GAP-*`',
  'closes every gap',
  'task, executable QA scenario, and evidence location',
  '`OKAY`',
  '`REJECT`',
  'the Explore equivalent',
  '`omo-oracle`',
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
  'Schema-1 manifests from 0.11.0, 0.12.0, and 1.0.0 are accepted',
  '0.11.0 and 0.12.0 manifests upgrade to 1.0.0 only on approved writes',
  '0c76f2d9838a664884739877da1692aa754eab1a',
  '3d8cf52b673fcbf4dd9d34361a273b791a19c2e5',
  'ulw-keyword.mjs',
  'ULTRAWORK MODE ENABLED!',
  '`omo-ulw-execute`',
  '`omo-mass-ulw`',
  '`omo-tech-debt-audit`',
  '`omo-ast-grep`',
  '`omo-lsp-setup`',
  '`omo-review-loop`',
  '`omo-frontend`',
  'json-error-recovery.mjs',
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

## Development QA

Before relying on `omo-init-deep`, walk its contract in disposable `mktemp` Git repositories and worktrees, never in the plugin repository. Check fresh local and committed runs, denied confirmation, byte-identical rerun, both mode transitions, manual edits, approved and denied `--create-new` deletion, unowned managed-directory files, malformed and duplicate exclude markers, tracked output, linked worktrees, invalid depth, symlink and traversal rejection, sensitive data omission, prompt injection resistance, capability gaps, unborn and dirty repositories, and `/context` or `InstructionsLoaded` uncertainty.

This QA checks the written contract. It does not prove a separate Claude session ran the skill.
