# Output Templates

## Phase 4: Review summary

```markdown
## Implementation Pass Report (final gate pending)

### What was done
- {summary}

### Loop Summary
| Item | Value |
|---|---|
| Loop iterations | {N}/{CAP} |
| Final result | PASS / PASS with warnings / STOPPED at max iterations |
| Total blocking issues | {N} |
| Total warnings | {N} |
| AUTO_FIX applied | {N} |
| ASK_USER count | {N} |
| Remaining unresolved | {N} (reasons) |
| Lane coverage | {lanes run}/{lanes planned}; skipped: {Copilot not installed / none} |

### Iteration Breakdown
| Iteration | Blocking | Warning | AUTO_FIX | ASK_USER | Result |
|---|---|---|---|---|---|
| Iter 1 | {N} | {N} | {N} | {N} | FAIL/PASS |
| **Total** | **{N}** | **{N}** | **{N}** | **{N}** | |

### Review History per Lane
| Lane | Iter 1 | Iter 2 | Iter 3 | Final |
|---|---|---|---|---|
| Security | FAIL ({N}) | PASS (0) | - | PASS |
| Robustness | FAIL ({N}) | PASS (0) | - | PASS |
| Quality | FAIL ({N}) | PASS (0) | - | PASS |
| Alignment | PASS (0) | - | - | PASS |
| omo-reviewer | INCONCLUSIVE ({N} gaps) | APPROVE | - | APPROVE |
| Copilot | SKIPPED (not installed) | SKIPPED | - | SKIPPED |

The omo-reviewer cell is its decision line (`APPROVE` / `REQUEST_CHANGES` / `INCONCLUSIVE` / `NOT_EXECUTED`). Count an evidence gap under the AUTO_FIX or ASK_USER column it was classified into.

### Evidence Gaps
| Iter | Missing evidence (verbatim) | Closed by | Status |
|---|---|---|---|
| 1 | {...} | {evidence produced / code change} | closed / open |

### Blocking Issues Fixed (all iterations)
1. [Security] File:Line - description -> AUTO_FIX (Iter 1)

### ASK_USER Items and Decisions
| # | Issue | User decision |
|---|---|---|
| 1 | {...} | Fix / Skip / Deferred |

### Verification
- Typecheck: PASS / FAIL / unavailable
- Tests: {N} passing, {N} failing
- Lint: PASS / FAIL / unavailable
- Phase 3.5 (Verify in Action): PASS / FAIL / SKIP ({reason})

### External Library Contract Checks
{per library: resolved version, source, version applicability, verified contract,
runtime evidence, limitations, gate decision; or `N/A - <reason>`}

### Files Changed
- {file}: {one-line description}
```

## Phase 5: User feedback

1. Parse feedback into actionable items.
2. Record them as scoped directives in the controlling Ralph ledger.
3. Return to Ralph for the next reserved iteration: Phase 3c work, validation, review, QA, and gate under the same remaining budget.
4. Summarize again (Phase 4).

```
feedback -> Ralph checks remaining budget -> next work/review pass -> gate
```

## Phase 6c: Cycle log entry

Append to `CYCLE_LOG`; never overwrite. This is loop bookkeeping, not a review.

