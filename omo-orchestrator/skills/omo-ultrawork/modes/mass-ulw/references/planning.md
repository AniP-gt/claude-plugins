# `omo-ultrawork` mode `mass-ulw` planning reference

Claude Code adaptation of oh-my-openagent `packages/omo-senpi/skills/mass-ulw/references/planning.md`. Read in full before defining the first graph. Before dispatch, state the plan in a few lines: the tasks and the file each one writes, a reason for every owner above the cheapest, and the check that will prove the deliverable.

Sections: Sizing and Decomposition (graph size, splitting, chains, fan-in, review joins) · Owner Routing (category to sub-agent) · Concurrency And Write Scope (handoffs, disjoint writes) · Task Prompt Contract (TASK to STOP WHEN) · Verification (who runs the check, heavier patterns) · Failure Playbook (recovery moves) · Mass Research (angles, leads, verify, reduce).

## Sizing and Decomposition

**Scale to the ask.** "Look into X" or "fix these" gets a few tasks and a check the coordinator runs itself. "Thorough", "all of them", an audit, or mass research gets a wider fan-out and one of the heavier verification patterns below. A wave holds as many tasks as there are independent pieces; there is no minimum, and padding the list buys queue time, not coverage.

**One task per independent piece.** Trace each task to a part of the request that can succeed or fail on its own, and invent no parts the request does not have. Parallel small tasks beat one big task when the work divides into pieces with disjoint write scopes that can each be checked alone. Keep work in one task when:

1. The pieces share a write scope you cannot untangle. Serialize or merge instead of pretending independence.
2. The work is one coherent judgment that needs the whole problem in view (a design decision, a root-cause diagnosis). Splitting it produces confident partial answers.
3. A task would take longer to brief than to execute. Fold it into its neighbor.

Split along the axis that makes pieces independent: by component, by disjoint file set, or by stage (collect, expand, verify, synthesize). Put already-known stages inside the same phase graph; a phase ends at its acceptance checkpoint.

**Chain per item; hold a wave only for cross-item work.** When item i's next stage needs only item i's result, chain `a-i -> b-i` so each item moves on the moment it verifies and a slow item delays only itself. Make a stage wait for a whole wave only when it needs every result together: dedup or merge across the set, an early exit when nothing was found, a comparison between items.

**Fan in through files.** A fan-in or synthesis task reads the bounded report each producer wrote, never N raw outputs, and its owner starts cheap unless the merge itself needs judgment.

**Join adjacent waves through one review task.** When every consumer needs every producer's output together, use `producers -> shared review -> consumers`, rather than all-to-all edges. The review verifies the producers against their declared checks and gates the consumers. A consumer needing only A1 gets `A1 -> review-A1 -> consumer` and starts when that branch clears; it does not wait for unrelated producers. Compute readiness from verified dependencies as results return, rather than imposing a whole-wave barrier. Preserve any additional dependency explicitly required by the plan or shared state.

A review finding names the failed producer and criterion. Repair that producer under the shared Ralph iteration budget, rerun its affected verification and any already-run consumers whose evidence it invalidates, and retain verified independent results. A downstream task waiting on the shared review remains pending until all inputs it consumes are supported. Branch and shared reviews may reuse the same current QA evidence under `omo-review` mode `review-work` Evidence Reuse; they are dependency checks, not additional final-gate reviewer panels.

Declare each required dependency review in the graph before dispatch. The coordinator's artifact and identity check does not replace that review. In a harvest -> expand -> verify chain, the verify task reviews the expanded claims; add a branch review before expand when it consumes harvested facts, and a shared review before reduction when it consumes several verified branches. A stage already owned by an independent reviewer can itself satisfy that dependency review when its declared check covers every consumed input; do not add a duplicate review of the same evidence.

