# Circuit Breaker Thresholds

Content-only guard. Claude Code does not count calls for you; the operator or coordinator applies these limits by inspection.

## Tool Loops

Call signature = tool name + normalized arguments.

| Condition | Threshold | Action |
|---|---|---|
| Same tool, same arguments | 5 consecutive | STOP, change approach, report |
| Same tool, different arguments | 10 consecutive | WARN, confirm it is a real batch |
| Any tool in one task | 50 total | WARN, check scope and progress |

Common causes: retrying the same error without changing anything, re-running a query that matches nothing, a fix that recreates the error it fixes.

After 3 distinct approaches fail, consult `omo-oracle` or ask the user.

## Delegation Loops

| Limit | Value |
|---|---|
| Delegation depth | 3 levels (A -> B -> C, then stop) |
| Top-level agent spawns | 10 per task |
| Circular delegation (B delegates back to A) | Break the chain: pick a different specialist or finish the step without delegating |

## Stuck Iterations (ralph loop, review loop)

Use `omo-ralph-loop` and its `references/iteration-guards.md` as the sole implementation/review iteration policy. Track blocker identity and validated progress in the same ledger; do not create another counter or reset its budget. Equal error counts can hide different errors, so a flat metric alone does not prove the same blocker recurred. Local tool and delegation recovery limits above remain in force and may stop sooner.

## Self-Check Before Each Call

1. Same tool and arguments as the last call? Change the arguments or the tool.
2. Third attempt on the same error? Change the approach entirely.
3. Delegating to the agent that delegated to me? Pick another owner.
