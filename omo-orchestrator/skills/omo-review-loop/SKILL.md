---
name: omo-review-loop
description: "Implement-review-fix loop: omo-implementer builds, parallel omo-reviewer lanes review, a synthesis judge picks AUTO_FIX or ASK_USER, omo-review-work gates. Use for implement+review."
argument-hint: [task-or-issue]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Skill, TodoWrite
user-invocable: true
---

Plugin port of the personal `implementation-review-loop` skill, rebuilt on omo-orchestrator agents.

# OMO Review Loop

Automated cycle: `omo-implementer` implements, parallel `omo-reviewer` lanes review one dimension each plus an evidence-gate lane (and an optional Copilot CLI lane), a synthesis judge classifies every finding, `omo-implementer` fixes, repeat. An outer gate (`omo-review-work`, plus the optional `review-pr` skill) decides whether the cycle is done.

Triggers: "implement and review", "review loop", "auto-review", "quality loop", "implement with review".

## Coordinator Boundary

The main context is coordinator-only (see `omo-guardrails`). It routes, records state, saves lane reports verbatim, and decides loop transitions. Implementation, review, QA, and validation commands go to sub-agents. Safety, retry, and stall rules come from `omo-guardrails`; implementation rules from `omo-implement` and `omo-programming`; final-gate semantics from `omo-review-work`. They are not restated here.

## Hard Boundaries

- Never push, publish, merge, open a PR, or post remote comments. CodeRabbit comment posting in `review-pr` is always skipped.
- Commit only when the user asks, via `omo-git-master`.
- Never install a missing tool, and never use `npx` to obtain one. A missing optional tool means its lane is skipped and recorded.
- Never synthesize output for a lane that did not run.

## Reference Files

| File | Used in |
|---|---|
| `references/setup.md` | Phase -1 docs, Phase 0 detection, risk, library contract, Phase 1 plan, Phase 2 implement |
| `references/shared-gates.md` | Common reviewer preamble and shared review gates, pasted into every lane |
| `references/reviewer-security.md` | Security lane prompt |
| `references/reviewer-robustness.md` | Robustness lane prompt |
| `references/reviewer-quality.md` | Quality, convention, and AI slop lane prompt |
| `references/reviewer-alignment.md` | Goal alignment lane prompt |
| `references/reviewer-evidence-gate.md` | `omo-reviewer` evidence-gate lane and `INCONCLUSIVE` handling |
| `references/reviewer-copilot.md` | Optional GitHub Copilot CLI lane |
| `references/synthesis-judge.md` | Phase 3b judge prompt and rules |
| `references/verify-and-oracle.md` | Phase 3d verify commands, 3f oracle consult, Phase 3.5 verify in action |
| `references/outer-gate.md` | Phase 6 outer gate (omo-review-work, optional review-pr), verdict mapping, 6e stuck consult |
| `references/templates.md` | Phase 4 report, Phase 5 feedback, cycle log entry, Phase 7 final report |
| `references/db-checklist.md` | DB, index, lock, and migration checklist |

## Paths

