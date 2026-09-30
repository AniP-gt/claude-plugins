# Output Templates

## Phase 4: Inner-loop summary

```markdown
## Implementation Complete

### What was done
- {summary}

### Loop Summary
| Item | Value |
|---|---|
| Loop iterations | {N}/5 |
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
2. Apply them with `omo-implementer` (Phase 3c).
3. Return to Phase 3a with a fresh 5-iteration budget.
4. Summarize again (Phase 4).

```
feedback -> fix -> review loop (max 5) -> summary -> feedback -> ...
```

## Phase 6c: Cycle log entry

Append to `CYCLE_LOG`; never overwrite. This is loop bookkeeping, not a review.

```markdown
### Cycle {OUTER_CYCLE}/3

- **review-pr verdict**: Approve | Needs Attention | Request Changes | SKIPPED (unavailable) | NOT_EXECUTED
- **omo-review-work outcome**: APPROVE | REQUEST_CHANGES | INCONCLUSIVE | NOT_EXECUTED
- **Phase 6 decision**: APPROVE | REQUEST_CHANGES (stricter of the gates that ran)
- **review-pr output**: {absolute path, or n/a}
- **omo-review-work output**: {absolute path}
- **Diff range**: {CYCLE_START_SHA}..working tree
- **Timestamp**: {TIMESTAMP}
- **Changed files**: {N} (+{N} new untracked)
- **Inner loop iterations this cycle**: {N}/5
- **Blocking findings** (union, deduplicated by file and defect mechanism; carried forward on REQUEST_CHANGES):
  1. {File:Line - description, quoted, gate named}
- **Unresolved evidence gaps** (from INCONCLUSIVE, verbatim):
  1. {missing evidence}
- **Needs Attention items** (Phase 7 follow-ups, non-blocking):
  1. {File:Line - description}
- **Nits**: {N} (non-blocking)
- **Recurring from previous cycle**: yes / no -> {omo-oracle consulted / n/a}
- **Oracle response** (appended verbatim when produced):
  - Matched row: alternative approach / needs business judgment / already correct (`ORACLE_OVERRIDE`) / systemic design problem
  - Directive: {verbatim}
  - Effect on OUTER_CYCLE: incremented / not incremented
  - Remaining cycles: {N}
- **CodeRabbit comments**: skipped (local diff mode)
```

Special lines: `- **Phase 6**: SKIPPED - empty diff (treated as APPROVE)`; `- **review-pr**: SKIPPED (unavailable)`; `- **omo-review-work**: NOT_EXECUTED - <reason>`.

## Phase 7: Final summary (in the response, not saved)

```markdown
## Final Review Gate Summary

### Outer Loop Cycle Summary
| Cycle | Inner iterations | review-pr | omo-review-work | Phase 6 decision | Blocking | Output paths |
|---|---|---|---|---|---|---|
| Cycle 1 | {N}/5 | {verdict or SKIPPED} | {outcome} | {decision} | {N} | {paths} |

One row per cycle that ran. No empty template rows.

### Blocking Findings Fed Back
| Cycle found | Gate | Finding (File:Line - description, or missing evidence) | Resolved in | Status |
|---|---|---|---|---|
| 1 | review-pr / omo-review-work | {...} | 2 | resolved / evidence produced / recurring / ORACLE_OVERRIDE |

### Lane and Gate Coverage
- Copilot lane: ran / SKIPPED (not installed) / NOT_EXECUTED
- review-pr gate: ran / SKIPPED (unavailable) / NOT_EXECUTED
- Other lanes with NOT_EXECUTED: {list or none}

### External Library Contract Checks
{per library evidence and gate decision, or `N/A - <reason>`; never an uncited compatibility claim}

### Final Result
**{APPROVE / MAX_CYCLES_REACHED}**

{If APPROVE}
- Cycle {N}: review-pr 0 Critical (or skipped) and omo-review-work APPROVE
- Needs Attention follow-ups (non-blocking):
  1. {item}

{If MAX_CYCLES_REACHED}
- Blocking findings or evidence gaps remain after 3 cycles
- Items requiring manual action:
  1. {finding, with the gate that raised it}
- Final review-pr output: {absolute path or n/a}
- Final omo-review-work output: {absolute path}
- Oracle analysis (if consulted): {summary}

### Next Steps
- Nothing was committed, pushed, or posted. {Commit via omo-git-master if the user asks.}
```