**Mass harvests: tasks are not items.** When a scan must cover hundreds or thousands of files or sources, shard items into tasks. Each task owns a batch (roughly 50-200 items) and writes one bounded report file (a few thousand tokens at most) to its declared handoff path. Define each batch's already-known harvest -> expand -> verify chain before dispatch, then fan in through an aggregator that reads verified digests, never raw outputs. More tasks than available agent slots means bounded dispatch batches, not a new phase. Add tasks after results only when newly found leads determine their scope; preserve verified independent branches.

**Do not split implementation from its test.** One task owns one deliverable end to end: the change and its proof. A code-only task and a test-only task serialize on the same files and double coordination.

## Owner Routing

Start every task at the cheapest owner that can do it. Escalate only with a one-line reason you could say out loud ("touches six files across three packages"). A chunk that splits into independent small tasks was never an escalation candidate.

| Upstream category | Claude Code owner | Use when |
|---|---|---|
| `quick` (default) | `omo-researcher` (haiku) for read-only; the Codex lane for mechanical edits when it applies, else `omo-implementer` (sonnet default) | Single file, pattern-following, batch scans |
| `unspecified-low` | the Codex lane when it applies, else `omo-implementer` (sonnet default) | A few files, or a judgment call a template cannot make |
| `unspecified-high` | the Codex lane when it applies, else `omo-implementer` with `model: opus` | Standard multi-file feature or fix with real integration surface, or a migration or performance optimization even with a clear spec |
| `writing` | the Codex lane when it applies, else `omo-implementer` with a prose-only scope | Docs, README, technical writing |
| `visual-engineering` | the Codex lane when it applies, else `omo-implementer`; then `omo-implement` mode `visual-qa` | Frontend, UI, styling. The controller puts the absolute MODE.md path for each requested mode in the worker brief (resolve `<plugin-root>` per `skills/omo-orchestrate/references/skill-catalog.md`). |
| `git` | `omo-implementer` following `omo-git-master` | Git operations only |
| external lookup | `omo-librarian` | Upstream source, library docs |
| media | Main context Reads PDFs/images directly (`pages` for PDFs); bulk extraction to `omo-researcher` | PDFs, images, diagrams |
| `deep-*` / `ultrabrain` | `omo-oracle` | Hairy cross-module reasoning or a trade-off evidence cannot settle. At most one per graph for the single hardest decision everything else depends on |
| review | `omo-reviewer` | Verification and final gate (the final gate adds `omo-security-reviewer` in parallel) |

The Codex lane is the protocol in `skills/omo-orchestrate/references/codex-implementer.md`; it applies inside Orca when an approved `omo-plan` exists or `omo-ultrawork` runs. Whenever an approved plan exists or ulw runs but the lane did not run (outside Orca included; a LIGHT change without a plan needs no record), dispatch `omo-implementer` and record `codex-impl: FALLBACK - <reason>`. Planned `writing` tasks (README, docs in the plan) go to the lane too; only research-lane prose-only wiki or docs writers stay with `omo-implementer` (`routing.md`). `git` stays with `omo-implementer` because Codex never makes commits. One Codex session per plan: Codex-owned tasks go to the same Codex tab in order, never parallel Codex tabs in one worktree, so they serialize even when ready together. While a Codex round runs, no task that writes to the working tree (the exempt prose-writer and git tasks included) runs in the same wave; it waits until the round ends, because Claude does not edit the tree during a Codex run and the post-run check would otherwise stop. Read-only lanes still fan out. A Codex result file is a done claim; a fresh `omo-reviewer` still verifies it.

Do not route a lane to `general-purpose` or a skill runner: they inherit the main session's model. When no owner above fits, pass `model: "sonnet"` on that Agent call. Every lane prompt carries the work budget from `omo-guardrails` `references/context-and-handoff.md`.

A graph where every task goes to the strongest owner is a routing failure: it overpays mechanical lanes and starves the one lane that needed the horsepower. Honor the user's literal routing words ("all quick", "deep") exactly.

## Concurrency And Write Scope

