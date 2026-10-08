---
type: llm
weight: 1
---

Score 1 only if the review points out that retrying charge() after an error can charge the customer twice, because (per src/payments/client.js) a TimeoutError can happen after the charge was captured, and the retry passes no idempotencyKey. Score 0 if the review does not identify the double-charge risk.
