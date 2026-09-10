---
name: omo-ultrawork
description: High-throughput work mode with independent parallel waves, bounded follow-up, evidence ledger, and a manual QA gate.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Ultrawork

Use this skill for large tasks that can be split into independent waves without losing control of quality.

## Workflow

1. Classify the work once as `LIGHT` or `HEAVY`, record the reason, and only ratchet toward `HEAVY` if risk increases. `HEAVY` applies to cross-system changes, security, external integrations, schema changes, concurrency, or user-requested thoroughness.
2. Split work into dependency-aware waves. Parallelize only independent files, questions, or contracts. Serialize same-file writes, shared mutable state, and named predecessors.
3. Give each wave one owner, one scope, success criteria, and one evidence target.
4. Keep follow-up bounded. If a delegated or parallel track stalls, do one follow-up pass, then record the gap and stop waiting.
5. Merge only after each wave reports concrete evidence.
6. Use a failing-first behavioral proof where the codebase supports it, then capture real-surface QA for the final behavior. Tests alone do not complete a user-facing deliverable.
7. Run an independent final review for `HEAVY` work and for any change that affects public behavior, security, persistence, or release-facing content.

## Evidence Ledger

Track for each wave:

- files read or changed
- symbols or behaviors affected
- tests, diagnostics, or commands run
- review findings or unresolved gaps

## Hard Rules

- Do not split work that shares mutable state unless order is explicit.
- Do not let multiple waves edit the same file without a merge plan.
- Do not duplicate research once one wave owns that question.
- Do not treat silence or partial output as success.
- Do not skip the final QA gate just because parallel work finished fast.
- Do not mark a wave complete until an executor's done claim is independently checked against its declared evidence.