- **Dependencies order; handoffs carry data.** `depends_on` substitutes nothing into a prompt. For file handoffs, paste the producer's absolute output path into its prompt and the same input path into the consumer's prompt. Verify existence, current input identity, and the producer's acceptance evidence before release; a missing report is a failed handoff. Each producer owns only its declared report, not the coordinator's graph or journal. For reply handoffs, the coordinator embeds bounded verified facts at dispatch. Every prompt stands alone.
- **Disjoint write scopes or serialize.** No two tasks in the same wave edit the same file or shared state (lockfile, generated index, shared config, DB schema, the same manifest). If two lanes must touch the same files, chain them or merge them.
- **Never add an edge to pass a fact you already know.** Paste it into the prompt and leave the edge out. Add an edge only when B consumes something A produces.
- Only when the user requested worktrees, parallel implementers editing overlapping trees can use `isolation: "worktree"` on the Agent call; the coordinator then owns the merge as its own serialized task with a verification step. Otherwise serialize overlapping writes in the current checkout.
- Dependency self-check before wave 1: every id exists, no cycles, no edge without a consumed output, every wave has a runnable task.

## Task Prompt Contract

A task prompt is the only thing the sub-agent sees. It has no conversation history and cannot ask you questions. Write it so a competent stranger executes it exactly. In this order:

1. **TASK**: one imperative sentence naming the deliverable.
2. **DELIVERABLE**: files changed, the exact report shape, the evidence produced.
3. **SCOPE**: what it may read and write, with exact paths, as a hard boundary. Name what is out of scope when a sibling task owns it.
4. **VERIFY**: the literal command it runs on its own work and the expected result, plus the observation behind each conclusion it reports. A conclusion comes from reading the source or file or running a tool, never from plausibility, recall, or the shape of the code.
5. **STOP WHEN**: the single observable condition that ends the task.
6. **LOAD_SKILLS**: for a prompt to `omo-implementer`, `omo-researcher`, `omo-reviewer`, `omo-security-reviewer`, or `omo-planner`, add a plain line `LOAD_SKILLS: [..]` or `LOAD_SKILLS: none` (not a bold label value), chosen from `omo-orchestrate` `references/skill-catalog.md`. A PreToolUse hook denies the dispatch without it.

Rules that make prompts obeyed:

- Self-contained. Paste paths, facts, and constraints in. "As discussed above" is a dangling reference.
- Minimum sufficient context. Every pasted fact must change what the task does.
- Binary observables: "exit code 0 and `dist/index.js` exists", never "check it works".
- Positive framing. Say what to do. Reserve NEVER / ONLY for true invariants (do not commit, do not edit outside scope).
- One role per task. A task that investigates does not also fix; a task that writes does not review its own work.
- When embedding an upstream output, quote or summarize the relevant part. Unbounded pastes drown the prompt.

Treat any prompt missing TASK or STOP WHEN, or a plan that names no check for the deliverable, as a defect to fix before dispatch.

## Verification

- Task outputs are claims. Before reporting done, prove the deliverable with a real check (test, build, endpoint call, the file itself) and keep the captured output.
- The coordinator runs the check itself when it is one short command. Give it a verification task depending on the producers it checks only when the check is long, splits into parallel parts, or needs a fresh context; that task's prompt names the exact invocation and the binary observable that decides PASS or FAIL.
- Paginated deliverables (PDF, DOCX, deck, print HTML) are verified by rendering every page and inspecting each for blank pages, bad breaks, split tables, and clipped text. Sampling is not verification.
- A downstream task that builds on an upstream result re-checks the specific facts it depends on (file exists, test passes, symbol exported) before trusting them.

Heavier patterns, for when the user asked for thoroughness or a wrong answer is expensive:

- **Adversarial verify**: a few independent skeptics per claim, each told to refute it and to answer "refuted" when unsure. Keep the claim only if most of them fail.
- **Perspective-diverse verify**: give each verifier a different lens (correctness, security, does it reproduce) instead of identical refuters.
- **Judge panel**: several independent attempts at a hard design, scored by parallel judges, then synthesized from the winner.
- **Loop until dry**: for discovery of unknown size, keep adding finders until two consecutive rounds return nothing new, deduplicating against everything seen.
- **Completeness critic**: one last task that asks what was not covered: a modality not run, a claim unverified, a source unread.

