# Error Recovery

## Classes

Check the error name first, then the message. STOP patterns win over RETRYABLE. Unknown errors default to NON_RETRYABLE.

| Class | Typical names | Message patterns | Recovery |
|---|---|---|---|
| RETRYABLE | rate limit, model unavailable, connection, expired token | `rate limit`, `too many requests`, `429`, `unavailable`, `try again`, `overloaded`, `502`, `503`, `504`, `timeout`, `network error` | Wait briefly, retry once, then switch approach. Escalate after 3 tries |
| STOP | quota exceeded, insufficient credits | `quota exceeded`, `billing limit`, `usage limit reached`, `out of credits`, `payment required`, `subscription limit` | Do not retry. Save progress, report, suggest waiting for reset or another provider |
| NON_RETRYABLE | validation, context length, permission denied, syntax | anything else | Fix the cause (smaller input, correct args, get access), then retry |
| BLOCKED | missing decision, approval, or dependency | n/a | Record the blocker and owner, ask one precise question |

## Tool Failures

| Failure | Recovery |
|---|---|
| Exit 1 | Read stderr, fix the command |
| Exit 2 | Fix usage or syntax |
| Exit 126 | Check permissions; report instead of changing them silently |
| Exit 127 | Command missing: check PATH, propose install, do not install without asking |
| Exit 137 | Killed or OOM: reduce input size |
| Timeout | Raise the timeout or split the work |
| File not found | Verify the path, search with Glob |
| Edit `old_string` not found | Re-read the file, it may have changed |
| File too large | Read with offset and limit |
| Agent returned empty | Retry once with a narrower prompt |
| Agent timed out or hit context limit | Split the task |
| Agent returned an error | Classify it with the table above |

## Escalation

1. RETRYABLE only: retry the same approach.
2. Try an alternative approach.
3. Consult `omo-oracle`.
4. Report to the user: error, each approach tried with its result, oracle advice, current state (done vs remaining), recommended next step.

## Preserve Progress

- Record progress and the error in the handoff before escalating.
- Do not revert successful work because a later step failed.
