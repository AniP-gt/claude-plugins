---
name: omo-review-work
description: Post-implementation review gate with multi-angle findings, explicit PASS or FAIL or INCONCLUSIVE, and fix feedback for blockers.
argument-hint: [diff-or-goal]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Review Work

Use this skill after implementation and before final handoff.

## Review Angles

- Goal alignment.
- Security and privacy.
- Robustness and edge cases.
- Code quality and maintainability.
- Test and validation coverage.
- Scope control and unrelated changes.

## Decision Contract

Return one result only:

- `PASS`: no blocking findings found in the reviewed scope.
- `FAIL`: one or more blocking findings are confirmed with evidence.
- `INCONCLUSIVE`: the review could not close because critical evidence is missing.

## Findings Rules

- A blocking finding must cite concrete evidence.
- Confirm uncertain issues against callers, contracts, tests, or existing patterns before escalating them.
- Feed confirmed blocking findings into the next fix pass.
- Record residual risks and missing validation separately from findings.

## Report Shape

- Reviewed scope.
- Decision.
- Blocking findings.
- Non-blocking warnings.
- Missing evidence.
- Required next action.
