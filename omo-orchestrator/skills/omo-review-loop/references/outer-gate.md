# Phase 6: Outer Gate

Phase 6 runs the installed `self-review` skill and `omo-review-work` on the task-wide local diff and uses their saved reports as the gate. It does not run its own reviewer agents and does not re-implement review logic.

## Use from other entry skills

Other entry skills (`omo-ultrawork`, `omo-ulw-execute`, `omo-mass-ulw`, and direct `omo-ralph-loop` implementation tasks) run the same 6b external review in parallel with their own final gate and merge it with 6d. Differences from `omo-review-loop`:

- `OUTER_DIR` is `<repo root>/docs/reviews/{TASK_ID}/` unless the user or plan names another directory.
- They run 6b alongside their own built-in gate (`omo-reviewer` or `omo-review-work`, as their skill says). They do not add 6b2 on top of it. An agent gate such as `omo-reviewer` returns its result in the reply; quote its decision and blocking findings in the ledger entry instead of saving a separate file.
- External `must` and `should` fix directives become fix work the same way their own gate's blockers do (a graph task, a plan fix task, or a todo). Add that work right away as pending; dispatch it in the next Ralph pass, and when a pausing `ASK_USER` exists, only after the answer arrives.
- Both gates run after the skill's final verification run and are independent, so run them in parallel. When the built-in gate is `omo-review-work`, fill its `Phase 3.5 result` slot with that final verification output.
- In the contract headers, replace `omo-review-loop Phase 6` / `Phase 6b2` with the calling skill and step (for example `omo-ulw-execute Phase 6`).
- "Ledger" and `CYCLE_LOG` both mean the task's handoff ledger `.claude/omo/handoffs/<task-slug>.md` when the skill keeps no `CYCLE_LOG`. "Phase 7 follow-ups" means a `Follow-ups` list in the skill's final report.

They pass their own review base as `CYCLE_START_SHA` and their goal, constraints, and background from the plan, notepad, or ledger. When no `RISK_LEVEL` was recorded, classify the changed areas with the risk table in the `omo-plan` skill's `references/rigorous-review.md`. In 6d their own built-in gate (`omo-reviewer` or `omo-review-work`) takes the `omo-review-work` column, and they record the 6c entry in their Ralph ledger when they keep no `CYCLE_LOG`.

| Gate | Skill | Required | Report |
|---|---|---|---|
| external review | `self-review` (review only), always when installed | `self-review`: required when listed as available | `{OUTER_DIR}/cycle{OUTER_CYCLE}_review_{TIMESTAMP}.md` |
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

## 6b: External review (self-review)

This plugin does not ship `self-review`; it uses the one the user or project installed. Decide whether it runs like this:

1. `REVIEW_SKILL: none` in `SPEC`, `task.md`, or the plan skips `self-review`; record `external review: SKIPPED (REVIEW_SKILL: none)`. Any other `REVIEW_SKILL` value is ignored and `self-review` runs. No other external review skill runs here; `review-pr` is for GitHub PRs and only the user invokes it.
2. `self-review`, when it appears in the available skills list: always run it with the review-only contract below. Its own fix stage never runs here: Ralph owns fixes and the iteration budget, so the findings come back through 6d like any other gate.
3. When `self-review` is not installed: record `external review: SKIPPED (self-review unavailable)` in `CYCLE_LOG`.

Run 6b and 6b2 in parallel, because the reviews are independent and read the same diff. A Skill call runs in the calling context, so dispatch `self-review` to an `omo-external-reviewer` agent, naming the skill and passing the contract below verbatim, while 6b2 proceeds; wait for every lane before 6c. Freeze the tree while they run: no edits until all reports are back. Record `external review: self-review` in `CYCLE_LOG` when it ran.

### self-review (review only)

Invoke `Skill(skill: "self-review", args: <contract>)`. It builds the diff itself from the working tree (committed, uncommitted, and untracked changes since the base), so do not paste the diff:

```
--dry-run    (skips the fix stage only; the report is still saved)
CALLER: omo-review-loop Phase 6 external review gate (non-interactive)
BASE_REF: {CYCLE_START_SHA}
REPORT_PATH: {OUTER_DIR}/cycle{OUTER_CYCLE}_review_{TIMESTAMP}.md (absolute path)
RISK_LEVEL: {RISK_LEVEL}

- Review and report only. Do not apply fixes, commit, stash, switch branches, or
  post anything. Do not ask the user questions; record each one as an `ask` finding.
- Save exactly one report at REPORT_PATH and state that absolute path in your final
  response.

## GOAL
{GOAL}
## CONSTRAINTS
{CONSTRAINTS}
## BACKGROUND
{BACKGROUND}
## External Library Contract Evidence
{evidence block, unchanged}
```

