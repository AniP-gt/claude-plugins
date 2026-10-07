# Evidence-Gate Lane (omo-reviewer) and INCONCLUSIVE Handling

The dimension lanes report what they find. This lane also reports what it could not verify. A concern the other lanes cannot confirm disappears from their reports; here it surfaces as missing evidence and forces the loop to resolve it instead of passing by silence.

## Integration points

| Point | What runs | Role |
|---|---|---|
| Phase 3a | `Agent(subagent_type="omo-orchestrator:omo-reviewer")` | per-iteration evidence-gate review |
| Phase 6b2 | `Skill(skill: "omo-orchestrator:omo-review-work")` | outer-gate second opinion (see `outer-gate.md`) |

## Launch (Phase 3a, same message as the other lanes)

```
Agent(
  subagent_type="omo-orchestrator:omo-reviewer",
  model="sonnet",
  description="evidence-gate review iter{N}",
  prompt="""
  Review this iteration's changes as an independent read-only reviewer.
  {Lane Context block from SKILL.md}
  {contents of shared-gates.md}

  ## Mid-work scope
  This is a mid-work iteration review, not the final gate. Review the available
  evidence and state what remains unproven. Do not require final-tree QA artifacts;
  Phase 3.5 and Phase 6 supply those.

  ## Output
  Use the OMO Reviewer output shape: findings first by severity with file references
  and concrete evidence, verified non-issues, scope creep, missing tests or
  validation gaps, residual risks, and stalled or unavailable evidence stated
  separately from confirmed findings. End with `Confidence: HIGH|MEDIUM|LOW` and a
  final decision line of exactly `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`.
  """
)
```

The coordinator saves the returned report to `{ITER_DIR}/omo_review.md`.

## Synthesis effect

| Decision | Effect |
|---|---|
| `APPROVE` | no blocking item; warnings and residual risks are recorded in synthesis |
| `REQUEST_CHANGES` | each confirmed finding is classified by the one-lane rules (security, robustness, quality, alignment -> `AUTO_FIX`; business logic or requirement interpretation -> `ASK_USER`) |
| `INCONCLUSIVE` | never PASS. `AUTO_FIX` when the implementer can produce the evidence (run the test, read the caller, record the library version, add dry-run output); `ASK_USER` when it needs a decision, production access, or information the loop lacks. Quote the missing evidence verbatim. |

- An `INCONCLUSIVE` closed by producing evidence with no code change is a valid resolution. Record the evidence; do not force a cosmetic edit.
- The same missing evidence across 2+ consecutive iterations triggers the Phase 3f oracle consult, like any recurring blocker.
- `REQUEST_CHANGES` or `INCONCLUSIVE` blocks the iteration exactly like a FAIL from a dimension lane.

## Unavailable

If the lane cannot be dispatched, or returns nothing after one bounded `SendMessage` follow-up, record `OMO_REVIEWER: NOT_EXECUTED` in synthesis and continue with the remaining lanes. This is degraded operation, not a blocker. Never write a self-review in its place.
