# Verify Commands, Oracle Consult, Verify in Action

## Phase 3d: Verify commands (after every fix)

Dispatch to a sub-agent; require the exact commands and their output. Prefer the project's own scripts (`package.json`, `Makefile`, `bin/`) over these defaults.

| Stack | Commands |
|---|---|
| Ruby / Rails | `bundle exec rubocop {files}` / `bundle exec rspec {specs}` |
| TypeScript | `npx --no-install tsc --noEmit` / `npm run lint` (project-local binaries only; never fetch a package) |
| Vue | `npm run lint` / `npx --no-install tsc --noEmit` when TypeScript |
| Rust | `cargo check` / `cargo test` / `cargo clippy` |
| Go | `go build ./...` / `go test ./...` / `go vet ./...` |
| Swift | `swift build` / `swift test` |

Also run the SPEC Done when commands (including the coverage command when tests were written). `npx` here means the repository's already-installed binary; if it is not installed locally, record the check as unavailable instead of downloading it.

A failing check becomes an `AUTO_FIX` item for the next iteration. An unavailable check is recorded as unverified, never as passed.

## Phase 3f: Oracle consult (inner-loop stuck detection)

Trigger (either):

- The same issue (same file and defect mechanism, or the same missing evidence) appears in synthesis across 2+ consecutive iterations.
- `iteration_count >= 5` with blocking items remaining.

```
Agent(
  subagent_type="omo-orchestrator:omo-oracle",
  description="Phase 3f inner-loop stuck consult",
  prompt="""
  The following issue has been flagged in 2 or more consecutive review iterations
  (or the 5-iteration budget ran out with it open). Explain the root cause and
  recommend an alternative approach.

  ## Recurring issue
  {quoted from synthesis.md}

  ## Synthesis excerpts
  {current and previous iteration}

  ## Diff since cycle start
  {git diff {CYCLE_START_SHA}}
  """
)
```

| Oracle response | Action |
|---|---|
| Concrete alternative approach | Update SPEC, append the directive to the ledger, restart Phase 2 with a fresh `omo-implementer` |
| Business logic decision needed | `ASK_USER` with the oracle's analysis |
| Already correct, review is wrong | Record `ORACLE_OVERRIDE` in synthesis and the ledger, proceed to Phase 3.5 |

## Phase 3.5: Verify in Action

After the review loop passes, verify real behavior with a fresh agent that did not implement the change. This is behavior testing, not code review.

```
Agent(
  subagent_type="omo-orchestrator:omo-reviewer",
  description="Phase 3.5 verify in action",
  prompt="""
  You are a QA verifier. Exercise the implemented behavior on its real surface. Do not
  edit product files. Run commands, requests, and sessions; record what you observe.

  Implementation: {summary}
  TASK_ID: {TASK_ID}
  Changed files: {git diff --name-only {CYCLE_START_SHA}}
  Surface: {one of: HTTP API / CLI / TUI / browser UI / library / job or batch / data}
  Endpoints or entry points (optional): {list}
  Done when: {from SPEC}

  ## Required process
  1. Scenario brainstorm: at least 10 one-line scenarios with expected behavior,
     covering happy paths, boundaries (empty, max length, zero, negative, special
     characters), error paths (invalid input, network failure, permission, timeout),
     regressions on shared code paths, and state transitions (reversed order, rapid
     repeats, concurrency).
  2. Expansion: add 3+ from "what would a careless or malicious user do?" and
     environment conditions (disk full, slow network, expired token). Prioritize
     P0 (must pass) / P1 (should pass) / P2 (nice to pass).
  3. Task list: turn scenarios into structured tests (name, steps, expected, priority).
  4. Execute P0 first: run, record actual, compare, PASS/FAIL, collect evidence on
     FAIL. If the application does not start, FAIL immediately.
  5. Aggregate and report.

  Clean up every process, port, session, or temp dir you start and list receipts.

  ## Output format
  <verdict>PASS | FAIL | SKIP</verdict>
  <skip_reason>only for SKIP: why no real surface can be exercised</skip_reason>
  <confidence>HIGH | MEDIUM | LOW</confidence>
  <scenario_coverage>
    Total: N; P0: X tested, Y passed; P1: X tested, Y passed; P2: X tested, Y passed
  </scenario_coverage>
  <test_results>
    - [PASS/FAIL] name (priority): steps, expected, actual, evidence for FAIL
  </test_results>
  <blocking_issues>P0/P1 failures only; empty when none</blocking_issues>
  <cleanup>receipts</cleanup>
  """
)
```

When `IS_FRONTEND=true`, also run the `omo-visual-qa` skill on the affected pages and treat its `REQUEST_CHANGES` as FAIL and its `INCONCLUSIVE` as missing evidence.

| Result | Next action |
|---|---|
| PASS | Phase 4 |
| FAIL | `omo-implementer` fixes the blocking issues, then back to Phase 3 (max 3 returns) |
| SKIP | Record the reason in the Phase 4 report and continue; Phase 6 `omo-review-work` will treat uncovered rows as missing evidence |

Save the verbatim result to `{WORK_DIR}/verify_in_action_cycle{OUTER_CYCLE}.md`; Phase 6 passes it to `omo-review-work`.
