---
name: omo-test-design
description: Design test cases (RSpec, Jest, and similar) that follow the project's existing spec style, using black-box and white-box techniques and domain risk checklists. Returns a case table for approval, then writes the specs. Use when asked to design, list, or add test cases or specs.
argument-hint: [target code or behavior]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Test Design

Use this skill to decide which test cases a change or an existing unit needs, and to write them in the style the project already uses. It designs cases; it does not change production code. When `omo-implement` decides tests are required and the cases are not obvious, it calls this skill with a write-directly contract (see step 7). `omo-plan` does not call it; a plan names it in the task so the executor runs it.

## Workflow

1. **Scope the target.** Name the unit under test (class, module, function, endpoint, component) and the behavior in scope. Read the code, its callers, and any spec, issue, or PR text that states expected behavior. When expected behavior is not stated anywhere and the code is the only source, mark each case derived from code alone as `oracle: code` so the reader knows the expectation was not confirmed by a spec. When every case is derived from code alone, say so once above the table instead of marking each row (the Note column then carries only other notes); in the spec, one comment may cover a group of such cases.
2. **Detect the project's test style.** Read 2 to 3 existing spec files nearest to the target (same directory, same layer; when the target has no spec, specs of the same layer or of its callers; when fewer than 2 exist, read what exists and say how many you read) plus the shared setup files and any project rules for tests (for example `.claude/rules`). Record the conventions listed in `references/frameworks/<framework>.md` (for RSpec: `rspec.md`; for Jest or Vitest: `jest.md`). For another framework, record the same categories: file location and naming, grouping, setup and fixtures, test doubles, assertion style, and shared helpers. Follow what the project does even when it differs from the framework's general best practice; report the difference as a note, not a change. Before planning in-memory test data (`build`, plain objects), open the factory or fixture definition and confirm it does not persist associations.
3. **Find existing coverage.** Search existing specs for the target and list what they already cover, so new cases do not duplicate them. When a coverage report exists, use it; do not run a full coverage job only for this step unless the user asks.
4. **Derive cases.** Apply the techniques in `references/techniques.md`:
   - Black-box first, from the stated behavior: equivalence partitions, boundary values, decision tables for combined conditions, state transitions for lifecycles, pairwise for many independent parameters.
   - White-box next, from the code: every branch outcome, each condition in a compound condition that can flip the result, loop counts 0, 1, and many, early returns, rescue or catch paths, and side effects (writes, enqueued jobs, sent mail, emitted events).
   - Domain risks: walk the checklist in `references/domains.md` for each domain the target touches (money, dates and time zones, authorization, state machines, external APIs, concurrency, text and encoding, pagination).
5. **Choose the test level per case.** Put each case at the cheapest level that can prove it: unit for pure logic, integration (request, model with DB, component with real children) when the behavior depends on wiring, end-to-end only for a critical user path. Follow the project's existing split between levels.
6. **Prioritize and trim.** Mark each case `must` (a branch with business impact, a bug fix regression, a public contract, a boundary that changes the result), `should` (likely failure modes), or `could` (low risk). An entry point that no in-repo caller uses (for example a wrapper like `invoke` when every caller calls `execute`) is `could` at most, and one case is enough. Decide duplicates yourself: drop a case you judge a duplicate, and when unsure, merge it and list the merge under the table instead of asking the user. Merge cases with the same input class and the same code path, even when two techniques produced them (a boundary case that is also a decision-table column is one case). A collapsed decision-table column is one case; do not add cases only to show that the collapsed conditions do not matter. Do not test framework or library behavior, private methods directly, or implementation details that a refactor would break without a behavior change.
7. **Present the case table** (format below) and wait for approval before writing specs. Answers to open questions alone are not approval: update the table with the answers and ask again. Exception: when the caller's contract says to write directly (for example `omo-implement` delegating without a user in the loop), skip the wait, write the specs, and include the case table in the result so the caller can review it. The table goes in the result, not in the spec file; in the spec, mark `oracle: code` cases with a one-line comment.
8. **Write the specs** in the detected style. Add cases to the existing spec file when one exists. Reuse existing factories, fixtures, shared examples, and helpers before adding new ones; add a new factory trait or helper only when no existing one fits. When an expected value depends on rounding or type conversion (decimal columns, money, time zones), write the input as a literal that fixes it exactly (a decimal as a string such as `"1.005"`, a time with an explicit zone), so the case does not depend on float representation.
9. **Run them.** Run only the new or changed spec files. For a bug fix or a behavior not yet implemented, confirm each new case fails for the expected reason before the fix, then passes after. For cases on existing correct behavior, confirm they pass, then break the behavior temporarily (or reason from the assertion) to confirm the case would catch it; a case that cannot fail is removed or rewritten. When the runner cannot run (dependencies not installed, no DB), keep the written specs, report the run and the failure check as unverified with the reason and the exact command to run, and do not mark either as done.
10. **Report** the case table with the result per case, the spec files changed, the run command and its result, and any case left unwritten with the reason.

## Case Table Format

```markdown
| ID | Level | Technique | Condition / input | Expected | Priority | Note |
|---|---|---|---|---|---|---|
| TC-01 | unit | boundary | quantity = 0 | validation error "must be greater than 0" | must | |
| TC-02 | unit | boundary | quantity = 1 | valid | must | |
| TC-03 | request | decision table | admin, archived record | 403 | must | oracle: code |
| TC-04 | unit | branch | API returns 503 | retried 3 times, then raises | should | |
```

The Technique column names the technique that produced the case; black-box and white-box names may appear in the same table.

Below the table, list:
- Detected style: framework, file location, grouping, setup, doubles, and helpers to reuse.
- Existing coverage that the new cases do not repeat.
- Merged cases: cases you merged because you were unsure whether they were duplicates, one line each.
- Open questions: behavior the code and the spec disagree on, or that neither defines. Ask these instead of guessing an expected value. Under a write-directly contract, return them to the caller in the result.

When the code disagrees with a stated spec, write the case with the spec's expected value, mark it `suspected bug` in the Note column, and add the disagreement to the open questions. This applies with or without a user in the loop.

## Hard Rules

- Do not change production code to make a test pass. When a case exposes a bug, report it with the failing case and stop for direction, unless the caller's task is the fix. Under a write-directly contract with no user in the loop, keep the case, mark it `suspected bug` in the result, and return to the caller instead of stopping.
- Do not invent expected values. Each expected value comes from a spec, an issue, a stated contract, or the current code (marked `oracle: code`).
- Do not weaken, skip, or delete existing tests.
- Do not add a new test library, matcher, or global setup without asking.
- Do not mock the unit under test. Mock only at boundaries the project already mocks (HTTP, time, external services), in the way it already does.
- Keep each case independent: no reliance on test order or on state left by another case.
- Do not claim a spec passes unless it ran in the current session.