If the external review skill saved the report at a different path than the one requested (for example with a `_2` suffix), record the path it reports and use that file; do not move it. If it reports completion but no file exists at any path it states, re-invoke once. If it fails again, record `external review: NOT_EXECUTED - no report` and continue with 6b2. Never infer a verdict from the chat response.

### Review input block

`omo-review-work` in 6b2 takes this block inline, because it reviews a diff it does not build itself:

```
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

## 6b2: omo-review-work (always)

Run it even when the external review returned Request Changes; the findings are merged in 6d and skipping it loses the evidence-gap signal. Invoke `Skill(skill: "omo-orchestrator:omo-review-work", args: <contract>)`:

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

{the review input block above, in full. `self-review` builds its own diff, so its contract carries none}
```

The coordinator saves the report to the stated path. If `omo-review-work` cannot run, record `omo-review-work: NOT_EXECUTED - <reason>`. A missing mandatory `omo-review-work` is always `INCONCLUSIVE`: stop and report the blocker even if the optional external review approved. Never substitute a self-written review.

## 6c: Read the saved reports

- `self-review` writes its report in Japanese. Extract the verdict from the `## 判定:` heading (`Approve` / `Request Changes` / `Needs Attention`) and quote the `Findings: must` items verbatim (file, line, description). Also quote the `Findings: should` items: they are fix directives in the same way, unless the fix changes a public API, schema, applied migration, or external contract, contradicts the GOAL or CONSTRAINTS, or conflicts with another finding; those become `ASK_USER`. An `ask` item whose answer could change a fix directive, the GOAL, or a contract becomes `ASK_USER` and pauses before the next iteration. Any other `ask` the code or evidence does not answer is carried to Phase 7 as a question for the user, and the fix pass proceeds. `nit` and `fyi` items are Phase 7 follow-ups.
- `omo-review-work`: extract the decision (`APPROVE` / `REQUEST_CHANGES` / `INCONCLUSIVE`), blocking findings, and for `INCONCLUSIVE` the exact missing evidence, verbatim.
- Do not write a third, competing review report. Append one entry to `CYCLE_LOG` (template in `templates.md`) with both decisions, both absolute report paths, `CYCLE_START_SHA`, `TIMESTAMP`, and the blocking findings carried forward. Never overwrite earlier entries. `CYCLE_LOG` is a real file so the loop can resume after a context reset, and it is the authoritative source for a previous cycle's report paths (never glob for them).

## 6d: Verdict mapping

Every gate that ran must clear; the stricter decides.

| external review | omo-review-work (or the entry skill's built-in gate) | Phase 6 decision |
|---|---|---|
| Approve with 0 `must` and 0 `should` directives, or SKIPPED | `APPROVE` | APPROVE |
| Approve / Needs Attention with 0 `must` and 1+ `should` directive | `APPROVE` | REQUEST_CHANGES; the `should` directives go to the next Ralph pass |
| Needs Attention (0 `must`, 0 `should` directives) | `APPROVE` | APPROVE; carry the items into Phase 7 as follow-ups |
| Approve / Needs Attention / SKIPPED | `REQUEST_CHANGES` | REQUEST_CHANGES; omo findings become fix directives |
| Approve / Needs Attention / SKIPPED | `INCONCLUSIVE` | INCONCLUSIVE; produce accessible missing evidence in the next Ralph iteration, or pause for unavailable evidence |
| any | `NOT_EXECUTED` | INCONCLUSIVE; required final gate unavailable |
| NOT_EXECUTED | any | INCONCLUSIVE; an attempted optional gate failed and has no usable verdict |
| Request Changes (1+ `must`) | any | REQUEST_CHANGES; merge both gates' blocking findings, deduplicated by file and defect mechanism |

- An `INCONCLUSIVE` whose evidence is genuinely unavailable to the loop (production access, a business decision, a third-party response) is an `ASK_USER` escalation that does not reserve another iteration; already dispatched work remains counted. Present the exact missing evidence and pause.
- Nits and `[Suggestion]` findings never affect the decision.
- A pausing `ASK_USER` does not change the decision. Record `REQUEST_CHANGES` (or the decision the table gives) plus `paused: ASK_USER`, and hold every fix directive until the answer, so the next pass carries all of them together.

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
