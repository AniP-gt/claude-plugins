---
name: omo-mass-ulw
description: Mass ultrawork. Splits a job into a dependency-ordered task graph and runs ready waves in parallel. Use when the user says mass ulw / mulw or asks for fan-out work where some tasks wait on others.
argument-hint: [task]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task
user-invocable: true
---

# OMO Mass Ultrawork

Claude Code adaptation of oh-my-openagent `packages/omo-senpi/skills/mass-ulw`. The `mass ulw` / `mulw` / `ulw mass` keywords point here. Every `omo-ultrawork` rule (goal block, certainty before implementation, evidence, manual QA, zero tolerance) still binds; this skill adds how the work is decomposed into a task graph, run wave by wave, and recovered.

Use it when real dependencies exist: task C needs A and B finished first. For fully independent work, plain parallel agent calls under `omo-ultrawork` are simpler. A graph with two tasks and no edge between them is not a graph.

Before implementation, initialize or reuse `omo-ralph-loop` for this task. Reuse its ledger, global iteration (default cap 20), review base, and blocker history. Each initial wave or repair pass reserves one iteration; final QA/review belongs to the current pass. Apply Ralph's resume checks and never reset state on feedback or a gate failure.

## Planning First

Before defining any task, read [planning.md](references/planning.md) in full. It holds the decomposition doctrine, owner routing, write-scope rules, the task prompt contract, the verification wave, and the failure playbook. A graph built without it is unplanned work.

Then write the run plan in one pass and execute that plan: components, tasks, waves, the owner and one-line reason for every non-default owner, and the verification wave. When reality forces a change, replan out loud instead of drifting task by task.

## Bootstrap

1. The first user-visible line is exactly `MASS ULTRAWORK MODE ENABLED!`.
2. Open with the `# Goal` block from `omo-ultrawork`. Success criteria carry result verification: every task and run completion claim is false until proven against captured evidence. The run ends when the criteria pass, never when the last task reports done.
3. Explore with parallel `omo-researcher` / `omo-librarian` calls until the file sets and dependencies are known. Do not build a graph on guesses.

## The Graph

Each task has:

- `id`: short stable slug (`api-auth`, `docs-rewrite`).
- `owner`: the sub-agent that runs it, chosen from the routing table in planning.md.
- `depends_on`: ids that must be verified complete first. Ordering only: nothing from an upstream result is injected automatically, so each prompt must stand alone. When a downstream task needs a verified upstream fact, the coordinator pastes it into that task's prompt at dispatch.
- `scope`: exact read and write paths. Parallel tasks never share a write path.
- `success`: a binary observable and the command or surface that proves it.

Self-check before wave 1: every dependency id exists, no cycles, no edge without a consumed output, every wave has a runnable task, no two tasks in one wave write the same file or shared state.

Record the graph in TodoWrite, one item per task: `<id> [wave N, deps: a,b] <path>: <action> - verify by <check>`. For multi-phase or long runs, also keep the `omo-handoff` ledger at `.claude/omo/handoffs/<task-slug>.md` with the graph, per-task status, and evidence paths, so a new context can resume without redoing verified tasks.

## Running Waves

Default runtime: one message per wave containing one Agent tool call per ready task. Each task is owned by exactly one sub-agent (`omo-implementer`, `omo-researcher`, `omo-librarian`, `omo-reviewer`, `omo-oracle`, `omo-media-reader`).

1. Compute the ready set: tasks whose dependencies are all verified complete.
2. State the independence justification for the wave in one line per task pair that could collide: disjoint write paths, no shared contract, no shared mutable state. If you cannot justify it, serialize.
3. Dispatch the whole ready set in a single message. Do not dispatch a task whose predecessor is only reported done but not yet verified.
4. When results return, verify each task against its `success` observable before marking it complete. Read the output; a worker that reports being blocked has not completed.
5. Update TodoWrite and the ledger, then compute the next ready set. Repeat until the graph is exhausted.

