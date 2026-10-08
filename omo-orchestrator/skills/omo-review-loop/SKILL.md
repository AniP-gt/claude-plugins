---
name: omo-review-loop
description: "Implement-review-fix loop: omo-implementer builds, parallel omo-reviewer lanes review, a synthesis judge picks AUTO_FIX or ASK_USER, omo-review-work gates. Use for implement+review."
argument-hint: [task-or-issue]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Skill, TodoWrite
user-invocable: true
---

Plugin port of the personal `implementation-review-loop` skill, rebuilt on omo-orchestrator agents.

# OMO Review Loop

Ralph-managed review workflow: `omo-implementer` implements, parallel `omo-reviewer` lanes review one dimension each plus an evidence-gate lane (and an optional Copilot CLI lane), a synthesis judge classifies every finding, the controller schedules fixes. The final gate (`omo-review-work`, plus an installed external review skill such as `self-review` or `review-pr` when available) returns its verdict to `omo-ralph-loop`, the sole loop controller.

Triggers: "implement and review", "review loop", "auto-review", "quality loop", "implement with review".

## Coordinator Boundary

The main context is coordinator-only (see `omo-guardrails`). It routes, records state, saves lane reports verbatim, and applies `omo-ralph-loop` transitions. Load that skill before dispatch and reuse an active TASK_ID/ledger; never recursively invoke a second controller. Implementation, review, QA, and validation commands go to sub-agents. Local tool/worker recovery rules come from `omo-guardrails`; all implementation/review iteration budgets and stall decisions come from `omo-ralph-loop`; implementation rules from `omo-implement` and `omo-programming`; final-gate semantics from `omo-review-work`. They are not restated here.

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
| `references/outer-gate.md` | Phase 6 outer gate (omo-review-work, optional external review skill), verdict mapping, 6e stuck consult |
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
- `N` is the global Ralph iteration, reserved before its work pass. It never resets for feedback, QA, or final-gate findings, and an iteration directory is never overwritten.
- `OUTER_CYCLE` is a legacy artifact-name alias for `N`, not a counter or budget. `CYCLE_LOG` remains an append-only gate-report index; the Ralph `LEDGER` owns control state. `CYCLE_START_SHA` is the persistent task-wide review base, recorded once before the first implementation and never refreshed per pass.

## Resume and Stop-Continuation

Run this check before Phase -1 resumes anything, whenever the skill is invoked or the user says continue or resume and a previous run left artifacts for this `TASK_ID`: any `ITER_DIR` (`docs/issues/{TASK_ID}/reviews/iter{N}/` or `.claude/omo/reviews/{TASK_ID}/iter{N}/`), `CYCLE_LOG`, or `LEDGER`. Decide from artifact state, not from keywords in the conversation.

1. Read the latest `synthesis.md` (highest `N`), the `CYCLE_LOG`, and the `LEDGER` in full, including referenced QA and final-gate reports.
2. A previous run is blocked by unanswered `ASK_USER`, an exhausted recorded budget, unresolved oracle escalation/stuck state, an `INCONCLUSIVE` requiring unavailable access or decisions, or a required lane/tool failure after its bounded follow-up. Historical inner/outer limits, `MAX_CYCLES_REACHED`, and QA retry exhaustion remain blocked states, even if a new default cap would be larger.
3. For a blocked run, present the blocking condition, pending `ASK_USER`, open `AUTO_FIX`, consumed iterations, recorded cap, and proposed next action. Wait for a user answer or explicit confirmation. Append answers and the confirmed plan before continuing. Confirmation alone does not extend an exhausted budget.
4. For legacy state without Ralph fields, append a migration entry preserving all artifacts, decisions, and report paths. Reconcile consumed work passes from the full ledger, iteration directories, feedback, QA returns, and gate history; record how they map to the global count and the earliest task review base. If consumption or the base cannot be reconstructed, pause for reconciliation instead of guessing or resetting. Never reduce a known consumed count. Carry forward an explicitly recorded total cap; otherwise record the default 20 only after reconciliation. A historical exhausted limit requires an explicit new budget grant before migration can continue.
5. A legacy `ORACLE_OVERRIDE` or empty-diff approval is not independent approval. Preserve it as history and require a fresh final gate before completion. Keep unresolved disputes as reviewer input.
6. On an interrupted non-blocked run, reconcile actual state and resume the recorded phase of the same reserved iteration. Announce that phase and number; do not spend another iteration or overwrite existing reports. Append phase-attempt suffixes if a report must be regenerated.

## Overview

Departure from the old nested loops: one task-wide Ralph budget (default 20) covers every pass.

```
SETUP                  Phase -1 docs, 0 detection, 1 plan as needed
RALPH reserves N       check shared cap, blockers, progress, and ownership
Phase 2/3c WORK         one implementation/fix/evidence pass
Phase 3d VERIFY        lint / typecheck / tests
Phase 3a REVIEW        independent parallel lanes
Phase 3b SYNTHESIZE    AUTO_FIX / ASK_USER / PASS
  fixes needed         return findings to Ralph for next N
  ASK_USER             pause; preserve N and cap
Phase 3.5 QA           real scenarios; failure returns to Ralph
Phase 4-5 REPORT       feedback returns to Ralph; no new budget
Phase 6 FINAL GATE     omo-review-work in parallel with self-review (+ review-pr only on user request)
  changes/evidence     return findings to Ralph for next N
  APPROVE              Ralph completes -> Phase 7 final report
```

