# Domain Risk Checklists

Walk the checklist for each domain the target touches. Each item is a candidate case; keep the ones that apply to the code.

## Money and quantities

- Rounding mode and the point where rounding happens (per line or on the total).
- Float use for money (should be decimal or integer minor units).
- Zero, negative, and maximum amounts; refunds and credits.
- Currency mismatch and currencies with 0 or 3 decimal places.
- Tax inclusive versus exclusive, and tax rate changes on a date.
- Sum of parts equals the total after rounding (allocation, splitting).

## Dates, times, and time zones

- The user's time zone versus the server's and the DB's (UTC storage).
- Start and end of day, month, and year; inclusive versus exclusive end.
- Month end (31st to a 30-day month, February 28 and 29), leap years.
- Daylight saving transitions where the zone has them.
- Date-only versus timestamp comparison.
- Freeze time in tests the way the project does (`travel_to`, `Timecop`, `jest.useFakeTimers`, `vi.setSystemTime`).

## Authorization and multi-tenancy

- Each role, including no login and an expired session.
- Owner versus another user of the same role.
- Records of another tenant or organization (should be invisible, not just forbidden).
- Soft-deleted, archived, or suspended records and users.
- Parameter tampering: an ID or a role field sent in the request body.

## State machines and workflows

- Each valid transition and its side effects.
- Events on terminal states, repeated events (idempotency), out-of-order events.
- Concurrent transitions on the same record.

## External APIs and I/O

- Success, client error (4xx), server error (5xx), timeout, malformed body.
- Retry count and backoff, and that a non-retryable error is not retried.
- Partial failure in a batch.
- Rate limit responses.
- Stub at the boundary the project already stubs (WebMock, VCR, `msw`, `nock`, a client double).

## Concurrency and jobs

- Double submit and duplicate job delivery (idempotency keys, unique constraints).
- Lock contention or timeout.
- Job retried after a partial write.

## Text and input

- Empty string versus nil or undefined versus whitespace only.
- Multibyte text (Japanese, emoji), full-width versus half-width characters, length counted in characters versus bytes.
- Leading and trailing whitespace, case sensitivity.
- Injection-shaped input where it reaches SQL, HTML, or a shell.

## Collections and pagination

- Empty, one item, exactly a page, one over a page.
- Sort stability with ties, and the order when no sort is given.
- N+1 queries where the project tests for them.