Very wide waves (more than ~10 tasks) fan in through aggregator tasks that read bounded per-task reports written to files. The coordinator never reads N raw outputs.

### Workflow tool rule

Claude Code also has a `Workflow` tool for deterministic multi-agent scripts. Use it ONLY when the user's own words explicitly ask for a workflow or multi-agent orchestration, or the user said `ultracode`. The `mass ulw` keyword alone does not authorize it. Without that explicit request, run waves as parallel Agent calls as above. When authorized, load `workflow-authoring` before writing the script and keep every rule in this skill (graph self-check, disjoint scopes, per-task verification, final gate).

## Supervision

Check each returned task against its own prompt's scope: the assigned work, only the assigned work, at the assigned depth. Writes outside scope, gold-plating past the deliverable, or circling one sub-problem is drift. Correct it with `SendMessage` to the same agent naming the exact boundary crossed. Drift caught in wave 1 costs one message; drift found at synthesis costs the run.

## Recovery

A failed task blocks only its dependents. Completed and verified tasks are never re-run.

| Situation | Move |
|---|---|
| Agent alive but stuck, off scope, or missing a fact | `SendMessage` to the same agent with the fact or boundary. Keeps its context. |
| Task failed or returned no usable result | Re-dispatch that task alone with a corrected prompt (retry). Dependents stay pending. |
| Task definition itself was wrong | Amend: rewrite that task's prompt or split it, then re-run it plus every transitive dependent. Verified unaffected tasks keep their results. |
| Many tasks in a wave fail at start within seconds | Environment or tool failure, not the prompts. Stop dispatching, fix the cause, retry the failed set. |
| Retry budget spent | Record every attempt in the ledger, stop, and surface the blocker. |

Every implementation repair or renewed review dispatch must reserve the next iteration in the same Ralph ledger before work starts. There is no separate per-task implementation retry cap. Bounded local tool recovery and one missing-output follow-up remain available within the current pass; neither authorizes another work pass or resets the shared budget. Elapsed time alone never justifies abandoning a running task.

## Verification Wave

Every graph that changes code ends with at least one verification task depending on all producer tasks. It runs the real check (test command, build, endpoint call, rendered surface) and reports captured output against the goal's success criteria. The synthesis task's own claim is not evidence. Paginated deliverables (PDF, deck, print HTML) are verified by inspecting every rendered page, not by file size or grep.

Then run the `omo-ultrawork` manual QA table on the real surface and re-read the original request against every criterion.

## Final Review Gate

Spawn `omo-reviewer` with the goal, graph, per-task evidence, diff, and ledger path. Outcomes:

- `APPROVE`: the only state that permits reporting done.
- `REQUEST_CHANGES`: each criterion-cited blocker becomes a new graph task with its own dependencies and success check. Return it to Ralph for the next repair iteration, re-verify affected tasks, and submit the task-wide diff and current evidence to a fresh independent reviewer.
- `INCONCLUSIVE`: name the missing evidence, add the task that produces it, and block completion until it exists.

Return every repair/re-review pass to the active `omo-ralph-loop` ledger and shared remaining budget. Ralph alone decides cap exhaustion and stuck stops; no separate final-gate retry budget.

## Report

Final report: graph summary (tasks, waves, owners), per-task status with evidence location, retries and amendments taken, verification output, review decision, changed files, and residual risks.

## Not Ported

Upstream runs on OmO's native dag runtime. These parts have no Claude Code equivalent and are intentionally absent: the `workflow` dag tool and JS SDK (`define`, `start`, `attach`, `snapshot`, `wait`, `cancel`), idempotent run keys and journaled auto-resume, `/dag` and desktop Workflows panels, RPC viewer channels, provider slot limiter and category model routing config, `team_create` teams, and automatic wake-driven continuation. Resume is manual: read the ledger, then continue from the first unverified task.
