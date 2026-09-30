# Rigorous Plan Review

Optional lane review of a written draft plan. Use it when `RISK_LEVEL` is `critical` or `high`, or when the user asks for a thorough or high-accuracy plan review. It replaces the single `omo-plan-reviewer` pass in Bounded Plan Review and uses the same budget: one initial pass plus at most two revisions.

This is not `omo-hyperplan`. Hyperplan critiques the problem framing before a plan exists. This review checks a written plan before the approval brief. Passing it never authorizes implementation.

## Risk Level

Classify the touched areas and record `RISK_LEVEL` and `RISK_REASON` in the plan TL;DR. `omo-review-loop` uses the same table, so the value carries into execution unchanged.

| Risk | Area | Review policy |
|---|---|---|
| critical | payment and billing, authn and authz, migrations, personal data | scrutinize every finding |
| high | transactions, external APIs, batch jobs, data integrity, query or index changes, duplicate user-triggered expensive actions | safety and robustness first |
| medium | controllers, services, forms, query objects | standard |
| low | views, serializers, config, tests, docs | suggestion-focused |

Migrations, raw SQL, index changes, explicit transactions, bulk data processing, lock queries, or production backfills force `high` or above. The plan must then carry query and SQL checks, lock scope, rollback, production-scale data volume, and batch fault isolation into its tasks and QA.

## Plan Risk Notes

Record each note that applies in the plan scope section, with the paths to verify:

- Behavior parity: calculations, data correction, persistence or update flows, callbacks, or batch and import behavior are compared with the current source of truth.
- Batch fault isolation: one record or auxiliary recalculation failure must not skip later required steps after earlier writes committed.
- Duplicate request guard: expensive forms, buttons, searches, imports, and downloads need a handler or action-level re-entry guard, not only a disabled state.
- Lifecycle: schedulers, recovery, alerts, admin or master data, imports, exports, and manual correction flows are planned across repeated cycles.
- Description accuracy: the task summary, docs, and PR text match the planned behavior.

## Lane Gates

Paste these into every lane prompt with the full plan text. A single-line summary is not enough context.

1. Verify before flagging. Check that referenced files, symbols, and APIs exist with Glob, Grep, or Read. A missing target is either `new addition required` or not a finding. Unverifiable concerns are not flagged.
2. Domain scope. Judge the product behavior users rely on. Ignore incidental harness, bot, or review-tool work unless the plan targets that tooling.
3. Applicability and proportionality. Block only when the risk follows from the exact planned predicate or path, is reachable in normal operation, lacks an existing mitigation, and needs the proposed fix. Theoretical or manual-only risks become notes unless normal operation can corrupt data, expose security, break a user flow, or leave unrecoverable state.
4. Verified non-issues go to Notes with the disproving predicate or contract, never to Issues.
5. Do not ask for obvious comments, defensive shims, or speculative hardening.
6. Output: `ISSUES_FOUND: YES | NO`, then at most five issues, each with severity (`critical`, `high`, `medium`, `low`), the cited plan task or section, evidence, and the required plan change, then Notes.

Lanes that use `omo-reviewer` review a plan, not a diff. Tell them to return the lane output above instead of `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`.

## Lanes

Launch all six in one message. Each lane may add domain risks the plan implies (payments, webhooks, migrations) under a line starting `Additionally, because this plan involves <domain>`.

| Lane | Agent | Focus |
|---|---|---|
| Executability | `omo-plan-reviewer` | references, task startability, executable QA, `IS-*` mapping, `GAP-*` closure. Keeps its own `OKAY` or `REJECT` output; `REJECT` counts as `ISSUES_FOUND: YES` |
| Strategy | `omo-oracle` | missing dependencies, ambiguous scope, unresolved blockers, reliance on unknown external state, a simpler approach that meets the goal |
| Security | `omo-reviewer` | authn and authz gaps in the design, sensitive data handling, unspecified injection-prone inputs, secrets handling, privilege escalation, mitigations that match existing auth or feature-flag contracts |
| Robustness | `omo-reviewer` | error handling and retry or rollback for external APIs and DB writes, idempotency, irreversible steps without rollback, transactions around unbounded batches, batch fault isolation, duplicate request guards, N+1 or consistency risks absent from QA |
| Quality | `omo-reviewer` | single-responsibility task split, acceptance criteria loose enough to pass slop, QA missing a happy or failure path, naming and API consistency, over- or under-engineering, logic duplicated across tasks, repeated literals where a domain constant fits, redundant queries or collection passes |
| Goal alignment | `omo-reviewer` | tasks outside the goal, deliverables or must-haves without a task, non-goals the plan violates, constraint compliance, behavior parity, at least five edge cases for high-risk goals, description accuracy |

When an agent is unavailable, run that lane as a manual section with the same gates and output, and state which lane was manual.

## Convergence

| Category | Definition | Action |
|---|---|---|
| MULTI | two or more lanes flag the same concern | must fix |
| Single, critical or high | one lane, severity critical or high, passes gate 3 | must fix |
| Single, medium or low | one lane only | fix when cheap, otherwise record in the plan notes |

Do not downgrade a single-lane critical or high issue because no other lane agreed. Do not keep a blocker that fails gate 3 after verification. Record it as a note with the reason.

Loop:

```text
no MULTI and no single critical/high  -> exit, plan review passed
otherwise                             -> revise plan, iteration += 1, rerun all lanes
iteration == 3                        -> exit, report remaining issues as blockers
```

A blocker that survives iteration 3 goes into the approval brief with its evidence and one exact question. Do not call the plan ready.

## Loop History

Include this table in the approval brief:

| Iteration | Exec | Strategy | Security | Robust | Quality | Goal | MULTI | Action |
|---|---|---|---|---|---|---|---|---|
| 1 | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | N | revised or passed |

## Final Verification Wave

Every final plan ends with this wave after all tasks. `omo-ulw-execute` registers it as its own todo and runs it before `omo-review-work`. All four must pass.

- F1 Plan compliance: each must-have exists, each non-goal and must-not has zero matches, deliverables match the plan. Output `Must [N/N] | Must NOT [N/N] | VERDICT`.
- F2 Code quality: typecheck, lint, and tests run; scan for `as any`, empty catches, stray debug output, unused imports, obvious comments, and redundant queries. Output `Build PASS/FAIL | Tests N pass/N fail | VERDICT`.
- F3 QA execution: every task QA scenario plus cross-task integration and edge cases. Output `Scenarios [N/N] | Integration [N/N] | VERDICT`.
- F4 Scope fidelity: each task's action compared with the actual diff, unplanned files listed, behavior parity and description accuracy confirmed. Output `Tasks [N/N] | Unplanned CLEAN/N files | VERDICT`.
