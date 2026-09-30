# Phase 6: Outer Gate

Phase 6 runs existing review skills on this cycle's local diff and uses their saved reports as the gate. It does not run its own reviewer agents and does not re-implement review logic.

| Gate | Skill | Required | Report |
|---|---|---|---|
| primary PR-style review | `review-pr` (LOCAL DIFF MODE) | optional, only if listed as available | `{OUTER_DIR}/cycle{OUTER_CYCLE}_review_{TIMESTAMP}.md` |
| second opinion, final-gate contract | `omo-orchestrator:omo-review-work` | always | `{OUTER_DIR}/cycle{OUTER_CYCLE}_omo_review_work_{TIMESTAMP}.md` |

## Timestamp

Generate once per cycle and reuse: `TIMESTAMP=$(date +%Y%m%d%H%M)`.

## 6a: LOCAL DIFF CONTEXT

```bash
# CYCLE_START_SHA was recorded right before this cycle's Phase 2
CYCLE_DIFF=$(git diff ${CYCLE_START_SHA})              # committed + uncommitted work
CYCLE_FILES=$(git diff --name-only ${CYCLE_START_SHA})
NEW_FILES=$(git ls-files --others --exclude-standard)  # untracked files git diff omits
REPORT_REPO_ROOT=$(git rev-parse --show-toplevel)
```

- If `CYCLE_START_SHA` is missing, use `git diff HEAD`.
- If `CYCLE_DIFF` and `NEW_FILES` are both empty, record `Phase 6: SKIPPED - empty diff` in `CYCLE_LOG` and treat the cycle as APPROVE.
- On `OUTER_CYCLE++`, record a fresh `CYCLE_START_SHA` so each gate sees only its cycle's changes.

| Field | Source |
|---|---|
| `CYCLE_DIFF`, `CYCLE_FILES`, `NEW_FILES` | commands above |
| `GOAL`, `CONSTRAINTS`, `BACKGROUND` | `SPEC`, else `task.md` / `plan.md` in `WORK_DIR`, else the Phase 1 plan |
| `RISK_LEVEL` | Phase 0 |
| External Library Contract evidence | `SPEC`, unchanged |
| Unresolved `ASK_USER` items | latest `synthesis.md` |
| Oracle directives | `CYCLE_LOG` |
| Phase 3.5 result | `{WORK_DIR}/verify_in_action_cycle{OUTER_CYCLE}.md` |

## 6b: review-pr in LOCAL DIFF MODE (optional)

Run only when `review-pr` appears in the available skills list. Otherwise record `review-pr: SKIPPED (unavailable)` in `CYCLE_LOG` and go to 6b2.

`review-pr` defaults to GitHub PRs, so every override must be stated or it will try to resolve a PR number. Invoke `Skill(skill: "review-pr", args: <contract>)`:

```
LOCAL DIFF MODE - invoked from omo-review-loop Phase 6.

There is no GitHub PR and none is required. Review the local changes below exactly
as you would a PR diff.

Overrides (all mandatory):
- Skip review-pr Phase 1. Do NOT run `gh pr view`, `gh pr diff`, `gh api`,
  `gh pr checkout`, `git checkout`, or `git switch`. Do not resolve a PR number.
  PR_DIFF is supplied inline; PR_COMMENTS is empty.
- Skip review-pr Phase 5 (CodeRabbit comments) unconditionally. Record
  "Phase 5: skipped (local diff mode)". Post nothing anywhere.
- Skip the PR-template completeness check; judge goal alignment against
  GOAL / CONSTRAINTS / BACKGROUND below.
- Skip review-pr Phase 6 (user feedback loop). Return after the report is saved.
- Run review-pr Phases 2, 2.5, 3, and 4 normally.
- Phase 4 is REQUIRED: save exactly one report at
  {OUTER_DIR}/cycle{OUTER_CYCLE}_review_{TIMESTAMP}.md (absolute path) and state that
  absolute path in your final response.

REPORT_REPO_ROOT: {REPORT_REPO_ROOT}
TASK_ID: {TASK_ID}    OUTER_CYCLE: {OUTER_CYCLE}    TIMESTAMP: {TIMESTAMP}
RISK_LEVEL: {RISK_LEVEL}

## GOAL
{GOAL}
## CONSTRAINTS
{CONSTRAINTS}
## BACKGROUND
{BACKGROUND}
## External Library Contract Evidence
{evidence block, unchanged}
## Changed Files
{CYCLE_FILES}
{NEW_FILES}
## Diff Under Review (PR_DIFF equivalent)
{CYCLE_DIFF}
{contents of each new untracked file}
```

