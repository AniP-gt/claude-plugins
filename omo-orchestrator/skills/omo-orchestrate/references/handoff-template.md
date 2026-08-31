# Durable Handoff Ledger Template

Use one manual ledger for each task at `.claude/omo/handoffs/<task-slug>.md`. Create it before the first recorded phase, then append every phase entry below the existing entries.

No hook, automatic creation, automatic persistence, or automatic continuation is provided. An operator must create, update, read, and resume this record manually.

## Immutable Task Metadata

Fill this block once. Do not edit it after the first phase entry. Record later corrections or scope changes as a new phase entry.

```text
# Handoff Ledger: <task-slug>

Task slug: <task-slug>
Goal: <one-sentence goal>
Scope: <included and excluded work>
Completion promise: <required end state, or not iterative>
Created at: <ISO 8601 timestamp>
Source plan or request: <path or reference>
```

## Append-Only Phase Entry

Copy this block for every phase. Append it after all earlier entries. Do not replace, delete, reorder, or rewrite an earlier entry. Preserve failed attempts. If an earlier entry is wrong, append a correction that identifies it.

```text
## Phase Entry <sequence>: <phase>

Timestamp: <ISO 8601 timestamp>
Task slug: <task-slug>
Phase: <planning | research | implementation | validation | review | fix | release | handoff>
Owner: <operator or assigned role>
Dependency status: <satisfied | pending | blocked | not applicable, with dependency names>
Files or artifacts: <paths, symbols, reports, or none>
Findings or changes: <factual result, including failed attempt when relevant>
Validation command and result: <exact command plus pass, fail, not run, or not applicable>
QA evidence location: <path, report, command output location, or not run>
Retry details: <attempt number, prior entry reference, result, or none>
Final-gate state: <not evaluated | APPROVE | REQUEST_CHANGES | INCONCLUSIVE>
Blockers: <none or concrete blocker, owner, and impact>
Next exact action: <one concrete action, owner, and precondition>
```

## Outcome Rules

- `APPROVE`: the sole completion state. Record the approval evidence for requested scope, task-specific constraints, dependencies and retries, executable QA, validation results, and handoff completeness. Record content-only compliance only when the original task, repository, or plugin contract requires it. For release-facing changes, also record plugin and marketplace version-parity evidence.
- `REQUEST_CHANGES`: retain the confirmed finding and evidence, mark the affected dependency blocked, and make the next exact action a bounded targeted fix, affected validation, and re-review. Append this entry before retrying.
- `INCONCLUSIVE`: retain the missing or untrusted evidence and reason, block completion, and name the evidence or decision needed next. Append this entry before obtaining evidence, handing the blocker off, or stopping.
- Failed attempt: include the attempted action, result, and retry number. A later success does not erase it.

A satisfied completion promise, exhausted retries, or passing validation is not a completion state. Only an `APPROVE` final-gate entry permits completion.

Keep entries factual and easy to inspect. Do not include secrets, tokens, private transcripts, or unrelated context.
