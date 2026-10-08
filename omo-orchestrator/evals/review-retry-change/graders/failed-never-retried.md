---
type: llm
weight: 1
---

Score 1 only if the review points out that invoices marked "failed" are never billed again, because src/jobs/scheduler.js only selects invoices with status 'pending' (so a temporary gateway outage now loses revenue silently, where before the invoice stayed pending and the next run retried it). Score 0 if the review does not connect the "failed" status to the scheduler query.
