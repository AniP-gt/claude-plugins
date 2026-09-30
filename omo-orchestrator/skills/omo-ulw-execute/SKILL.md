---
name: omo-ulw-execute
description: Runs a written omo plan wave by wave via sub-agents with an evidence ledger, verified done claims, and a final review gate. Use when the user says ulw execute or asks to run a written omo plan.
argument-hint: [plan-path]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task
user-invocable: true
---

# OMO ULW Execute

Claude Code adaptation of oh-my-openagent `packages/shared-skills/skills/ulw-execute`. The `ulw execute` keyword hook in this plugin points here. Every rule below binds until the plan is complete or a stop condition fires.

This is a manual, content-only workflow. It has no Boulder state, no continuation hook, and no automatic resume. Progress lives in TodoWrite, the plan file, and the handoff ledger, and the operator keeps driving until done.

## Absolute Rule: Orchestrator, Never Implementer

You do not write product code, edit product files, write tests, or run QA yourself. Every unit of implementation, test, QA, and review work goes to a sub-agent through the `Task` tool.

Your hands touch only: plan selection, plan checkboxes, TodoWrite, the handoff ledger, decomposition, dispatch, verdicts, and evidence records. About to edit a product file or run an implementation command? Stop and dispatch a worker instead.

Run at maximum safe parallelism: every independent unit is dispatched in one message; only named dependencies, same-file writes, shared contracts, and shared mutable state serialize.

## Usage

```text
/omo-ulw-execute [plan-path]
```

- `plan-path` (optional): a plan file, usually `.claude/omo/plans/<task-slug>.md` written by `omo-plan`, or any file the user names.
- Invoking this skill is the explicit kickoff authorization that `omo-plan` and `omo-start-work` require. It authorizes executing the approved plan, nothing outside it.

## Phase 1: Select The Plan

1. If `plan-path` was given, read it.
2. Otherwise list `.claude/omo/plans/` and read `.claude/omo/handoffs/` for an active ledger whose source plan is unfinished.
3. Exactly one unfinished ledger or exactly one plan: select it. Several candidates: ask one focused selection question.
4. No plan, or only a brief without waves, tasks, and acceptance criteria: the brief is not decision-complete. Run `omo-plan` for the request, follow its approval gate, and continue here only after the user approves the plan. Do not invent an unapproved plan to keep moving.
5. Before dispatch, check the plan is executable: exact files, per-task acceptance criteria, dependencies, and QA commands. For a large or risky plan with no prior review, run `omo-plan-reviewer` once. A `REJECT` with a critical finding stops execution and returns to `omo-plan`.

## Phase 2: Goal, Todos, And Ledger

Do all of this before the first dispatch.

1. **Goal.** Record a detailed objective: plan path, concrete end state, wave and task counts, delivery mode (local changes only unless the user asked for more), and how completion is verified.
2. **Todos.** Mirror the plan into TodoWrite: one item per top-level task (column-zero checkbox or task row), plus the final verification wave. Register every item up front. Use the format `path: <action> for <task-id> - verify by <check>`.
3. **Ledger.** Create or reconcile `.claude/omo/handoffs/<task-slug>.md` per `omo-handoff`. Append a kickoff entry with the goal, plan path, waves, owners, dependencies, evidence targets, risks, and first exact action. If the ledger exists, read it fully and resume from its latest next exact action.
4. **Keep them in sync.** Mark a todo `in_progress` when its work dispatches and `completed` only after verification passes. Never batch-complete. TodoWrite, plan checkboxes, and the latest ledger entry must tell the same story at every boundary (dispatch, verify, review, stop).
5. **Discovered work.** A pre-existing bug, failing test, stale doc, or wrong guidance found mid-run is recorded in the ledger, assessed against the plan scope, and either added as a plan task and todo before it runs, or explicitly deferred with a reason. Workers report out-of-scope defects; only the orchestrator adds and dispatches them.

## Phase 3: Execute The Next Wave

