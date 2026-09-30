# omo-mass-ulw planning reference

Claude Code adaptation of oh-my-openagent `packages/omo-senpi/skills/mass-ulw/references/planning.md`. Read in full before defining any graph. Every section exists because its absence was observed failing: unplanned runs collapse into three big tasks with no verification.

## Decomposition Doctrine

**Topology lock first.** Before writing any task, list the 1-6 top-level components that can each succeed or fail independently. Every task traces to exactly one component. Do not collapse a multi-component request into one blob task because it looks small, and do not invent components the request does not have.

**Split first, route second.** The default question is not "which owner does this chunk need" but "how do I turn this chunk into more small tasks". When pieces have disjoint write scopes, self-contained prompts, and can each be verified alone, many small tasks in parallel beat one big task on a stronger model. They finish sooner, fail in isolation, and cost less. Reserve stronger owners for what survives splitting.

**Do not split when:**

1. The pieces share a write scope you cannot untangle. Serialize or merge instead of pretending independence.
2. The work is one coherent judgment that needs the whole problem in view (a design decision, a root-cause diagnosis). Splitting it produces confident partial answers.
3. A task would take longer to brief than to execute. Fold it into its neighbor.

**Wave sizing.** One task per genuinely independent chunk, whether five or sixty. Fewer than 3 in a wave usually means under-splitting. Never merge independent chunks to make a wave look smaller. Split along the axis that makes pieces independent:

- By component: each independently shippable part is its own lane.
- By file domain: one component spanning disjoint file sets gets one task per set.
- By phase: collect (investigate in parallel), verify (falsify the collections), synthesize (turn verified facts into the deliverable).

**Default shape is fan-out, then fan-in.** N parallel lanes with no dependencies, then one synthesis task depending on all of them. Merging verified pieces is mechanical unless the merge itself needs judgment, so the synthesis owner starts cheap too.

**Mass harvests: tasks are not items.** When a scan must cover hundreds or thousands of files or sources, shard items into tasks. Each task owns a batch (roughly 50-200 items) and writes one bounded report file (a few thousand tokens at most) to a ledger path. Chain phases when one wave is not enough, with an aggregator per phase, so synthesis reads digests, never raw outputs.

**Do not split implementation from its test.** One task owns one deliverable end to end: the change and its proof. A code-only task and a test-only task serialize on the same files and double coordination.

## Owner Routing

Start every task at the cheapest owner that can do it. Escalate only with a one-line reason you could say out loud ("touches six files across three packages"), and only after the split-first doctrine has been applied.

| Upstream category | Claude Code owner | Use when |
|---|---|---|
| `quick` (default) | `omo-researcher` for read-only; `omo-implementer` with `model: sonnet` for mechanical edits | Single file, pattern-following, batch scans |
| `unspecified-low` | `omo-implementer` | A few files, or a judgment call a template cannot make |
| `unspecified-high` | `omo-implementer` with `model: opus` | Standard multi-file feature or fix with real integration surface |
| `writing` | `omo-implementer` with a prose-only scope | Docs, README, technical writing |
| `visual-engineering` | `omo-implementer`, then `omo-visual-qa` | Frontend, UI, styling |
| `git` | `omo-implementer` following `omo-git-master` | Git operations only |
| external lookup | `omo-librarian` | Upstream source, library docs |
| media | `omo-media-reader` | PDFs, images, diagrams |
| `deep-*` / `ultrabrain` | `omo-oracle` | Hairy cross-module reasoning or a trade-off evidence cannot settle. At most one per graph for the single hardest decision everything else depends on |
| review | `omo-reviewer` | Verification and final gate |

A graph where every task goes to the strongest owner is a routing failure: it overpays mechanical lanes and starves the one lane that needed the horsepower. Honor the user's literal routing words ("all quick", "deep") exactly.

## Concurrency And Write Scope

