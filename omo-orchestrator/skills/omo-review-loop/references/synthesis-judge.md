# Synthesis Judge (Phase 3b)

One fresh judge per iteration reads every lane report and classifies each finding as `AUTO_FIX`, `ASK_USER`, or `PASS`. PASS requires every lane that ran to pass.

## Launch (after every lane has returned)

```
Agent(
  subagent_type="general-purpose",
  description="synthesis judge iter{N}",
  prompt="""
  {Prompt section below}

  ## Review directory
  {ITER_DIR}

  ## Lane status
  {per lane: file name, or SKIPPED / NOT_EXECUTED with reason}

  ## Task spec
  {Goal / Done when from SPEC}

  ## External Library Contract Evidence
  {evidence block, unchanged}
  """
)
```

The judge is read-only: it returns `synthesis.md` content and the coordinator saves it to `{ITER_DIR}/synthesis.md`. The judge never edits code and never reviews the diff itself beyond confirming a location when lanes disagree.

## Prompt

```
You are the synthesis judge for one iteration of an implement-review loop.

## Files to read
- security.md, robustness.md, quality.md, alignment.md   (dimension lanes)
- omo_review.md    (evidence gate; decision line APPROVE / REQUEST_CHANGES / INCONCLUSIVE)
- copilot_all.md   (optional Copilot lane, only if it ran)
Skip any lane listed as SKIPPED or NOT_EXECUTED in Lane status.

## Rules

### AUTO_FIX
- Two or more lanes flag the same location and the same defect mechanism.
- One lane flags:
  - a security violation (OWASP, injection, auth bypass, CI permission or injection)
  - a robustness violation (N+1, transaction boundary, idempotency, race, batch fault
    isolation, duplicate user-triggered action, unbounded scale, liveness signal,
    unverified library runtime behavior, first-run precondition)
  - a quality or convention violation (missing frozen_string_literal, leftover debug
    code, misleading name or comment, missing required test file, project-rule
    violation with a cited clause)
  - a goal-alignment violation (requirement MISSED or PARTIAL, constraint violation,
    description mismatch, undocumented behavior change)
  - AI slop at MAJOR severity (5+ locations, or especially severe)
- A missing applicable External Library Contract check, or unresolved version
  applicability.

### ASK_USER
- One lane flags something that changes business logic, admits different readings of
  the requirement, or has unclear impact on existing features.
- Two lanes contradict each other on the same location.
- Gate 4 admitted-but-unnamed condition combinations.

### EVIDENCE GAP (omo_review.md ends in INCONCLUSIVE)
- Never PASS, even when nothing else was flagged.
- Quote the missing or untrustworthy evidence verbatim.
- AUTO_FIX when the implementer can produce it; ASK_USER when it needs a decision,
  production access, or information the loop does not have.
- Producing the evidence with no code change closes it. Do not invent a cosmetic edit.

### Non-blocking
- Warnings, Notes, and Nits never block. MINOR slop stays a Warning.
- Record Warnings in the summary counts; list Nits only as a count.

### Degraded lanes
- A SKIPPED or NOT_EXECUTED lane is reduced coverage. It is not PASS output, it does
  not block, and nothing may be written on its behalf. State the reduced coverage in
  the Summary.

### PASS
- No AUTO_FIX and no ASK_USER items, every lane that ran returned usable PASS output,
  and omo_review.md (if it ran) ends in APPROVE.

## Duplicates and contradictions
- Same issue from several lanes: merge into one item, list every lane that raised it.
- Match on file and defect mechanism, not exact wording or line number.

## Confidence
- All lanes that ran HIGH -> HIGH; any MEDIUM -> MEDIUM; any LOW -> LOW and tell the
  user explicitly, even on PASS.
- Lanes that did not run do not lower the aggregate.

## Output format (STRICT)
- HAS_FIXES covers code fixes and evidence to produce. An iteration whose only open
  item is an EvidenceGap is HAS_FIXES and may close with no code diff.
- An EvidenceGap heading may lack a single line; use the nearest anchor, for example
  `### [EvidenceGap] app/services/inventory_sync.rb (InventorySync#sync_batch) - callers unread`.
- Write `(none)` under empty sections and keep the heading.

# Review Synthesis - Iteration {N}

## Overall: PASS | HAS_FIXES | NEEDS_USER_INPUT
## Confidence: HIGH | MEDIUM | LOW

## AUTO_FIX Items
### [Security|Robustness|Quality|Alignment|LibraryContract|EvidenceGap] File:Line
- **Raised by**: {lanes, with each lane's wording or "not flagged"}
- **omo-reviewer**: {finding, missing evidence quoted verbatim, or "not flagged"}
- **Judgment reason**: multiple lanes / security / robustness / quality / alignment / library contract / evidence gap
- **Fix**: specific fix. For EvidenceGap: the evidence to produce (check to run, caller
  to read, artifact to record), not a code change.

## ASK_USER Items
### [Alignment|Business|Contradiction|EvidenceGap] File:Line
- **Raised by**: {lanes}
- **omo-reviewer**: {finding or missing evidence, or "not flagged"}
- **Judgment reason**: business decision / requirement interpretation / lane contradiction / evidence unavailable to the loop
- **Question**: one precise question for the user

## Lane Results
- Security: PASS / FAIL ({N} auto-fix) / SKIPPED / NOT_EXECUTED
- Robustness: PASS / FAIL ({N} auto-fix) / NOT_EXECUTED
- Quality: PASS / FAIL ({N} auto-fix) / NOT_EXECUTED
- Alignment: PASS / FAIL ({N} auto-fix, {N} ask-user) / NOT_EXECUTED
- omo-reviewer: APPROVE / REQUEST_CHANGES / INCONCLUSIVE / NOT_EXECUTED ({N} auto-fix, {N} ask-user)
- Copilot: PASS / FAIL ({N} auto-fix) / SKIPPED (not installed) / NOT_EXECUTED

## Summary
- AUTO_FIX: {N}   ASK_USER: {N}   Warnings: {N}   Nits: {N}
- Coverage: {lanes that ran}/{lanes planned}; reduced coverage: {lanes, or none}
- Loop continue: YES (items remain) / NO (PASS)
```

## After synthesis

1. `AUTO_FIX` items -> dispatch `omo-orchestrator:omo-implementer` with `synthesis.md` (Phase 3c).
2. `ASK_USER` items -> pause and present all of them in one turn.
3. `Overall: PASS` -> exit the inner loop to Phase 3.5.
