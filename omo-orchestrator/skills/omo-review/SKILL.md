---
name: omo-review
description: OMO-style PR review gate for evidence-first security, robustness, quality, goal alignment, scope control, and missing validation.
argument-hint: [diff-or-goal]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Review

Use this skill before handing off changes that touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs. Treat it as a PR-style gate with one completion state: `APPROVE`.

## Review Areas

- Goal alignment.
- Security and privacy risk.
- Robustness and edge cases.
- Code quality and maintainability.
- Test and validation coverage.
- Scope creep and unrelated changes.
- Domain scope filtering: ignore incidental AI harness, bot, generated-analysis, or review-tool noise unless the task explicitly changes that tooling.
- File understanding: identify each changed file's role and local change before judging it.
- Pre-finding verification: check existing patterns, contracts, callers, or tests before flagging uncertain issues.
- Behavior parity: when replacing behavior, verify whether differences are intentional and safe.
- Lifecycle checks: for jobs, schedulers, retries, recovery, admin data, imports, exports, and manual correction flows, model repeated execution cycles.
- Release checks: when the change is publish-facing, verify version metadata, package contents, docs, migration notes, and unpublished-change impact.
- Security checks: distinguish confirmed vulnerabilities from hardening notes by proving source, sink, attacker control, preconditions, and impact.

Findings come first and must include concrete evidence. If no findings are found, state residual risks and what was not tested.

Evidence means file paths, symbols, caller or callee references, test names, diagnostics, or command results. A vague concern is not enough for `REQUEST_CHANGES`.

## Report Contract

- Decision: `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`.
- Scope reviewed.
- Blocking findings with file references and evidence.
- Warnings or non-blocking improvements.
- Verified non-issues, separate from findings, with evidence that disproves each suspected concern.
- Missing validation.
- Residual risks.
- Approval evidence that supports every required final check when the decision is `APPROVE`.
- Release or security escalation needed, if applicable.

Do not escalate a finding to blocking unless the evidence shows a real contract break, user-visible risk, data-loss path, security issue, or verification gap that could hide one.

Do not convert every checklist item into a finding. A finding must be actionable, applicable, and proportional to the risk.

## Final Outcome Rules

- `APPROVE` is the sole completion state. Return it only when evidence verifies requested scope, task-specific constraints, dependency and retry state, executable QA evidence, validation results, and handoff completeness. Apply content-only checks, including unsupported automation, hooks, runtime engines, scripts, dependencies, and provider-specific behavior, only when the original task, repository, or plugin contract requires them. For release-facing changes, also verify plugin and marketplace version parity.
- `REQUEST_CHANGES` requires confirmed findings. Append the outcome and evidence to the handoff ledger, then route only the affected area through a bounded targeted fix, affected validation, and re-review.
- `INCONCLUSIVE` means required evidence is missing, unavailable, or untrustworthy. It blocks completion. Append the exact evidence gap, blocker, owner, and next action to the handoff ledger before obtaining the evidence or handing the blocker off.

Append either non-approval outcome to the handoff ledger before retrying or stopping.

Do not approve because a review found no issue by inspection alone. Cite the validation, QA, dependency, retry, and scope evidence that supports approval.
