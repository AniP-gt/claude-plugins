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

Track a comparable progress metric per iteration (error count, failing tests, open review findings).

| Situation | Action |
|---|---|
| Same metric for 3 iterations | STOP, report the stuck items |
| Metric increasing | STOP, revert the last change, report |
| Different errors each time (churn) | WARN, switch strategy |
| Over 30 minutes on one task | WARN, confirm progress is real |

Partial progress counts: if the metric dropped and then stalled, report what was fixed and stop only on the remainder.

## Self-Check Before Each Call

1. Same tool and arguments as the last call? Change the arguments or the tool.
2. Third attempt on the same error? Change the approach entirely.
3. Delegating to the agent that delegated to me? Pick another owner.