```markdown
### Ralph iteration {N}/{CAP} (artifact alias: cycle{OUTER_CYCLE})

- **External review**: self-review | review-pr | SKIPPED (unavailable) | NOT_EXECUTED
- **External review verdict**: Approve | Needs Attention | Request Changes | n/a
- **omo-review-work outcome**: APPROVE | REQUEST_CHANGES | INCONCLUSIVE | NOT_EXECUTED
- **Phase 6 decision**: APPROVE | REQUEST_CHANGES | INCONCLUSIVE (mandatory final gate must run)
- **External review output**: {absolute path, or n/a}
- **omo-review-work output**: {absolute path}
- **Diff range**: {CYCLE_START_SHA}..working tree
- **Timestamp**: {TIMESTAMP}
- **Changed files**: {N} (+{N} new untracked)
- **Ralph state**: iteration {N}/{CAP}; phase {phase}; paused: ASK_USER / no; next exact action {action}
- **Blocking findings** (union, deduplicated by file and defect mechanism; carried forward on REQUEST_CHANGES):
  1. {File:Line - description, quoted, gate named}
- **ASK_USER** (external `ask` items that pause the loop, verbatim; or none):
  1. {question, gate named}
- **Unresolved evidence gaps** (from INCONCLUSIVE, verbatim):
  1. {missing evidence}
- **Needs Attention items** (Phase 7 follow-ups, non-blocking: nit/fyi and non-pausing `ask` items):
  1. {File:Line - description}
- **Nits**: {N} (non-blocking)
- **Recurring from previous cycle**: yes / no -> {omo-oracle consulted / n/a}
- **Oracle response** (appended verbatim when produced):
  - Matched row: alternative approach / needs business judgment / disputed finding for independent review / systemic design problem
  - Directive: {verbatim}
  - Controller action: next iteration / paused / exhausted / stuck
  - Remaining Ralph iterations: {CAP minus N}
- **CodeRabbit comments**: skipped (local diff mode) (only when review-pr ran)
```

Special lines: `- **Diff**: empty; mandatory independent final gate still required`; `- **External review**: SKIPPED (unavailable)`; `- **omo-review-work**: NOT_EXECUTED - <reason>`.

## Phase 7: Final summary (in the response, not saved)

```markdown
## Final Review Gate Summary

### What Was Done and Why
Write this section first, in the user's language, so the user does not have to ask for it.
- Purpose: the problem that was happening and who it affected.
- Intent: the main design choices, each with the alternative that was rejected and why.
- Outcome: verified facts only, with numbers where they exist (real-surface runs, query counts, timings, tests added, coverage). Leave out anything not verified.
- Remaining: what this change does not do, and the effect of leaving it.

### Ralph Gate History
| Artifact alias | Ralph iteration | External review (skill: verdict) | omo-review-work | Phase 6 decision | Blocking | Output paths |
|---|---|---|---|---|---|---|
| Cycle 1 | {N}/{CAP} | {verdict or SKIPPED} | {outcome} | {decision} | {N} | {paths} |

One row per gate invocation; preserve earlier report paths. No empty template rows.

### Blocking Findings Fed Back
| Cycle found | Gate | Finding (File:Line - description, or missing evidence) | Resolved in | Status |
|---|---|---|---|---|
| 1 | external review / omo-review-work | {...} | 2 | resolved / evidence produced / recurring / disputed (review pending) |

### Lane and Gate Coverage
- Copilot lane: ran / SKIPPED (not installed) / NOT_EXECUTED
- External review gate: self-review / review-pr / SKIPPED (unavailable) / NOT_EXECUTED
- Other lanes with NOT_EXECUTED: {list or none}

### External Library Contract Checks
{per library evidence and gate decision, or `N/A - <reason>`; never an uncited compatibility claim}

### Final Result
**{APPROVE / MAX_ITERATIONS_REACHED / BLOCKED / STUCK}**

{If APPROVE}
- Cycle {N}: external review 0 `must` and 0 `should` directives (or skipped) and omo-review-work APPROVE
- Needs Attention follow-ups (non-blocking):
  1. {item}

{If MAX_ITERATIONS_REACHED / BLOCKED / STUCK}
- Blocking findings or evidence gaps remain; report the recorded Ralph iteration/cap and stop reason
- Items requiring manual action:
  1. {finding, with the gate that raised it}
- Final external review output: {absolute path or n/a}
- Final omo-review-work output: {absolute path}
- Oracle analysis (if consulted): {summary}

### Next Steps
- Nothing was committed, pushed, or posted. {Commit via omo-git-master if the user asks.}
```
