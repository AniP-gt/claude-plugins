# Measured Verification: Before And After Numbers

A change that is meant to move a quantity is verified with numbers measured before and after it, by one command, on one machine. Reading the code, or one run after the edit, does not show how much it moved. How to measure (a deterministic measure first, repeated runs, medians against the spread of the baseline runs, behavior held fixed, no gaming) is in `omo-ralph-loop` `references/iteration-guards.md`, Measured Goals rules 2, 3, and 5. This file says when a measurement is required, what to measure, and how to report it.

## 1. When It Applies

Required: the purpose or the claim of the change is a quantity (faster, cheaper, fewer tokens, fewer queries, smaller, less memory, a higher pass rate), or the user asks for numbers.

Guard: the purpose is something else, but the diff changes one of the following, and a command that yields the number already exists or is a single local command. Take one before/after measurement to show the change made it no worse.

- a SQL query or an index
- code that an existing benchmark covers
- the prompt, model, or tool settings of an LLM call in an application

Not required: when the purpose is not a quantity, wording, docs, renames, config values other than the guard items above, rule or skill prose, and any change that touches none of the above. The purpose decides: a skill or prompt edit made to cut its token count or cost is required. Do not report a proxy such as a line count or a test count just to have a number.

## 2. The Measure Row

Add one row per metric to the QA design (`real-surface-qa.md`, Design), next to the scenario it belongs to:

- Metric: what is counted or timed, and its unit.
- Command: the exact command, and how the number is read from its output.
- Baseline: the value on the unchanged code, and the revision it was taken on.
- Pass: a binary comparison with the baseline. For a required measurement, the after value beats the baseline by more than the spread of the baseline runs, or reaches the stated target. For a guard, the after value is not worse than the baseline by more than that spread.
- Role: primary, or guard with a tolerance. Use one primary metric per goal. A guard metric worse than its tolerance is a question for the user, never a silent accept. Fix the metrics before the baseline, and do not redefine them after seeing results.
- Runs: how many times each side runs. A deterministic count needs one run; a number that varies between runs follows Measured Goals rule 2.
- Conditions held equal: the machine, the input or dataset and its size, the configuration, and for an LLM measurement the model and the case set. When the change itself swaps the model, name the old and new model and hold the input and case set fixed.
- Cost: for a measurement that spends money (paid API calls), the number of calls and the estimated cost. When no approved plan showed that cost to the user, ask before running it. Prefer a free or offline count when one answers the question.

A target is asked for only where Measured Goals rule 1 already requires it (a Ralph loop whose goal is a quantity with a direction and no number). A single pass and a guard need no target question.

## 3. Baseline

Take the baseline with the approved command after the QA design is approved and before the first edit. Whoever runs the QA takes it: the main context before a Codex launch, `omo-implementer` as its first step otherwise.

- Measure it again even when the user or an issue reports a number.
- When the edit already happened, take the baseline from the base revision in a separate worktree on the same machine, then remove the worktree.
- When the base cannot be built or run, report "baseline unavailable" and make no improvement claim.

Running a measurement several times is sampling, not a retry. The ban on test retries (`omo-programming`) and the rule that re-running an unchanged command is not a new approach (`omo-implementer`) do not apply to it.

## 4. What To Measure

Use the repository's own benchmark, profiler, or counting command when it has one. Otherwise pick from this table. Each command was checked against its documentation or a local run on 2026-11-19; check the version in use before relying on one.

