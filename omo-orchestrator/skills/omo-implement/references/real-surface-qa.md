# Real-Surface QA: Design, Review, Run

Every change gets at least one real-surface check. The diff sets how wide the check is, not whether it happens. Only a diff with no executable surface at all (docs or comments only) may use an artifact check instead (the rendered page, the loaded skill, the parsed config); name it in the design.

## 1. Design

The controller writes the QA design before any edit, from the plan, the risk map, and the test decision. One row per scenario:

- Priority: P0 (must pass before done) or P1.
- Behavior: which changed behavior or risk-map row it proves.
- Surface: HTTP API, browser UI, CLI, TUI, library, job, or data artifact.
- Tool: picked by the table below; must exist in this environment.
- Target: the local environment only (`localhost`, a local container, a local worker). Never production, staging, or a shared environment, and never a real external send (mail, chat, payment) unless the user asks.
- Setup: how the target starts (server command, seed data, env vars) and how it is stopped.
- Steps: the exact commands or browser actions.
- Pass: a binary observable (status code and body field, visible text, exit code, DB row, log line).
- Evidence: where the output, screenshot, or transcript is saved.

Cover each changed behavior with at least one scenario, add a regression scenario for unchanged neighboring behavior that has business impact, and add the failure path the change touches (invalid input, permission, timeout). Keep the count proportional: a one-line fix may need two scenarios, a new endpoint more.

An approved `omo-plan` already holds QA rows for its tasks. Reuse them as the design: fill in only the fields above that they lack (usually Priority, Target, Setup, and the regression row), and send only those additions through step 2.

## 2. Review

Dispatch `omo-orchestrator:omo-reviewer` (`LOAD_SKILLS: none`) as a QA design review, not a code review: tell it this is mid-work analysis of a design before any edit, so no final-tree QA evidence exists or is required, and findings target design rows only. Pass the request, the planned diff or changed files, the risk map, and the design, and ask for `APPROVE` or `REQUEST_CHANGES` with the missing or wrong rows, checking:

- Every changed behavior and every risk-map row with business impact and no guardrail has a scenario, or a stated reason none can exist.
- The surface matches what a user or caller actually touches; a test that calls the code inline is not a real surface.
- The tool exists here, the target is local, and setup and cleanup are concrete.
- Each pass condition is binary and each scenario names its evidence path.

On `REQUEST_CHANGES` or `INCONCLUSIVE`, redesign only the flagged rows and review again. After 3 rounds without `APPROVE`, stop and ask the user with the open rows. Do not run QA on a design that has not received `APPROVE`. Attach the approved design to the `omo-implementer` brief; the design review does not use a Ralph iteration.

## 3. Run

Implementation, tests, and QA are one continuous flow: after the edit, run diagnostics and tests, then the approved scenarios, without returning to the user or controller in between. Stop early only for a blocker (`SKILL.md` step 8).

- Run P0 scenarios first; record the actual result next to the pass condition.
- On a failing scenario, fix the code and re-run the tests and the affected scenarios.
- When the final diff touches a surface or behavior the design does not cover, run what the design covers, then return the uncovered rows to the controller for step 2 instead of running unreviewed scenarios.
- Stop every server, browser tab, session, and container you started, and list them in the report.

## Tool Selection

| Surface | Tool |
|---|---|
| HTTP API | `curl` against the local server. Record the full command, status code, the headers that matter, and the body (`curl -sS -i` or `-w '%{http_code}'`). Start the local server first when it is not running. A browser UI change that calls a changed endpoint also gets a `curl` scenario for that endpoint. |
| Browser UI, inside Orca | When `ORCA_WORKTREE_ID` is set, resolve the Orca executable as the `orca-cli` skill says (`ORCA_CLI_COMMAND`, `orca-dev`, `orca-ide`, else `orca`) and check `<orca> status --json`. When it succeeds, use Orca's embedded browser: load `<orca> skills get orca-cli --reference browser` first, then `goto`, `snapshot`, `click`/`fill`, `wait`, `screenshot`, `console`, and `network` with `--json`. On `runtime_access_denied`, re-run outside the sandbox; do not run `orca open` or restart Orca. |
| Browser UI, otherwise | When the `playwright:playwright-step` skill is installed (it appears in the skill list), load it and drive the page with it (navigate, snapshot, click, screenshot, console). |
| Browser UI, neither | Another browser automation tool already available here; if none exists, report the browser scenarios as unverified (`SKILL.md` step 8). |
| CLI | The real command with real arguments; record stdout, stderr, and exit code. |
| TUI | A real session in tmux (or an Orca terminal inside Orca); record the transcript. |
| Library | A small driver that imports the public API and calls it as a caller would. |
| Job | A real worker process with its real queue and lock store (`SKILL.md` step 7). |

For a browser UI change, also run `omo-visual-qa` with the same tool.