If `review-pr` reports completion but no file exists at the stated path, re-invoke once. If it fails again, record `review-pr: NOT_EXECUTED - no report` and continue with 6b2. Never infer a verdict from the chat response.

## 6b2: omo-review-work (always)

Run it even when `review-pr` returned Request Changes; the findings are merged in 6d and skipping it loses the evidence-gap signal. Invoke `Skill(skill: "omo-orchestrator:omo-review-work", args: <contract>)`:

```
Invoked from omo-review-loop Phase 6b2 as the outer gate.

- The diff, GOAL, CONSTRAINTS, BACKGROUND, RISK_LEVEL, and External Library Contract
  evidence are supplied inline below. Do not resolve a GitHub PR.
- Run the two-lane gate in full: real-surface QA against the final tree first, then
  one fresh independent final reviewer. The Phase 3.5 result below is existing QA
  evidence to audit. A row it does not cover (named happy path, riskiest applicable
  edge, adjacent regression, each stated success criterion) is missing evidence, not
  assumed coverage.
- Apply the shared gates in shared-gates.md in the final reviewer's brief.
- Return the full report; it is saved to
  {OUTER_DIR}/cycle{OUTER_CYCLE}_omo_review_work_{TIMESTAMP}.md.

## Phase 3.5 result
{verbatim, or "SKIPPED - <reason>"}

{the same GOAL / CONSTRAINTS / BACKGROUND / evidence / files / diff block as 6b}
```

The coordinator saves the report to the stated path. If `omo-review-work` cannot run, record `omo-review-work: NOT_EXECUTED - <reason>`. With `review-pr` also skipped or failed, no gate ran: the cycle is `INCONCLUSIVE`, stop, and report the blocker. Never substitute a self-written review.

## 6c: Read the saved reports

- `review-pr` writes in Japanese. Extract the verdict from the `## 判定:` heading (`Approve` / `Request Changes` / `Needs Attention`) and quote the `Findings: Critical` items verbatim (file, line, description).
- `omo-review-work`: extract the decision (`APPROVE` / `REQUEST_CHANGES` / `INCONCLUSIVE`), blocking findings, and for `INCONCLUSIVE` the exact missing evidence, verbatim.
- Do not write a third, competing review report. Append one entry to `CYCLE_LOG` (template in `templates.md`) with both decisions, both absolute report paths, `CYCLE_START_SHA`, `TIMESTAMP`, and the blocking findings carried forward. Never overwrite earlier entries. `CYCLE_LOG` is a real file so the loop can resume after a context reset, and it is the authoritative source for a previous cycle's report paths (never glob for them).

## 6d: Verdict mapping

Every gate that ran must clear; the stricter decides.

| review-pr | omo-review-work | Phase 6 decision |
|---|---|---|
| Approve (0 Critical) or SKIPPED | `APPROVE` | APPROVE |
| Needs Attention (0 Critical) | `APPROVE` | APPROVE; carry the items into Phase 7 as follow-ups |
| Approve / Needs Attention / SKIPPED | `REQUEST_CHANGES` | REQUEST_CHANGES; omo findings become fix directives |
| Approve / Needs Attention / SKIPPED | `INCONCLUSIVE` | REQUEST_CHANGES; the directive is to produce the missing evidence, which may close with no code change |
| Request Changes (1+ Critical) | any | REQUEST_CHANGES; merge both gates' blocking findings, deduplicated by file and defect mechanism |

- An `INCONCLUSIVE` whose evidence is genuinely unavailable to the loop (production access, a business decision, a third-party response) is an `ASK_USER` escalation that does not consume a cycle. Present the exact missing evidence and pause.
- Nits and `[Suggestion]` findings never affect the decision.