- `depends_on` is ordering only. Every prompt stands alone.
- **Disjoint write scopes or serialize.** No two tasks in the same wave edit the same file or shared state (lockfile, generated index, shared config, DB schema, the same manifest). If two lanes must touch the same files, chain them or merge them.
- **Never add an edge to pass a fact you already know.** Paste it into the prompt and leave the edge out. Add an edge only when B consumes something A produces.
- Parallel implementers editing overlapping trees can use `isolation: "worktree"` on the Agent call; the coordinator then owns the merge as its own serialized task with a verification step.
- Dependency self-check before wave 1: every id exists, no cycles, no edge without a consumed output, every wave has a runnable task.

## Task Prompt Contract

A task prompt is the only thing the sub-agent sees. It has no conversation history and cannot ask you questions. Write it so a competent stranger executes it exactly. In this order:

1. **TASK**: one imperative sentence naming the deliverable.
2. **DELIVERABLE**: files changed, the exact report shape, the evidence produced.
3. **SCOPE**: what it may read and write, with exact paths, as a hard boundary. Name what is out of scope when a sibling task owns it.
4. **VERIFY**: the literal command it runs on its own work and the expected result.
5. **STOP WHEN**: the single observable condition that ends the task.

Rules that make prompts obeyed:

- Self-contained. Paste paths, facts, and constraints in. "As discussed above" is a dangling reference.
- Minimum sufficient context. Every pasted fact must change what the task does.
- Binary observables: "exit code 0 and `dist/index.js` exists", never "check it works".
- Positive framing. Say what to do. Reserve NEVER / ONLY for true invariants (do not commit, do not edit outside scope).
- One role per task. A task that investigates does not also fix; a task that writes does not review its own work.
- When embedding an upstream output, quote or summarize the relevant part. Unbounded pastes drown the prompt.

Treat any prompt missing TASK or STOP WHEN, or a graph with no verification task, as a defect to fix before dispatch.

## Verification Wave

- Every graph that changes code ends with at least one verification task depending on all producers.
- It runs the real check (test, build, endpoint call) and reports captured output. Its prompt names the exact invocation and the binary observable that decides PASS or FAIL.
- Paginated deliverables (PDF, DOCX, deck, print HTML) are verified by rendering every page and inspecting each for blank pages, bad breaks, split tables, and clipped text. Sampling is not verification.
- Task outputs are claims until verified. A downstream task that builds on an upstream result re-checks the specific facts it depends on (file exists, test passes, symbol exported) before trusting them.

## Failure Playbook

- **A failed task blocks only its dependents.** Read its error first, then recover that task in place. Never rebuild the whole graph.
- **Retry first.** Re-dispatch only the failed task, with an edited prompt when the failure shows what was missing. Dependents stay pending until it verifies.
- **Amend when the definition was wrong.** Rewrite or split the bad task, then re-run it plus its transitive dependents. Verified unaffected tasks keep their results.
- **SendMessage when the agent is alive but stuck or needs context.** Continuing the same agent keeps its context. If it cannot be continued, retry with a fresh dispatch.
- **Start-time storms.** If many tasks in one wave fail within seconds without doing work, the environment or tool is failing, not the prompts. Stop dispatching, fix the cause, then retry the failed set.
- **Verify a completion claim before trusting it.** A task that returns a report saying it was blocked has not completed. Retry it.
- **Abandon only when the goal is abandoned.** Record the reason in the ledger.
- Retry budget: one initial attempt plus at most two materially different retries per task, then stop and surface the blocker.

## Mass Research

When the user combines the mass trigger with research ("mass ulw research", "mulw research"), run the harvest as phased waves and follow `omo-ultraresearch` for its evidence contract and convergence rules.

- Wave 1 over-collects: enumerate every angle (source territory, sub-question, entity, time window, competing approach) and give each its own task. Coverage is the deliverable.
- Route across the owner table in one graph; one owner tier across every task is the routing failure above.
- Each wave's leads define the next wave's tasks. Deduplicate against leads already seen and stop when new waves repeat known evidence.
- Synthesis reduces through several parallel slice tasks reading bounded digests, then one final reducer (`omo-oracle` when the merge needs judgment). Never hand dozens of raw outputs to one task.
