# DB Review Checklist

Paste into the robustness and alignment lane prompts whenever the diff touches DB access, SQL, migrations, indexes, transactions, batch jobs, bulk processing, or lock queries.

## Index utilization
- Does each WHERE column have an index?
- Is the composite-index prefix rule satisfied (leftmost column first)?
- Will production data scale cause a full scan? Require EXPLAIN evidence.
- Is the `WHERE col IN (...)` column the leading index column?

## Lock risks
- Do UPDATE/DELETE go through the PK or a unique index? Range conditions take gap locks.
- Is `SELECT ... FOR UPDATE` minimized?
- Multiple tables locked in one transaction: deadlock risk?
- For `acts_as_paranoid`, is `deleted_at IS NULL` covered by the index?

## Transaction scope
- External API calls, mail, and job enqueue happen outside transactions.
- No N+1 inside a transaction (watch `save!` vs `update_columns`).
- Ruby: variables defined inside a `do...end` block are not visible outside it (NameError).

## Batch-specific
- `find_each` / `in_batches` used, not `.to_a` over everything.
- The same record not re-queried inside a loop.
- Idempotent on re-execution.
- Bullet does not run for Sidekiq jobs or `rails runner` (it hooks Rack middleware). An N+1 claim, present or absent, for job or batch code needs `Bullet.start_request` / `end_request` around the job call, or a measured SQL-count comparison across input sizes. "Bullet did not flag it" or a read-through is not evidence.
- `belongs_to` to an `acts_as_paranoid` model returns nil for a soft-deleted owner. In monitoring or notification jobs, check whether a soft-deleted association (for example a deactivated store) makes message building or the alert condition raise or silently skip, so the job goes quiet exactly when it should alert.

## Migration: add_index risk

When a migration adds an index, confirm the production row count with the user before assessing (`ASK_USER`):

```
## Production data scale confirmation required

Table: `{table_name}`
Index to add: `{column_name(s)}`

Please run in production:
SELECT COUNT(*) AS record_count FROM {table_name};
-- for paranoia tables
SELECT COUNT(*) AS total, COUNT(deleted_at) AS deleted FROM {table_name};
```

| Rows | Risk | Action |
|---|---|---|
| up to 100K | Low | normal `add_index` |
| 100K to 1M | Medium | consider `algorithm: :inplace` |
| 1M+ | High | `algorithm: :inplace` or pt-osc required |
| 10M+ | Critical | pt-osc almost certainly required; consult a DBA |

```ruby
# index on a large table
add_index :table_name, :column_name, algorithm: :inplace, lock: :none
```
