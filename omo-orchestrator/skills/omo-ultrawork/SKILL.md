---
name: omo-ultrawork
description: Ultrawork (ulw) mode. Plans, delegates parallel waves to sub-agents, verifies on the real surface, and keeps going until done. Use when the user says ulw or ultrawork.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task
user-invocable: true
---

# OMO Ultrawork

Claude Code adaptation of the oh-my-openagent ultrawork directive (`packages/prompts-core/prompts/ultrawork/default.md`). The `ulw` / `ultrawork` keyword hook in this plugin points here. Every rule below binds for the whole task.

Implementation skills can also enter this mode without the keyword; the decision rules are in `references/auto-escalation.md`.

Before implementation, initialize or reuse `omo-ralph-loop` for this task. Reuse its ledger, global iteration (default cap 20), review base, and blocker history. Each initial wave or repair pass reserves one iteration; final QA/review belongs to the current pass. Apply Ralph's resume checks and never reset state on feedback or a gate failure.

## Bootstrap

1. The first user-visible line is exactly `ULTRAWORK MODE ENABLED!`.
2. Open with a binding `# Goal` block, written outcome-first: what will be TRUE when done (an outcome, never an activity), the named deliverable surfaces, the scenario contract as success criteria (binary observables that can fail), explicit scope bounds, and one line `I'll stop right away when <observable state>`. Never invent a budget or deadline the user did not state. When the goal is a quantity ("reduce", "faster", "fewer"), a criterion is a metric with command, baseline, and target, set up per `omo-ralph-loop` `references/iteration-guards.md` § Measured Goals.
3. Survey the skills. Read the description of every skill even loosely relevant, decide which apply, and state the chosen skills and agents with a one-line reason each before acting. A matching skill that goes unused is a defect.

## Certainty Before Implementation

Do not write code until you understand what the user actually wants, how the existing code works, and exactly which files change.

- Delegate exploration when scope warrants it: use parallel `omo-researcher` (codebase) and `omo-librarian` (external libraries, upstream source) agents for unclear, multi-surface, risky, or upstream-dependent work. For trivial, fully understood scope, confirm the context directly.
- For hard problems, consult `omo-oracle` instead of struggling alone.
- If ambiguity remains after exploration, ask the user. Do not guess.

You are not ready while you are making assumptions about requirements, are unsure which files to modify, or your plan contains "probably" or "maybe".

## Plan Agent (Non-Trivial Work)

Size the scope first: count distinct surfaces, files, and steps. Any task with 2+ steps, multiple files, unclear scope, or an architecture decision requires `omo-planner` (use `omo-plan-consultant` first when intent is unclear). Execute in the exact wave order and parallel grouping the plan specifies, and run the verification it defines for each task. Use `SendMessage` to continue the same planner for clarifications or refinements instead of spawning a fresh one.

## Delegate By Default

The main context orchestrates. It does not implement unless the change is trivial (1-2 obvious lines with all context loaded).

| Task type | Owner |
|---|---|
| Codebase exploration | `omo-researcher`, in parallel |
| Documentation or upstream lookup | `omo-librarian`, in parallel |
| Planning | `omo-planner` |
| Hard problem, architecture, repeated failures | `omo-oracle` |
| Implementation | `omo-implementer`, one owner per independent file set |
| PDFs, images, diagrams | `omo-media-reader` |
| Review gate | `omo-reviewer` |

Every `omo-implementer` brief is self-contained: goal, files to modify, implementation approach with the existing pattern to copy (file:line), and a binary `Done when`. Without `Done when` the executor has no exit.

Parallelize independent agent calls in one message. Read before change, never in parallel with it. Serialize same-file writes, shared mutable state, shared contracts, and named predecessors. Size the work as `LIGHT` or `HEAVY` once and only ratchet toward `HEAVY` when risk grows.

## Execution Rules

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

Create once at start: `NOTE=$(mktemp -t ulw-$(date +%Y%m%d-%H%M%S).XXXXXX.md)` and echo the path. Append, never rewrite:

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

Name the exact tool and invocation with concrete inputs for every scenario. "This should work", "the types check out", and "tests pass" are not QA. Cleanup is part of QA: every spawned process, port, tmux session, browser context, container, or temp dir gets a teardown TODO that is executed before done.

## Test Decision

1. Read the tests covering the area before touching it. A wrong test is a finding to report; never edit a test green. Reproduce a bug before fixing it.
2. Make the smallest change that meets the scenario and update tests it makes stale. Add a test only when the repository keeps tests for this behavior and a regression would otherwise pass unnoticed.
3. Exercise the real surface named by the scenario and record the artifact path in the notepad.
4. Re-run the full scenario list plus the step-1 tests and record pass or fail with evidence.

Prose, documentation, and prompt changes take semantic review plus real-surface QA only when a runnable surface exists; do not add tests that pin wording. Visual-only changes still require rendered-surface QA.

## Commits

When the user or project allows commits, commit one atomic, verified increment at a time, never one end-of-run omnibus. Before each message, run `git log --oneline -20` and `git log -5 -- <touched paths>` and match subject shape, scope, language, and body style. Use `omo-git-master` for the workflow. Never push, publish, or merge without explicit permission.

## Reviewer Gate

Trigger when any apply: the user asked for rigor ("strictly", "rigorously", "厳密", "深く"), the task touches 3+ files or ran long, or it is refactor, migration, performance, security, persistence, or public-behavior work.

1. Before this gate, run the external review on the task-wide diff from the Ralph review base, following the `omo-review-loop` skill's `references/outer-gate.md` § 6b (which skill runs: the plan's `REVIEW_SKILL`, else `self-review` review-only, else `review-pr` in LOCAL DIFF MODE, else a recorded skip) and its section for other entry skills. Read its report by § 6c and merge it with this gate's outcome by § 6d. Approval needs both to clear.
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
