---
name: omo-review-work
description: Post-implementation review gate with evidence-based APPROVE, REQUEST_CHANGES, or INCONCLUSIVE outcomes and targeted fix feedback.
argument-hint: [diff-or-goal]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Review Work

Use this skill after implementation and before final handoff.

## Two-Lane Gate

1. Run or verify real-surface QA against the final tree before code review. Cover the named happy path, the riskiest applicable edge, adjacent regression behavior, and every stated success criterion. Each row records scenario, exact command or action, expected result, observed result, verdict, and artifact or evidence location.
2. If any QA row fails, return `REQUEST_CHANGES` without treating a code review as a substitute for working behavior.
3. Launch exactly one independent read-only final reviewer after QA evidence is available. The reviewer audits the goal, constraints, diff, context, security, and QA artifacts. A review after a fix must be fresh and use the updated evidence.
4. Missing, empty, or stalled reviewer output is `INCONCLUSIVE`, never approval.

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
- The real-surface QA matrix, including its evidence artifacts and whether any later edit made a row stale.
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
