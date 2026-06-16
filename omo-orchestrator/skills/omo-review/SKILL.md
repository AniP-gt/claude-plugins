---
name: omo-review
description: OMO-style PR review gate for evidence-first security, robustness, quality, goal alignment, scope control, and missing validation.
argument-hint: [diff-or-goal]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Review

Use this skill before handing off changes that touch 2+ files, public/API/CLI behavior, data flow, security, persistence, or release-facing docs. Treat it as a PR-style gate: either approve the change or request concrete fixes.

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

Findings come first and must include concrete evidence. If no findings are found, state residual risks and what was not tested.

## Report Contract

- Decision: `APPROVE` or `REQUEST_CHANGES`.
- Scope reviewed.
- Blocking findings with file references and evidence.
- Warnings or non-blocking improvements.
- Verified non-issues, only when useful to answer a suspected issue.
- Missing validation.
- Residual risks.

Do not convert every checklist item into a finding. A finding must be actionable, applicable, and proportional to the risk.