When coverage is bounded (top-N, sampling, no retry), say what was dropped.

## Failure Playbook

- **A failed task blocks only its dependents.** Read its error first, then recover that task in place. Never rebuild the whole graph.
- **Classify before retry.** Follow `omo-guardrails` `references/error-recovery.md` for start and resume failures: verify child status and ownership before replacement, keep unknown or foreign-owned children pending, and redact error payloads. STOP and BLOCKED override retry advice. Once recovery is authorized and the original child is confirmed absent or terminal, re-dispatch only the failed task with an edited prompt when needed. Dependents stay pending until it verifies.
- **Amend when the definition was wrong.** Rewrite or split the bad task, then re-run it plus its transitive dependents. Verified unaffected tasks keep their results.
- **SendMessage when the agent is alive but stuck or needs context.** Continuing the same agent keeps its context. If it cannot be continued, retry with a fresh dispatch.
- **Start-time storms.** If many tasks in one wave fail within seconds without doing work, the environment or tool is failing, not the prompts. Stop dispatching, fix the cause, then retry the failed set.
- **Verify a completion claim before trusting it.** A task reporting a blocker has not completed. Classify and resolve the blocker before retrying; a report is not authority to bypass access or duplicate an unknown live child.
- **Abandon only when the goal is abandoned.** Record the reason in the ledger.
- For implementation/review tasks, every repair redispatch above first returns to `omo-ralph-loop` to reserve the next shared iteration; there is no separate task retry cap. Local command recovery and one missing-output follow-up stay within the current pass and never authorize an additional work pass. Research-only task retries follow the research workflow's convergence rules.

## Mass Research

When the user combines the mass trigger with research ("mass ulw research", "mulw research"), define the known harvest -> expand -> verify chains in one phase graph and follow `omo-research` mode `ultraresearch` for its evidence contract and convergence rules. Slot limits determine dispatch batches within that phase.

- Open with the angles the topic has, then grow until dry: enumerate the distinct angles you can name (source territory, sub-question, entity, time window, competing approach, adjacent field) and give each one harvest task. A broad topic has dozens and a narrow one a handful; padding the list buys queue time, not coverage. A run that stops after its first harvest collected breadth and no depth.
- Harvest and expand reports tag every claim `OBSERVED:` and every closed lead `PROBED:` as `ultraresearch` Source Lanes defines; a claim the task only remembers goes in as a lead. The verify task re-opens each `OBSERVED:` source and passes only a claim whose observation it reproduces: a source that shows something else fails the claim, an unreachable source leaves it `UNKNOWN`, and a claim with no `OBSERVED:` line goes back to the coordinator as a lead.
- Route across the owner table in one graph; one owner tier across every task is the routing failure above.
- Verified leads determine additional chains whose scope was unknown, not permission to postpone already-known stages. Register those chains before dispatch, deduplicate against every lead already seen (rejected ones included, or they return every round), and stop expanding when a round adds nothing new.
- A short deliverable (a memo, a one-page answer) bounds the synthesis, not the harvest: the angles still come from the topic.
- Verify what the deliverable rests on: one verify task per cluster of related angles (for example one per subject compared, plus one for cross-cutting angles) re-checks the `OBSERVED:` sources behind the claims the synthesis will use. Give every angle its own verify task only when the user asked for claim-by-claim rigor.
- One reducer merges the verified claims and writes the deliverable (a prose-only `omo-implementer`; when the merge needs judgment, `omo-oracle` decides it first and the writer records its verdict, since `omo-oracle` is read-only). When one context cannot hold them, several parallel slice tasks reading bounded digests feed that final reducer. Never hand dozens of raw outputs to one task.