## Phase -1, 0, 1, 2

Follow `references/setup.md`. Key points:

- Phase -1 reads existing docs. A written plan, task, or spec skips Phase 1.
- Phase 0 sets `DETECTED_STACK`, `RISK_LEVEL`, `RISK_REASON`, `IS_FRONTEND`, `IS_CI_CHANGE`, GOAL/CONSTRAINTS/BACKGROUND, and the External Library Contract evidence block.
- The library evidence block is passed unchanged to the implementer, every lane, the judge, the Phase 3.5 verifier, and the Phase 6 gates. A stage must not PASS when an applicable check is missing or its version applicability is unresolved.
- Record `CYCLE_START_SHA=$(git rev-parse HEAD)` once before the first Phase 2, or reuse the task's recorded review base. Preserve it across commits and iterations so final review covers the whole task.

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
TASK_ID: {TASK_ID}    Ralph iteration: {N}/{CAP}    Ledger: {LEDGER}
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
6. A skipped optional lane is reduced coverage, never PASS output. A required `NOT_EXECUTED` lane blocks PASS and pauses after its bounded follow-up fails. Never fill in another lane's output.

### 3c. Fix

A synthesis finding ends the current pass. Return it to Ralph; only after the controller reserves the next iteration may the fix dispatch run. Dispatch `omo-orchestrator:omo-implementer` with `synthesis.md`, `SPEC`, the ledger path, and the library evidence. It fixes `AUTO_FIX` items only (code fixes and evidence items), touches nothing unrelated, and appends to the ledger. `ASK_USER` items wait for the user.

### 3d. Verify

Dispatch the stack verify commands in `references/verify-and-oracle.md` to a sub-agent after every fix. A failing check is an `AUTO_FIX` item for the next iteration, not a pass.

### 3e. Loop decision

```
ASK_USER pending               -> pause and record; resume only after answer
synthesis PASS and verify pass -> Phase 3.5
blocking findings remain       -> return to Ralph for next iteration or stop at cap
```

### 3f. Oracle consult

Ralph consults `omo-oracle` for a repeated blocker after two iterations and stops if the same blocker persists for three consecutive iterations. Use `references/verify-and-oracle.md` for the consultation prompt. Advice never resets the budget or substitutes for reviewer approval.

## Phase 3.5: Verify in Action

After synthesis and validation pass, run the fresh QA lane in `references/verify-and-oracle.md`. PASS -> Phase 4. FAIL -> return issues to Ralph for the next scoped fix pass. SKIP -> record missing coverage; the final gate still requires its applicable QA evidence.

## Phase 4-5: Report and Feedback

Use `references/templates.md`. The Phase 4 report includes the loop summary, iteration breakdown, per-lane table (evidence gate shows its decision line; skipped lanes show `SKIPPED` or `NOT_EXECUTED`), evidence gaps, fixed blocking items, ASK_USER decisions, Phase 3.5 result, and the External Library Contract Checks. User feedback becomes scoped directives for the next Ralph iteration under the remaining budget. Do not wait for optional feedback before running the final gate.

## Phase 6-7: Outer Gate

Follow `references/outer-gate.md`.

1. 6a: build the LOCAL DIFF CONTEXT from the persistent `CYCLE_START_SHA`, including untracked files and current evidence. An empty diff still requires the final independent gate.
2. 6b: run `self-review` review-only (or the plan's `REVIEW_SKILL`), plus `review-pr` in LOCAL DIFF MODE only when the user asked for it; record a skip for any skill that is not installed.
3. 6b2: always run `omo-orchestrator:omo-review-work` on that context, in parallel with 6b.
4. 6c: save reports and append their paths and outcomes to `CYCLE_LOG` and the controlling `LEDGER`.
5. 6d: every executed gate must clear, and `omo-review-work` must explicitly return `APPROVE`. Findings go to Ralph for the next iteration; unavailable evidence pauses.
6. 6e: recurring findings use the same Ralph blocker history and oracle consultation, not another loop.

Phase 7 reports `APPROVE`, `MAX_ITERATIONS_REACHED`, or the exact blocked/stuck state. Approval requires fresh independent evidence for the final tree.

## Stop Conditions

- Ralph owns the single default 20-iteration cap and same-blocker three-iteration stop. Feedback, QA, oracle, and gate failures never reset it.
- Pause for any `ASK_USER`, unavailable required evidence, oracle escalation, or required tool/lane failure after its bounded follow-up.
- A pause does not reserve another iteration. Already dispatched work remains counted.
- Only the final independent `APPROVE` completes the loop. Oracle advice, empty diffs, passing checks, and budget exhaustion cannot approve.

## Anti-Patterns

| Violation | Severity |
|---|---|
| Reviewer and implementer share context, or a lane reads another lane's output | CRITICAL |
| Skipping review after a "small" change | CRITICAL |
| Filling a skipped lane with another model's output | CRITICAL |
| SPEC has no Done when (implementer has no stop condition) | HIGH |
| Fixing unrelated code during a fix pass | HIGH |
| Exceeding the recorded Ralph cap | HIGH |
| Not running verification after fixes | HIGH |
| Rewriting the implementation from scratch on a fix pass | HIGH |
