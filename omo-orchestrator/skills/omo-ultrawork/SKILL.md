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

1. Split work into independent waves.
2. Give each wave one owner, one scope, and one evidence target.
3. Keep follow-up bounded. If a delegated or parallel track stalls, do one follow-up pass, then record the gap and stop waiting.
4. Merge only after each wave reports concrete evidence.
5. Run a manual QA gate before final handoff.

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
