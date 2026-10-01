# Phase 6: Outer Gate

Phase 6 runs existing review skills on the task-wide local diff and uses their saved reports as the gate. It does not run its own reviewer agents and does not re-implement review logic.

| Gate | Skill | Required | Report |
|---|---|---|---|
| primary PR-style review | `review-pr` (LOCAL DIFF MODE) | optional, only if listed as available | `{OUTER_DIR}/cycle{OUTER_CYCLE}_review_{TIMESTAMP}.md` |
| second opinion, final-gate contract | `omo-orchestrator:omo-review-work` | always | `{OUTER_DIR}/cycle{OUTER_CYCLE}_omo_review_work_{TIMESTAMP}.md` |

## Timestamp

Generate once per gate invocation and reuse: `TIMESTAMP=$(date +%Y%m%d%H%M)`.

## 6a: LOCAL DIFF CONTEXT

```bash
# CYCLE_START_SHA is the persistent review base recorded before the first work pass
CYCLE_DIFF=$(git diff ${CYCLE_START_SHA})              # committed + uncommitted work
CYCLE_FILES=$(git diff --name-only ${CYCLE_START_SHA})
NEW_FILES=$(git ls-files --others --exclude-standard)  # untracked files git diff omits
REPORT_REPO_ROOT=$(git rev-parse --show-toplevel)
```

- If `CYCLE_START_SHA` is missing, reconcile it from the task ledger before review; do not silently substitute HEAD and hide earlier commits.
- If the diff is empty, record that fact and still run `omo-review-work` against the original goal and current evidence. Empty diff is never approval.
- `OUTER_CYCLE` aliases the global Ralph iteration `N` only for legacy-compatible filenames. Preserve the review base across every pass. Append an attempt suffix when rerunning a gate within the same iteration so reports are never overwritten.

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

The coordinator saves the report to the stated path. If `omo-review-work` cannot run, record `omo-review-work: NOT_EXECUTED - <reason>`. A missing mandatory `omo-review-work` is always `INCONCLUSIVE`: stop and report the blocker even if optional `review-pr` approved. Never substitute a self-written review.

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
| Approve / Needs Attention / SKIPPED | `INCONCLUSIVE` | INCONCLUSIVE; produce accessible missing evidence in the next Ralph iteration, or pause for unavailable evidence |
| any | `NOT_EXECUTED` | INCONCLUSIVE; required final gate unavailable |
| NOT_EXECUTED | any | INCONCLUSIVE; an attempted optional gate failed and has no usable verdict |
| Request Changes (1+ Critical) | any | REQUEST_CHANGES; merge both gates' blocking findings, deduplicated by file and defect mechanism |

- An `INCONCLUSIVE` whose evidence is genuinely unavailable to the loop (production access, a business decision, a third-party response) is an `ASK_USER` escalation that does not reserve another iteration; already dispatched work remains counted. Present the exact missing evidence and pause.
- Nits and `[Suggestion]` findings never affect the decision.

```
APPROVE
  -> append gate paths/outcomes to CYCLE_LOG and LEDGER -> Ralph completes -> Phase 7
REQUEST_CHANGES or recoverable INCONCLUSIVE
  -> append blocking findings or missing evidence
  -> return to Ralph; check shared cap and stuck history before reserving next N
  -> next pass applies minimal directives, validates, runs all review lanes and QA,
     then runs the final gate again against the same task-wide review base
Unavailable evidence or missing required gate
  -> append exact blocker and next action -> pause without completion
```

## 6e: Oracle consult

Use Ralph's same blocker history across synthesis, QA, and final gates. Compare findings by file and defect mechanism, including missing evidence, not line number or wording. After two consecutive iterations with the same blocker, consult `omo-oracle` with the exact findings, saved report paths, approaches tried, current diff, and remaining shared budget. The same blocker in three consecutive iterations stops the run.

| Oracle response | Action |
|---|---|
| Concrete alternative approach | Append as directives for the next Ralph iteration, if permitted by its cap and stop rules |
| Reviewer expectation ambiguous or business judgment needed | `ASK_USER`; pause and record the decision needed |
| Implementation already correct, reviewer too strict | Save reasoning as disputed-finding evidence for a fresh independent review; never substitute oracle approval |
| Systemic design problem | Escalate with analysis and stop |

Append oracle responses verbatim to `CYCLE_LOG` and reference them in `LEDGER`. An oracle consult never grants iterations, clears unanswered decisions, or bypasses a required gate.

## Phase 7

Present the final report (template in `templates.md`) in the response, not as a new review file. Link every saved gate report by absolute path. Include the External Library Contract Checks evidence and gate decision, or the explicit N/A reason.
