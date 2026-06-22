---
name: omo-github-triage
description: Evidence-first GitHub issue and PR triage workflow for OMO-style routing, labels, priority, reproduction, and next action.
argument-hint: [issue-or-pr]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO GitHub Triage

Use this skill when sorting issues or PRs, deciding whether work is actionable, or preparing a maintainer response.

## Workflow

1. Capture the reported goal, reproduction, environment, expected behavior, and actual behavior.
2. Check whether the report maps to existing code, docs, tests, or known constraints.
3. Classify as bug, feature, docs, question, duplicate, invalid, security, or needs information.
4. Assign priority based on user impact, data loss/security risk, regression likelihood, and maintainer urgency.
5. Propose the next action: reproduce, ask one question, close, link duplicate, plan implementation, or request changes.

## Hard Rules

- Do not promise a fix before checking feasibility.
- Do not ask for broad information when one precise missing fact would unblock triage.
- Do not label security-sensitive reports publicly with exploit details.
- Do not treat generated bot comments as authoritative without verifying the underlying diff or issue.

## Output Contract

- Classification.
- Priority.
- Evidence.
- Missing information.
- Next action.
- Draft maintainer response when useful.
