---
name: omo-handoff
description: Manual handoff workflow. Keeps a task-linked append-only phase ledger, or writes a short brief to continue in a fresh session instead of compacting.
argument-hint: [task-slug]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(orca:*)
user-invocable: true
---

# OMO Handoff

Use this skill when work must survive a context change, an operator change, or a pause between phases. Keep one ledger per task at `.claude/omo/handoffs/<task-slug>.md`.

This is a manual workflow. It provides no hook, automatic creation, automatic persistence, or automatic continuation. An operator creates the record, appends each entry, and reads it before taking the next action. The only command it runs is the Orca launch in [Fresh-Session Brief](#fresh-session-brief), and only when the user asks for it in that turn; it never starts a session on its own.

## Fresh-Session Brief

A long conversation resends every earlier turn, including dead-end hypotheses, failed commands, and rejected options. `/compact` lets the model choose what survives and keeps adding to the same session. A brief lets you choose, and the next session starts from zero.

Suggest a brief when any of these hold: the approach changed and the earlier attempts no longer apply, two or more failed attempts sit in the history, the user says they will resume later (another day or after a long break, when the prompt cache will have expired), or the task is switching. Write it when the user agrees or asks for a handoff.

Write `.claude/omo/briefs/<task-slug>.md`, kept apart from the ledgers so a resume summary never mistakes one for the other. Use only lowercase letters, digits, and hyphens in `<task-slug>`, because it also goes into the commands below. Unlike the ledger the brief is a snapshot: replace it on each handoff. Keep it under about 40 lines and point to files instead of pasting their content.

```text
# Brief: <task-slug>
Written: <ISO 8601 timestamp>   Ledger: <path or none>   Branch: <branch>

## Goal
<one sentence>

## Decisions changed
<each decision, what it replaced, and why>

## Current state of the code
<changed files, what works, last validation command and result>

## Directions that failed
<what was tried, how it failed, why not to retry>

## Unverified
<assumptions and checks not yet run>

## Next exact action
<one concrete action>
```

Then start the next session:

- Inside Orca (`orca worktree current --json` reports `"ok": true`) and the user asked to continue in a new session: run `orca terminal create --worktree active --title <task-slug> --command claude --json`, then `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json`. Send only when the result reports `satisfied: true`: `orca terminal send --terminal <handle> --text "Read .claude/omo/briefs/<task-slug>.md and continue from its next exact action." --enter --wait-submit 15 --json`. On `satisfied: false`, wait once more with a larger timeout; if it still fails, report that the handoff did not start and do not send. Once the send reports `accepted: true` and the submission is observed, report the handle and stop working in this session; if only input acceptance is reported, tell the user to check that terminal instead of resending.
- A `runtime_access_denied` (EPERM) error means the command sandbox blocked the Orca socket, not that Orca is absent. Tell the user so, and use the paste fallback below unless they choose to allow the Orca command outside the sandbox.
- Otherwise: print that same one-line prompt and tell the user to run `/clear` (or open a new session) and paste it.

Do not put secrets, tokens, or transcript excerpts in the brief.

## Record Contract

1. Create the ledger from the handoff template before the first recorded phase.
2. Set immutable task metadata once: task slug, goal, scope, completion promise when iterative, creation time, and source plan or request.
3. Do not revise immutable metadata. If the goal or scope changes, append an entry that records the change and its authority.
4. Append one phase entry after each meaningful outcome, including failed attempts, blocked work, review results, and final-gate decisions.
5. Never replace, delete, reorder, or summarize away an earlier entry. Correct an error with a later entry that names the entry being corrected.
6. Read the whole ledger before resuming work. Follow the latest next exact action unless a later user instruction changes it.

## Resume Summary

When the user asks to resume or "where was I", list `.claude/omo/handoffs/`, read the matching ledger in full, and present before acting:

- Goal, source plan, and last entry timestamp.
- Progress: count top-level checkboxes in the source plan (`- [x] N.` done, `- [ ] N.` pending, including final-wave `F<N>.` items). Ignore nested acceptance-criteria checkboxes.
- Completed, in progress, and remaining tasks by title.
- Open blockers, recorded decisions, and scope boundaries.
- The latest next exact action, then confirm it with the user before continuing.

If no ledger exists, say so and offer to start one. Do not guess prior state from memory.

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

- `APPROVE`: the sole completion state. Preserve the approval evidence, satisfied dependencies, executable QA evidence, validation results, and handoff completeness. Preserve content-only compliance only when the original task, repository, or plugin contract requires it. For release-facing changes, preserve evidence of version agreement across every manifest that declares the version.
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