Resolve once at Phase -1 and record them in the ledger.

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
[ -d "$REPO_ROOT/docs/issues" ] && LAYOUT=docs || LAYOUT=omo
```

| Variable | `LAYOUT=docs` (repo already has `docs/issues/`) | `LAYOUT=omo` (default otherwise) |
|---|---|---|
| `WORK_DIR` | `docs/issues/{TASK_ID}/` | `.claude/omo/reviews/{TASK_ID}/` |
| `SPEC` | `docs/issues/{TASK_ID}/spec.md` | `.claude/omo/reviews/{TASK_ID}/spec.md` |
| `ITER_DIR` | `docs/issues/{TASK_ID}/reviews/iter{N}/` | `.claude/omo/reviews/{TASK_ID}/iter{N}/` |
| `OUTER_DIR` | `docs/reviews/{TASK_ID}/` | `.claude/omo/reviews/{TASK_ID}/outer/` |
| `CYCLE_LOG` | `docs/issues/{TASK_ID}/outer_cycle_log.md` | `.claude/omo/reviews/{TASK_ID}/outer_cycle_log.md` |
| `LEDGER` | `.claude/omo/handoffs/{TASK_ID}.md` | same |

- `TASK_ID`: issue number when known, else the existing `docs/issues/<name>/` directory name, else a kebab-case slug of the task. Derive it; do not stall to ask.
- The user may override `WORK_DIR` or `OUTER_DIR` in the invocation. All paths resolve from `REPO_ROOT`, never the shell's current directory.
- `N` counts monotonically across outer cycles and Phase 5 rounds, so an iteration directory is never overwritten.

## Resume and Stop-Continuation

Run this check before Phase -1 resumes anything, whenever the skill is invoked or the user says continue or resume and a previous run left artifacts for this `TASK_ID`: any `ITER_DIR` (`docs/issues/{TASK_ID}/reviews/iter{N}/` or `.claude/omo/reviews/{TASK_ID}/iter{N}/`), `CYCLE_LOG`, or `LEDGER`. Decide from artifact state, not from keywords in the conversation.

1. Read the latest `synthesis.md` (highest `N`), the latest `CYCLE_LOG` entry, and the `LEDGER` in full.
2. The previous run ended blocked when any of these holds:
   - `ASK_USER` items with no recorded answer in the ledger (`Overall: NEEDS_USER_INPUT`)
   - inner limit reached: iteration 5 of the cycle ended with blocking items
   - outer limit reached: cycle 3 without `APPROVE`, or `MAX_CYCLES_REACHED`
   - stuck: a 3f or 6e oracle consult, or an escalation row, with no recorded resolution, or an `omo-guardrails` circuit breaker tripped
   - the evidence gate returned `INCONCLUSIVE` needing access or a decision the loop lacks
   - a required lane or tool recorded as failed after its bounded follow-up
3. Blocked: present one summary in a single turn with the blocking condition, the pending `ASK_USER` items, the open `AUTO_FIX` items, the current iteration and cycle, and the proposed next action. Wait for the user to confirm or answer. Never resume a blocked loop silently.
4. Before continuing, append the user's answers to each `ASK_USER` item and the confirmed plan to the ledger (`omo-handoff`). Answered items become directives for the next fix pass. A limit that was reached does not reset unless the user explicitly grants a new budget, and that grant is recorded too.
5. Not blocked (for example, the run was interrupted mid-iteration): resume from the ledger's latest next exact action and state which phase and iteration it resumes.

## Overview

```
[OUTER LOOP: max 3 cycles]
Phase -1 LOAD DOCS      existing plan/spec/task docs, paths, ledger
Phase 0  DETECT         stack, risk, frontend/CI flags, library contract
Phase 1  PLAN           skipped when a written plan/spec exists; else omo-planner
Phase 2  IMPLEMENT      omo-implementer (record CYCLE_START_SHA first)
Phase 3  REVIEW LOOP    up to 5 iterations:
  3a Review             parallel lanes in one message
  3b Synthesize         synthesis judge -> AUTO_FIX / ASK_USER / PASS
  3c Fix                omo-implementer applies AUTO_FIX only
  3d Verify             lint / typecheck / tests
  3e Loop?              blocking remains -> 3a
  3f Stuck?             omo-oracle consult
Phase 3.5 VERIFY IN ACTION   fresh QA lane runs real scenarios
Phase 4  REPORT         loop summary
Phase 5  USER FEEDBACK  feedback -> back to Phase 3 (fresh 5-iteration budget)
Phase 6  OUTER GATE     omo-review-work (+ review-pr if available) on this cycle's diff
  6d                    both clear -> Phase 7 | any blocks -> next cycle
  6e                    same blocker across cycles -> omo-oracle consult