| Area | Numbers | Command |
|---|---|---|
| SQL, PostgreSQL | Plan node types, the planner's estimated `cost` and `rows`; with `ANALYZE` the actual time, rows, and loops per node, `Planning Time`, `Execution Time`, and buffer hits and reads | `EXPLAIN <statement>` for the estimate. `EXPLAIN (ANALYZE, BUFFERS) <statement>` for actual numbers; it executes the statement, so wrap a data-modifying one as `BEGIN; EXPLAIN ANALYZE ...; ROLLBACK;` |
| SQL, MySQL 8.0.18 or later | Estimated cost and rows next to actual time, rows, and loops; `query_cost` and `rows_examined_per_scan`; rows read by one statement | `EXPLAIN ANALYZE <statement>` (it runs the statement). `EXPLAIN FORMAT=JSON <statement>` for `query_cost`. `FLUSH STATUS`, then the statement, then `SHOW SESSION STATUS LIKE 'Handler_read%'` for rows read |
| SQL, SQLite | Whether each table is read by `SCAN` or by `SEARCH ... USING INDEX` | `EXPLAIN QUERY PLAN <statement>`. Its output format is meant for people and may change between releases; compare the plan shape, not the text |
| Queries per request or job | Number of SQL statements for one request or one job run, at two data sizes | The framework's query log or query counter around that request or job |
| Program speed | Time per operation, and a deterministic companion such as allocations or operation counts | The repository's benchmark first. Go: `go test -bench <regexp> -benchmem -count <n>` (`ns/op`, `B/op`, `allocs/op`), and `benchstat old.txt new.txt` to compare when it is installed. A command-line program: `hyperfine --warmup <n> --runs <n> '<old command>' '<new command>'` when it is installed. Node.js: time a fixed input with `performance.now()` from `node:perf_hooks`; profile with `node --cpu-prof` |
| Memory | Peak resident set size of the process | macOS: `/usr/bin/time -l <command>` (`maximum resident set size`, in bytes). Linux with GNU time: `/usr/bin/time -v <command>` (maximum resident set size, in kilobytes) |
| Size | Bytes of the built artifact | The project's build command, then `wc -c <file>` |
| LLM call | `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens` from `usage` in the API response; the two cache fields are counted in addition to `input_tokens` | Read `usage` from the responses of a fixed set of requests. To count a request without sending it: `POST /v1/messages/count_tokens`, which is free. Report tokens and cost separately: a cache read is billed at a fraction of the input price, so fewer input tokens and lower cost are different results |
| Agent, skill, or plugin behavior | Pass rate, score, and cost over a fixed set of cases with repeated runs | `claude plugin eval <plugin> --case <glob> --runs <n> --max-cost-usd <usd>`, then `aggregates.passRate`, `aggregates.score`, and `costUsd` in `aggregate-result.json`. For one headless session: `claude -p --output-format json` (`total_cost_usd`, `usage`). Read the transcripts as well as the score: a grader that sees only the final message can score a hook's follow-up question instead of the report |

## 5. Local Data And Production

- Measure in the local environment only (`real-surface-qa.md`, Target). Never run `EXPLAIN ANALYZE` against production: it executes the statement.
- Measure on the same database engine and major version as production. Numbers from another engine are not a measurement of this query.
- Without production-scale data, seed to a stated row count, refresh the table statistics, and report the row count next to the numbers. A plan on a small table can differ from the plan at production size, so also give the user a read-only plain `EXPLAIN` to run there as numbered steps, with the result that would confirm or refute the local finding, and report that part as unverified until they run it.

## 6. Report

```
| Metric | Command | Baseline | After | Change | Runs (spread) | Conditions |
```

- One row per metric: the primary metric first, guard metrics after it.
- The Command column holds the command or script path exactly as run, so another person can run it again. Naming only the timing method (a timer function, "measured with a benchmark") is not enough.
- An after value inside the spread of the baseline runs is "no measurable change", not an improvement.
- Put the table in the done report and in the PR body draft.
- When the quantity was not measured, write `Not measured: <reason>` in place of the table and list it as an unverified area (`SKILL.md` step 8). When only the user's environment can measure it, give numbered steps: build, baseline on the old code, the metric and how to read it, the conditions to hold equal. Do not state that it improved; `SKILL.md` Hard Rules allow a run time only with a measurement behind it.