```
APPROVE
  -> append CYCLE_LOG entry -> Phase 7

REQUEST_CHANGES
  -> append CYCLE_LOG entry with the blocking findings
  -> if OUTER_CYCLE < 3:
       STUCK CHECK (before OUTER_CYCLE++ and before the next fix pass):
         compare the union of this cycle's blocking findings and unresolved evidence
         gaps (from every gate that ran) with the previous cycle's union, reading the
         previous reports at the paths in CYCLE_LOG. Match on file and defect
         mechanism, not line number or wording; two findings are the same when one
         fix would resolve both. No-op on cycle 1.
         Any recurrence -> 6e oracle consult; its action table decides what happens.
       OUTER_CYCLE++
       record a fresh CYCLE_START_SHA and TIMESTAMP
       feed the blocking findings and oracle directives into Phase 2 as fix directives
       re-run from Phase 2 (Phase -1 may be skipped)
  -> if OUTER_CYCLE == 3:
       Phase 7 with MAX_CYCLES_REACHED
```

- Additional-fix instruction: the next cycle's implementer makes additional fixes on top of the previous implementation. No rewrite from scratch.
- Inner loop on re-entry: the next cycle runs the full Phase 3 inner loop (max 5 iterations) before Phase 6 again. Phase 6 findings are added to Phase 2 input, not substituted for the inner review.

## 6e: Oracle consult (outer-loop stuck detection)

Scope: Phase 3f handles an issue surviving 2+ iterations within one cycle. Phase 6e handles a blocking finding surviving a whole cycle (inner loop plus gates).

Trigger: a blocking finding from any gate at the end of cycle N is also present at the end of cycle N+1. This includes `review-pr` Critical findings, `omo-review-work` blocking findings, and an `INCONCLUSIVE` whose missing evidence was not produced. When the recurrence is omo-only (0 Criticals in both cycles), pass the two omo reports and say so; do not skip the consult.

```
Agent(
  subagent_type="omo-orchestrator:omo-oracle",
  description="Phase 6e outer-loop stuck consult",
  prompt="""
  The blocking finding(s) below from the Phase 6 gates persisted across two
  consecutive outer cycles (Cycle {N} and Cycle {N+1}). The implementer ran a full
  inner-loop fix pass in Cycle {N+1} but the gate still flags the same problem.
  {If the recurrence is an unresolved INCONCLUSIVE: the gate is blocked on missing
   evidence the cycle did not produce, not on a code defect.}

  ## Recurring blocking finding(s)
  {verbatim from both cycles, each labeled: review-pr Critical / omo-review-work
   blocking / omo-review-work INCONCLUSIVE - missing evidence}

  ## Cycle {N} gate report excerpts
  {blocking findings / missing evidence}

  ## Cycle {N+1} gate report excerpts
  {blocking findings / missing evidence}

  ## Cycle {N+1} diff
  {git diff {CYCLE_START_SHA}}

  Explain why the fix did not resolve the concern, and give an alternative approach or
  a clarification directive for the next cycle.
  """
)
```

| Oracle response | Action |
|---|---|
| Concrete alternative approach | Append the plan to the next cycle's Phase 2 input as a high-priority directive; OUTER_CYCLE++ and re-run from Phase 2 |
| Reviewer expectation ambiguous or needs business judgment | `ASK_USER` with the analysis; pause the outer loop |
| Implementation already correct, reviewer too strict | Record `ORACLE_OVERRIDE` in `CYCLE_LOG`, treat as resolved, go to Phase 7 |
| Systemic design problem, not incrementally fixable | Escalate to the user with the analysis; do not consume another cycle |

- Only the first row increments `OUTER_CYCLE`. The escalation rows pause and resume at Phase 2 with the user's decision; the paused cycle is not consumed. The override row skips remaining cycles and carries the oracle's reasoning into Phase 7.
- A consult never buys an extra cycle. A row-1 consult at the end of cycle 2 leaves cycle 3 as the last attempt; say so in the `CYCLE_LOG` entry.
- Append the oracle response to `CYCLE_LOG` verbatim the moment it is produced.

## Phase 7

Present the final report (template in `templates.md`) in the response, not as a new review file. Link every saved gate report by absolute path. Include the External Library Contract Checks evidence and gate decision, or the explicit N/A reason.