Phase 7  FINAL REPORT   APPROVE / MAX_CYCLES_REACHED
```

## Phase -1, 0, 1, 2

Follow `references/setup.md`. Key points:

- Phase -1 reads existing docs. A written plan, task, or spec skips Phase 1.
- Phase 0 sets `DETECTED_STACK`, `RISK_LEVEL`, `RISK_REASON`, `IS_FRONTEND`, `IS_CI_CHANGE`, GOAL/CONSTRAINTS/BACKGROUND, and the External Library Contract evidence block.
- The library evidence block is passed unchanged to the implementer, every lane, the judge, the Phase 3.5 verifier, and the Phase 6 gates. A stage must not PASS when an applicable check is missing or its version applicability is unresolved.
- Record `CYCLE_START_SHA=$(git rev-parse HEAD)` immediately before each cycle's Phase 2.

## Phase 3: Review Loop

### 3a. Launch lanes (single message, all simultaneous)

| Lane | Agent | Prompt | Output file in `ITER_DIR` |
|---|---|---|---|
| security | `omo-orchestrator:omo-reviewer` | `references/reviewer-security.md` | `security.md` |
| robustness | `omo-orchestrator:omo-reviewer` | `references/reviewer-robustness.md` | `robustness.md` |
| quality | `omo-orchestrator:omo-reviewer` | `references/reviewer-quality.md` | `quality.md` |
| alignment | `omo-orchestrator:omo-reviewer` | `references/reviewer-alignment.md` | `alignment.md` |
| evidence gate | `omo-orchestrator:omo-reviewer` | `references/reviewer-evidence-gate.md` | `omo_review.md` |
| copilot (optional) | `omo-orchestrator:omo-reviewer` running the CLI | `references/reviewer-copilot.md` | `copilot_all.md` |

Each dimension prompt is assembled as: lane prompt + Lane Context block + `references/shared-gates.md`. Add `references/db-checklist.md` to robustness and alignment when the diff touches DB, SQL, migrations, indexes, transactions, batch jobs, or locks. Lanes are independent: none may read another lane's output.

`omo-reviewer` has no Write tool. Each lane returns its report in the required format and the coordinator saves it verbatim to its output file. An empty or missing return is a lane failure: one bounded follow-up with `SendMessage`, then record `NOT_EXECUTED` for that lane.

Lane Context block (identical for every lane):

```
TASK_ID: {TASK_ID}    Iteration: {N}/5    Outer cycle: {OUTER_CYCLE}/3
Stack: {DETECTED_STACK}    IS_CI_CHANGE: {true|false}
Risk: {RISK_LEVEL} - {RISK_REASON}
Diff under review: run `git diff {CYCLE_START_SHA}` and `git diff --name-only {CYCLE_START_SHA}`
  yourself, plus `git ls-files --others --exclude-standard` for new untracked files (read them).
