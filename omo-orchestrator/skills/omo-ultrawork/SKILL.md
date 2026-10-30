---
name: omo-ultrawork
description: Ultrawork (ulw) mode. Plans, delegates parallel waves to sub-agents, verifies on the real surface, and keeps going until done. Use when the user says ulw or ultrawork. Modes: ulw-execute (ulw execute, run a written omo plan wave by wave), mass-ulw (mass ulw, mulw, fan-out where some tasks wait on others).
argument-hint: [mode] [goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task, Skill, AskUserQuestion
user-invocable: true
---

# OMO Ultrawork

Claude Code adaptation of the oh-my-openagent ultrawork directive (`packages/prompts-core/prompts/ultrawork/default.md`). The `ulw` / `ultrawork` keyword hook in this plugin points here. Every rule below binds for the whole task.

Implementation skills can also enter this mode without the keyword; the decision rules are in `references/auto-escalation.md`.

Before implementation, initialize or reuse `omo-ralph-loop` for this task. Reuse its ledger, global iteration (default cap 20), review base, and blocker history. Each initial wave or repair pass reserves one iteration; final QA/review belongs to the current pass. Apply Ralph's resume checks and never reset state on feedback or a gate failure.

Load `omo-guardrails` with the Skill tool before the first dispatch or edit; other sections cite its rules by name only.

## Modes

Mode selection, in order:

1. The first argument word is a mode name or alias from the table: use that mode.
2. The brief carries a `MODES: omo-ultrawork/<mode>` line: use that mode.
3. Otherwise match the triggers in the table. No match: follow the default flow in the rest of this file. An unknown first word is part of the goal, not a mode.

Mode files live at `${CLAUDE_SKILL_DIR}/modes/<mode>/MODE.md`. If the variable is not expanded, use the Base directory shown when this skill was loaded plus `modes/<mode>/`. A bare `references/…` path inside a MODE.md is relative to that mode's directory; a path qualified with another skill name is relative to that skill's directory; `skills/<name>/…` is relative to the plugin root.

| Mode | Alias | Precedence | Use when |
|---|---|---|---|
| `ulw-execute` | - | replaces this file's flow | `ulw execute`, run a written omo plan wave by wave |
| `mass-ulw` | `mulw` | replaces this file's flow | mass ulw, mulw, fan-out where some tasks wait on others |

"Replaces" means: read the MODE.md and follow it as the procedure; the rest of this file applies only where the MODE.md names it.

When `ulw-execute` and `mass-ulw` are both requested, `ulw-execute` is the procedure and `mass-ulw` only supplies how to split waves.

## Bootstrap

1. The first user-visible line is exactly `ULTRAWORK MODE ENABLED!`.
2. Open with a binding `# Goal` block, written outcome-first: what will be TRUE when done (an outcome, never an activity), the named deliverable surfaces, the scenario contract as success criteria (binary observables that can fail), explicit scope bounds, and one line `I'll stop right away when <observable state>`. Never invent a budget or deadline the user did not state. When the goal is a quantity ("reduce", "faster", "fewer"), a criterion is a metric with command, baseline, and target, set up per `omo-ralph-loop` `references/iteration-guards.md` § Measured Goals.
3. Survey the skills. Read the description of every skill even loosely relevant, decide which apply, and state the chosen skills and agents with a one-line reason each before acting. A matching skill that goes unused is a defect.

## Certainty Before Implementation

Do not write code until you understand what the user actually wants, how the existing code works, and exactly which files change.

- Delegate exploration when scope warrants it: use parallel `omo-researcher` (codebase) and `omo-librarian` (external libraries, upstream source) agents for unclear, multi-surface, risky, or upstream-dependent work. For trivial, fully understood scope, confirm the context directly.
- Consult `omo-oracle` for hard problems and after 2 failed fix attempts on the same problem, not on a first attempt. After those 2 failures, also run the debug rescue Codex consult in `skills/omo-orchestrate/references/codex-consult.md` in parallel. After 3 consecutive failures, stop editing, revert to the last working state, document each attempt, consult `omo-oracle` (and Codex again when its first consult did not resolve it), and ask the user if it is still unresolved.
- When an `omo-oracle` reply ends with `ESCALATE: fable — <point>`, re-run the same consult once with `model: "fable"` without asking. Attach the Opus answer and the point, say it is the Fable re-run, and use its answer. If Fable refuses or fails, keep the Opus answer.
- When the work is sized `HEAVY` or contains an architecture decision, send the plan to `omo-oracle` before the first implementation wave: the goal, the files and changes per task, and the specific uncertainties. Ask it to check the approach, missed issues, and a simpler path. In parallel, run the plan critique Codex consult in `skills/omo-orchestrate/references/codex-consult.md` on the same plan. Fold both answers' confirmed findings into the plan; do not implement a decision `omo-oracle` was asked to settle before it answers. A Codex consult that reports `codex-consult: NOT_EXECUTED` does not block: continue with the `omo-oracle` answer alone. Skip this for `LIGHT` work.
- If ambiguity remains after exploration, ask the user. Do not guess.
- When the user settled a decision in the conversation before `ulw`, restate your reading in the `# Goal` block as `Decided: <A>, not <B>` whenever the wording allows a second reading (keep or remove, all or a filtered subset, this change or a later issue). Keep these lines in the ledger, open each progress or done report with them, and do not re-propose an option the user rejected. Misreading "leave the delete as is for now" as "remove it later" cost five rounds of correction.

You are not ready while you are making assumptions about requirements, are unsure which files to modify, or your plan contains "probably" or "maybe".

## Plan Agent (Non-Trivial Work)

Size the scope first: count distinct surfaces, files, and steps. Any task with 2+ steps, multiple files, unclear scope, or an architecture decision requires `omo-planner` (use `omo-plan-consultant` first when intent is unclear). When an approved `omo-plan` for this task exists in the conversation or a plan file, use it as the plan and skip the planner and the `omo-plan-reviewer` pass below; `omo-plan` already reviewed it. Execute in the exact wave order and parallel grouping the plan specifies, and run the verification it defines for each task. Use `SendMessage` to continue the same planner for clarifications or refinements instead of spawning a fresh one. When the plan is saved to a file (`.claude/omo/plans/*.md`), run `omo-plan-reviewer` once on that path before the first wave; skip it for inline plans and todo lists.

## Delegate By Default

The main context orchestrates. It does not implement unless the change is trivial (1-2 obvious lines with all context loaded).

| Task type | Owner |
|---|---|
| Codebase exploration | `omo-researcher`, in parallel |
| Documentation or upstream lookup | `omo-librarian`, in parallel |
| Planning | `omo-planner` |
| Hard problem, architecture, 2+ failed fix attempts | `omo-oracle` |
| Implementation | `omo-implementer`, one owner per independent file set |
| PDFs, images, diagrams | `omo-media-reader` |
| Review gate | `omo-reviewer` |
| Research that writes files, long command-driven verification | see `omo-orchestrate` `references/routing.md` |

Do not dispatch `general-purpose` or a skill runner without `model: "sonnet"` (or `"haiku"` for read-only); they otherwise inherit the main model. Every brief that runs commands carries the work budget from `omo-guardrails` `references/context-and-handoff.md`.

Every brief to a gated worker (`omo-implementer`, `omo-researcher`, `omo-reviewer`, `omo-planner`) carries a `LOAD_SKILLS` line chosen from `omo-orchestrate` `references/skill-catalog.md`; a PreToolUse hook denies the dispatch otherwise.

Every `omo-implementer` brief is self-contained: goal, files to modify, implementation approach with the existing pattern to copy (file:line), a binary `Done when`, and the real-surface QA design approved by `omo-implement` `references/real-surface-qa.md` (Design and Review) before dispatch. Without `Done when` the executor has no exit.

Parallelize independent agent calls in one message. Read before change, never in parallel with it. Serialize same-file writes, shared mutable state, shared contracts, and named predecessors. Size the work as `LIGHT` or `HEAVY` once and only ratchet toward `HEAVY` when risk grows.

## Execution Rules

### Task Resources

Before the first task command, create and record one owned scratch root with `RUN_TMP=$(mktemp -d)`. Register its cleanup TODO immediately, before using it. For task commands, export `TMPDIR="$RUN_TMP" NODE_COMPILE_CACHE="$RUN_TMP/node-compile-cache" BUN_RUNTIME_TRANSPILER_CACHE_PATH="$RUN_TMP/bun-transpiler"`. A new shell does not retain exports: set them in each command invocation, and pass them explicitly to children that do not inherit the environment. Independent child tasks create and record their own roots; these variables do not redirect every tool's cache, so record any additional owned cache paths separately.

- At creation, add a cleanup TODO for every owned worktree, cache, PID, port, tmux session, browser context, container, script, and temporary path. Record its exact identity and owner. Keep these TODOs when reconciling the plan or resuming after interruption.
- Capture durable evidence and the handoff ledger outside disposable roots. If evidence was captured inside a root, copy it to the recorded durable location and verify it is readable before deleting the original. The durable notepad is retained for handoff.
- Tear down QA resources before recording a scenario as complete; remove the run root and eligible worktrees at task end, after owned processes exit. A teardown command's exit status alone is insufficient: record a read-back receipt, such as PID absent, port unbound, context closed, or exact temporary path absent. Distinguish absence from a permission error or failed inspection tool; an inconclusive probe leaves cleanup pending. Check the recorded launch identity before stopping a PID that could have been reused. No receipt leaves its cleanup TODO pending.
- Remove only resources whose task ownership is established. Never wipe shared caches, user files, foreign resources, or a parent directory containing retained resources. Worktrees are created only when the user requests them; preserve a worktree needed by an open PR, another task, or an explicit handoff, record why it is retained and who owns its next action, and remove other owned worktrees only under the authorized Git lifecycle. Unknown ownership blocks that deletion, not independent work.

- TODO format: `path: <action> for <scenario-id> - verify by <check>`. Exactly one `in_progress` at a time. Mark completed immediately; never batch. Rewrite vague items such as "Implement feature" or "Fix bug".
- Bounded follow-up: if a delegated track stalls, do one follow-up pass, then record the gap and stop waiting.
- Do not duplicate research once an agent owns that question.
- Do not mark a wave complete until the executor's done claim is checked against its declared evidence.
- Re-read the original request after completion and check every scenario.

## Scenario Contract

Before writing code, define realistic scenarios sized to the change: 1-2 for a small single-surface change, 3+ for multi-surface or risky work.

| Class | Required | Example |
|---|---|---|
| Happy path | always | valid input returns 200 with the expected body |
| Edge (boundary, empty, malformed, concurrent) | when risky | empty list, max-length input, two writers race |
| Adjacent-surface regression | when multi-surface | caller X still works, sibling endpoint Y unchanged |

Each scenario states upfront a binary pass condition, the real surface that proves it (CLI stdout, curl status and body, browser assertion, tmux transcript, parsed config, DB diff), and the existing tests that cover it. You are not done until every scenario passes with its artifact captured.

## Durable Notepad

Create once at start in the durable repository handoff directory: create `.claude/omo/handoffs/` if absent, then run `NOTE=$(mktemp "$PWD/.claude/omo/handoffs/ulw-notepad.XXXXXX")` and record the returned absolute path. This explicit directory keeps the notepad outside `$RUN_TMP` even after `TMPDIR` is exported. Retain it for handoff; append, never rewrite:

```text
# Ultrawork Notepad - <one-line goal>
Started: <ISO timestamp>

## Plan (exhaustive, atomic)
## Scenarios (the contract)
## Now (single step in progress)
## Todo (remaining, ordered)
## Findings (non-obvious facts with file:line refs)
## Learnings (patterns and pitfalls)
```

After compaction or context loss, re-read the notepad and resume. For work that spans sessions, also use `omo-handoff`.

## Evidence

Every scenario needs evidence from both applicable lanes:

- Tests of record: the existing suite for the area, read before the change and green after it when such tests exist.
- User-surface artifact: what the user actually sees, captured by running it when a runnable surface exists. For prose, documentation, or prompts with no runnable surface, use semantic inspection or a blank-slate scenario trace that proves the intended reader or agent behavior without pinning exact wording.

Build exit 0, full suite green, and clean diagnostics are supporting evidence, not sufficient. "Tests pass" alone is not done. A test that pins prose or visual text is not evidence.

Evidence stays valid until one of its inputs changes. When a change affects an importer, scenario, dependency, or other blast-radius path, rerun each affected check before one final complete scenario set. Treat every defect inside that blast radius as current work. Record defects outside it as findings, but do not mark their criteria passed.

## Manual QA Is Mandatory

| If the change... | You must... |
|---|---|
| Adds or modifies a CLI command | Run it with Bash and show the output |
| Changes build output | Run the build and inspect the output files |
| Modifies API behavior | Call the endpoint and show the response |
| Changes UI or a TUI layout | Use `omo-visual-qa` on the rendered surface |
| Adds a tool, hook, or feature | Exercise it end-to-end in a real scenario |
| Modifies config handling | Load the config and verify it parses |
| Touches a path with an external side effect (upload, outbound send, payment, write to a third party) | Do not trigger the real effect: replace the boundary in-process, drive the path with fixed fake data, and report the range that could not be verified |

Name the exact tool and invocation with concrete inputs for every scenario. "This should work", "the types check out", and "tests pass" are not QA. Cleanup is part of the task: register teardown TODOs at resource creation under Task Resources, verify QA teardown before closing the scenario, and finish task-directory teardown before done. Retained handoff resources need the owner and reason recorded there.

## Test Decision

1. Read the tests covering the area before touching it. A wrong test is a finding to report; never edit a test green. Reproduce a bug before fixing it.
2. Make the smallest change that meets the scenario and update tests it makes stale. Add a test only when the repository keeps tests for this behavior and a regression would otherwise pass unnoticed.
3. Exercise the real surface named by the scenario and record the artifact path in the notepad.
4. Reconcile the full scenario list plus the step-1 tests against the final inputs. Run every missing or affected check; reuse an unchanged row only under `omo-review` mode `review-work` Evidence Reuse, recording its current provenance. Record pass or fail for the complete set with evidence. A full scenario set does not require repeating independently valid rows.

Prose, documentation, and prompt changes take semantic review plus real-surface QA only when a runnable surface exists; do not add tests that pin wording. Visual-only changes still require rendered-surface QA.

## Commits

When the user or project allows commits, commit one atomic, verified increment at a time, never one end-of-run omnibus. Before each message, run `git log --oneline -20` and `git log -5 -- <touched paths>` and match subject shape, scope, language, and body style. Use `omo-git-master` for the workflow. Never push, publish, or merge without explicit permission.

## Reviewer Gate

Run this gate for every ulw task, whatever its size: ultrawork means implement, review, and fix until the review approves. A one-file change gets the same gate; only the review effort scales with the diff.

1. In parallel with this gate, run the external review on the task-wide diff from the Ralph review base, following `omo-review` `modes/review-loop/references/outer-gate.md` § 6b (`self-review` review-only, unless the plan sets `REVIEW_SKILL: none`; a missing skill is a recorded skip) and its section for other entry skills. Read its report by § 6c and merge it with this gate's outcome by § 6d. Approval needs both to clear.
2. Spawn `omo-reviewer` with the goal, scenarios, evidence, diff, and notepad path.
3. Verify each concern yourself. A concern blocks only when it names a success criterion the evidence fails; others are notes.
4. Return criterion-cited blockers to Ralph and reserve the next shared iteration before dispatching any fix. In that pass, fix the blockers, re-run the affected scenario QA, and update the notepad.
5. In that same iteration, submit the updated task-wide diff and current QA evidence to a fresh independent reviewer. Approval with non-blocking notes counts as approval.
6. Return every repair/re-review pass to the active `omo-ralph-loop` ledger and shared remaining budget. Ralph alone decides cap exhaustion and stuck stops; do not grant a separate final-gate retry budget.

## Zero Tolerance

- No scope reduction: no demo, skeleton, simplified, or basic versions.
- No mock work: port A means port A fully, with no extra and no missing features.
- No partial completion or "you can extend this later".
- No skipping requirements you consider optional.
- No premature stopping: done means every TODO completed and verified.
- No test deletion or skipping to make the build pass.
- No silence treated as success, and no skipped QA gate because parallel work finished fast.

If you hit a blocker, do not deliver a compromised version: explore alternatives, consult `omo-oracle`, or ask the user. The user asked for X. Deliver exactly X.
