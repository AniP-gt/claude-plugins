---
name: omo-review-work
description: Post-implementation review gate with evidence-based APPROVE, REQUEST_CHANGES, or INCONCLUSIVE outcomes and targeted fix feedback.
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
- Release readiness when the work changes published behavior, package metadata, installation, or docs.
- Exploitability when the work touches security-sensitive boundaries.

## Final-Gate Contract

Return one result only:

- `APPROVE`: the sole completion state. Use it only when the requested scope and task-specific constraints are satisfied, blocking findings are closed, and the required evidence supports completion. Apply this plugin's content-only constraints only when the original task, repository, or plugin contract makes them applicable.
- `REQUEST_CHANGES`: confirmed findings require a bounded, targeted fix. Route each finding to the affected change, run its affected validation, then re-review the resulting diff.
- `INCONCLUSIVE`: required evidence is unavailable or cannot be trusted. Completion is blocked until that evidence is obtained, or the exact blocker, owner, and needed decision are recorded in the handoff ledger.

Before returning a final outcome, verify:

- Requested scope and excluded work against the original request.
- The original task, repository, and plugin constraints. When they require content-only work, verify that unsupported automation, hooks, runtime engines, scripts, dependencies, and provider-specific behavior are absent.
- Dependency state and retry evidence, including failed or invalidated attempts where applicable.
- Executable QA evidence and the validation results for the reviewed behavior.
- Handoff completeness: current state, findings, blockers, retries, evidence, and one next exact action.
- Version parity between plugin and marketplace metadata when the change is release-facing.

## Findings Rules

- A blocking finding must cite concrete evidence.
- Confirm uncertain issues against callers, contracts, tests, or existing patterns before escalating them.
- Feed each confirmed finding into one bounded targeted fix, its affected validation, and a re-review.
- Record residual risks and missing validation separately from findings.
- Append `REQUEST_CHANGES` and `INCONCLUSIVE` outcomes to the handoff ledger before retrying or stopping.

## Report Shape

- Reviewed scope.
- Decision.
- Blocking findings.
- Verified non-issues, when evidence disproves a suspected concern.
- Non-blocking warnings.
- Missing evidence.
- Approval evidence, including the checks that justify `APPROVE`.
- Required next action.
- Escalation target: fix pass, pre-publish review, security research, or user decision.