1. Re-read the full plan. Find the first wave with unfinished tasks. Ignore nested checkboxes under acceptance criteria, evidence, or definition-of-done sections.
2. Record the wave goal (its tasks and their acceptance criteria) as a ledger entry before its first dispatch.
3. Classify each task `LIGHT` (narrow change inside existing layers) or `HEAVY` (new module or abstraction, auth or security, external integration, schema or migration, concurrency, cross-domain refactor, or the plan asks for care). When unsure, take `HEAVY`. Upgrade the moment a `HEAVY` fact surfaces; never downgrade.
4. Decompose each task into atomic sub-tasks sized for one worker in one run. A sub-task that would need mid-flight steering is two sub-tasks.
5. Dispatch every independent sub-task in the wave in one message with multiple `Task` calls. Dependent sub-tasks wait for their predecessor's verified result.

### Delegation Router

If the plan names an owner for a task, follow it and record any deviation with a reason. Otherwise:

| Shape | Agent |
|---|---|
| Mechanical, single-file, config, copy, docs | `omo-implementer`, split into many small parallel workers |
| Standard feature across a few files with known patterns | `omo-implementer`, one owner per independent file set |
| Hard, cohesive problem (one algorithm, one migration, one subtle bug) | one `omo-implementer` with the whole problem; consult `omo-oracle` first when the central decision is a trade-off or invariant argument |
| Missing codebase fact | `omo-researcher` |
| Missing external or upstream fact | `omo-librarian` |
| PDF, image, or diagram input | `omo-media-reader` |
| Verification and review | `omo-reviewer` |

Splittable work splits. Cohesive hard work stays whole; never force-split parts that share one insight.

### Sub-Task Message

Each dispatch is self-contained and includes:

1. Goal and the exact files or directories in scope.
2. Tests already covering the behavior, to be read before any edit as the behavior of record. For a bug, the reproduction to capture before the fix. Add a test only when the repository keeps tests for this behavior and a regression would otherwise pass unnoticed.
3. Constraints from the plan and project rules (`omo-programming`, `omo-implement`).
4. Automated verification commands to run.
5. One manual QA channel with the exact tool, invocation, input, and binary PASS/FAIL observable: `curl -i` against a live endpoint, a real CLI run with its stdout, a tmux session for a TUI, `omo-visual-qa` for rendered UI, a parsed config dump, or a DB state diff. Never "verify it works".
6. The adversarial classes that apply (below) and how each is probed.
7. Required artifact path and cleanup receipt.
8. The expected return: a done claim in the shape defined in Phase 4.

### Adversarial Classes

A class applies when its trigger holds. Probe each applicable class; record the rest as not applicable with a one-line reason.

| Trigger | Class |
|---|---|
| New input parsing | malformed input |
| Untrusted external text | prompt injection |
| Resumable or long-running flow | cancel and resume |
| Generated or cached artifacts | stale state |
| Uncommitted user files in scope | dirty worktree |
| Long external commands | hung or long command |
| New or timing-sensitive tests | flaky test |
| Log-based success claim | misleading success output |
| Mid-operation interrupts | repeated interruption |

### Waiting On Workers

- Each `Task` result is the lane's completion signal. Do not sleep, poll, or re-read status hoping it changed.
- If a worker stalls or returns without its deliverable, do one bounded follow-up with `SendMessage` to the same agent. If that fails, record the gap as inconclusive (never a pass) and dispatch a smaller, fresh sub-task for the missing deliverable.
- Any process, port, tmux session, browser context, container, or temp dir a worker spawns gets a teardown todo that is executed and receipted before the task closes.

## Phase 4: Verify Every Done Claim

A worker done claim is never final. Each implementation sub-task returns:

```text
DONE CLAIM
task: <task id and title>
changed_files: <paths>
tests: <exact command and result>
manual_qa: <artifact path or captured output>
adversarial: <class: observed result | class: not applicable, reason>
cleanup: <receipts>
risks: <known risk or none>
```

Then a different context verifies it. Dispatch `omo-reviewer` (fresh, read-only) with the plan task, acceptance criteria, diff, and claimed evidence. It reruns or reproduces the claim and returns:

```text
VERIFY
verdict: confirmed | false-positive | needs-fix | needs-human-review
evidence: <file, command, log, artifact, or "not inspected">
repro: <exact command or steps>
```

- `confirmed` is the only pass. Every other verdict blocks the task.
- The verifier must be independent of the executor. You may verify yourself only if you neither implemented nor materially rewrote that task, and only by reading and rerunning, never by editing.
- The verifier probes the applicable adversarial classes, always including stale state, dirty worktree, and misleading success output when their triggers hold.
- On a non-confirmed verdict: append the feedback to the ledger, reset the todo to `in_progress`, and re-dispatch the executor with the exact failure. Use `omo-oracle` after two failed attempts on the same task.

Each task passes five gates before it closes: plan reread against acceptance criteria, automated verification, manual QA artifact, adversarial probes, and cleanup receipts.

## Phase 5: Mark Progress

Only after the verifier returns `confirmed`:

1. Edit the plan checkbox from `- [ ]` to `- [x]`, or mark the task row done in the plan's own convention.
2. Mark the todo `completed`.
3. Append a task-completed ledger entry with changed files, commands and results, QA artifact, adversarial results, cleanup receipts, and the next exact action.
4. Re-read the plan, confirm the remaining count dropped, and continue with the next task or wave. Do not ask whether to continue.

## Phase 6: Final Verification And Review Gate

When every task and the final verification wave are done:

1. Dispatch a worker to run the plan's final verification commands and the full scenario list against the final tree.
2. Run `omo-review-work` on the full diff with the goal, plan, QA matrix, and ledger. It launches one fresh independent reviewer and returns exactly one outcome:
   - `APPROVE`: the sole completion state.
   - `REQUEST_CHANGES`: append the findings to the ledger, add each as a bounded fix task and todo, execute and verify it through Phases 3 to 5, then re-run this gate with a fresh reviewer. At most two re-review rounds.
   - `INCONCLUSIVE`: append the missing evidence and why it is unavailable. Obtain it and re-run, or stop with the blocker recorded.
3. On `APPROVE`, append the final ledger entry and print:

```text
ORCHESTRATION COMPLETE
plan: <path>
verification: <commands and results>
artifacts: <paths>
cleanup: <receipts>
review: APPROVE (<reviewer evidence>)
```

## Delivery And Git Boundaries

- Default delivery is local changes in the current checkout. Use a git worktree only when the user asks for one; then run every edit, command, and QA step inside it and record its absolute path in the ledger.
- Commit only when the user or project allows it, one verified atomic increment at a time, via `omo-git-master`.
- A request to open or ship a PR prepares a local handoff only: branch state, commit list, PR title and body draft, check commands, and review evidence, as in `omo-work-with-pr`. Never push, publish, merge, or comment remotely without explicit user permission.
- Only the orchestrator decides landing order when lanes conflict. Workers never resolve a sibling's conflict blind.

## Stop Conditions

Stop, append a ledger entry with the blocker and one exact next action, and surface it to the user when:

- A blocker needs an owner decision, credentials, or external approval.
- A required dependency or tool stays unavailable after one bounded follow-up.
- The same confirmed blocker survives two fix attempts and an `omo-oracle` consult.
- `REQUEST_CHANGES` findings remain after two re-review rounds.
- The plan is wrong or contradicted by the code in a way that changes scope; return to `omo-plan` instead of improvising.

Everything else is not a stop: keep executing.

## Hard Rules

- No production change before the covering tests were read and, for a bug, the reproduction captured. A test that contradicts the intent is a finding, never edited green.
- No `--dry-run` or tests-only claim as completion evidence. A manual QA artifact is required.
- No completion while an applicable adversarial class was never probed.
- No direct implementation, test writing, or QA by the orchestrator.
- No scope reduction, skeletons, or "extend later". Deliver the plan as written.
- No silence, stalled output, or a finished parallel wave treated as success.
- No stale-memory execution. After compaction or a pause, the plan file and the ledger are the source of truth; read both before acting.