## GOAL / CONSTRAINTS / BACKGROUND / Done when
{from SPEC}
## External Library Contract Evidence
{evidence block, unchanged}
## Unresolved ASK_USER decisions and oracle directives
{from the previous synthesis.md and CYCLE_LOG, or "none"}
```

### 3b. Synthesis

After every lane returns, spawn one judge per `references/synthesis-judge.md`. It reads all lane files and returns `synthesis.md`, which the coordinator saves to `ITER_DIR`. Rules in brief:

1. Two or more lanes flag the same location and mechanism -> `AUTO_FIX`.
2. One lane flags a security, robustness, convention, or goal-alignment violation -> `AUTO_FIX`.
3. One lane flags something that needs a business-logic or requirement-interpretation decision, or lanes contradict each other -> `ASK_USER`.
4. Evidence-gate `INCONCLUSIVE` -> never PASS. `AUTO_FIX` when the implementer can produce the evidence, else `ASK_USER`. Producing evidence with no code change is a valid resolution.
5. Nothing flagged by any lane that ran -> `PASS`.
6. Skipped or `NOT_EXECUTED` lanes are recorded as reduced coverage, never counted as PASS output and never filled in by another model.

### 3c. Fix

Dispatch `omo-orchestrator:omo-implementer` with `synthesis.md`, `SPEC`, the ledger path, and the library evidence. It fixes `AUTO_FIX` items only (code fixes and evidence items), touches nothing unrelated, and appends to the ledger. `ASK_USER` items wait for the user.

### 3d. Verify

Dispatch the stack verify commands in `references/verify-and-oracle.md` to a sub-agent after every fix. A failing check is an `AUTO_FIX` item for the next iteration, not a pass.

### 3e. Loop decision

```
ASK_USER pending                        -> pause, present all ASK_USER items in one turn, resume after answer
synthesis PASS and verify pass          -> exit to Phase 3.5
iteration_count >= 5 with blocking left -> 3f oracle consult, then report to user
else                                    -> iteration_count++ -> 3a with a fresh ITER_DIR
```

### 3f. Oracle consult

Trigger: the same issue (same file and defect mechanism, or the same missing evidence) appears in synthesis across 2+ consecutive iterations, or 5 iterations end with blocking items. Consult `omo-orchestrator:omo-oracle` per `references/verify-and-oracle.md`.

## Phase 3.5: Verify in Action

After the review loop passes, run the fresh QA lane in `references/verify-and-oracle.md`. PASS -> Phase 4. FAIL -> `omo-implementer` fix and back to Phase 3 (max 3 times). SKIP -> record the reason and continue.

## Phase 4-5: Report and Feedback

Use `references/templates.md`. The Phase 4 report includes the loop summary, iteration breakdown, per-lane table (evidence gate shows its decision line; skipped lanes show `SKIPPED` or `NOT_EXECUTED`), evidence gaps, fixed blocking items, ASK_USER decisions, Phase 3.5 result, and the External Library Contract Checks. User feedback restarts Phase 3 with a fresh 5-iteration budget.

## Phase 6-7: Outer Gate

Follow `references/outer-gate.md`.

1. 6a: build the LOCAL DIFF CONTEXT from `git diff {CYCLE_START_SHA}`. Empty diff -> record `SKIPPED - empty diff` and treat as APPROVE.
2. 6b: run the `review-pr` skill in LOCAL DIFF MODE only if it is listed as available. Otherwise record `review-pr: SKIPPED (unavailable)`.
3. 6b2: always run `omo-orchestrator:omo-review-work` on the same context.
4. 6c: read the saved reports, append one entry to `CYCLE_LOG`. Never write a competing third review report.
5. 6d: every gate that ran must clear; the stricter decides. Blocking findings from any gate feed the next cycle's Phase 2 as additional-fix directives.
6. 6e: a blocking finding or unresolved evidence gap recurring across consecutive cycles -> `omo-oracle` consult before the next fix pass.

Outer loop max 3 cycles. Without approval, Phase 7 reports `MAX_CYCLES_REACHED`. Phase 7 is presented in the response, not saved as a new review file.

## Stop Conditions

- Inner loop: 5 iterations per cycle (fresh budget after Phase 5 feedback).
- Outer loop: 3 cycles. An oracle consult never buys an extra cycle.
- Phase 3.5 FAIL: 3 fix returns.
- Pause for the user: any `ASK_USER`, an `INCONCLUSIVE` needing access or a decision the loop lacks, an oracle escalation row, or a required tool failing after one bounded follow-up. A pause does not consume a cycle.
- Only an `APPROVE` Phase 6 decision (or an `ORACLE_OVERRIDE` recorded in `CYCLE_LOG`) completes the loop.

## Anti-Patterns

| Violation | Severity |
|---|---|
| Reviewer and implementer share context, or a lane reads another lane's output | CRITICAL |
| Skipping review after a "small" change | CRITICAL |
| Filling a skipped lane with another model's output | CRITICAL |
| SPEC has no Done when (implementer has no stop condition) | HIGH |
| Fixing unrelated code during a fix pass | HIGH |
| Exceeding 5 iterations or 3 cycles without reporting | HIGH |
| Not running verification after fixes | HIGH |
| Rewriting the implementation from scratch on an outer-cycle fix pass | HIGH |
