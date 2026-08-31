---
name: omo-handoff
description: Manual durable handoff workflow for a task-linked append-only phase ledger with evidence, blockers, and one exact next action.
argument-hint: [task-slug]
allowed-tools: Read, Grep, Glob, Edit, Write
user-invocable: true
---

# OMO Handoff

Use this skill when work must survive a context change, an operator change, or a pause between phases. Keep one ledger per task at `.claude/omo/handoffs/<task-slug>.md`.

This is a manual, content-only workflow. It provides no hook, automatic creation, automatic persistence, or automatic continuation. An operator creates the record, appends each entry, and reads it before taking the next action.

## Record Contract

1. Create the ledger from the handoff template before the first recorded phase.
2. Set immutable task metadata once: task slug, goal, scope, completion promise when iterative, creation time, and source plan or request.
3. Do not revise immutable metadata. If the goal or scope changes, append an entry that records the change and its authority.
4. Append one phase entry after each meaningful outcome, including failed attempts, blocked work, review results, and final-gate decisions.
5. Never replace, delete, reorder, or summarize away an earlier entry. Correct an error with a later entry that names the entry being corrected.
6. Read the whole ledger before resuming work. Follow the latest next exact action unless a later user instruction changes it.

## Required Phase Entry

Every entry must include:

- Timestamp.
- Task slug.
- Phase.
- Owner.
- Dependency status.
- Files or artifacts.
- Findings or changes.
- Validation command and result.
- QA evidence location.
- Retry details.
- Final-gate state.
- Blockers.
- Next exact action.

Use explicit values when a field does not apply: `none`, `not run`, `not applicable`, or `unknown`. Keep evidence at a file path, command result, test name, diagnostic, or other inspectable location. Do not put secrets, tokens, private transcripts, or unrelated context in the ledger.

## Outcome Guidance

- `APPROVE`: the sole completion state. Preserve the approval evidence, satisfied dependencies, executable QA evidence, validation results, and handoff completeness. Preserve content-only compliance only when the original task, repository, or plugin contract requires it. For release-facing changes, preserve plugin and marketplace version-parity evidence.
- `REQUEST_CHANGES`: preserve the confirmed finding, evidence, and reviewer or owner. Set the final gate to `REQUEST_CHANGES`, mark the affected dependency blocked, and make the next exact action a bounded targeted fix, affected validation, and re-review.
- `INCONCLUSIVE`: preserve the missing or untrusted evidence and why it is unavailable. Set the final gate to `INCONCLUSIVE`, block completion, and name the exact evidence or decision needed before work resumes or the blocker is handed off.
- Failed attempt: record the attempted action, result, and retry count. Do not rewrite the earlier attempt after a later fix succeeds.

Append `REQUEST_CHANGES` and `INCONCLUSIVE` gate results before retrying or stopping. Keep verified non-issues separate from findings and retain the evidence that disproves them.

## Stop Rules

- Complete only when the final gate is `APPROVE` and the completion promise is met.
- Stop and ask for a decision when a blocker needs external approval, a dependency remains unavailable, or a safe next exact action cannot be named.
- `REQUEST_CHANGES`, `INCONCLUSIVE`, a satisfied completion promise, exhausted retries, or passing validation do not permit completion without `APPROVE`.
- Do not claim that the ledger resumes work on its own. A later operator must read it and manually continue.

Use the [handoff template](../omo-orchestrate/references/handoff-template.md) for the metadata block and every phase entry.
