---
name: omo-tech-debt-audit
description: Read-only, file-cited tech debt audit across 9 dimensions with severity, effort estimates, and prioritized fixes, written to a TECH_DEBT_AUDIT.md report.
argument-hint: [scope]
allowed-tools: Read, Grep, Glob, Bash, Write, Task
user-invocable: true
---

# OMO Tech Debt Audit

Claude Code adaptation of oh-my-openagent `.agents/skills/tech-debt-audit`.

Use this skill for a codebase health check, tech debt audit, architecture review, code quality assessment, or cleanup planning. `[scope]` narrows the audit to a path or module; default is the whole repository.

## Hard Rules

- Read-only on source code. Do not edit, format, install, or delete anything.
- The only write is the report file. Before writing, confirm the output path with the user. Default: `TECH_DEBT_AUDIT.md` at the repo root. Do not overwrite an existing report without confirmation.
- Every concrete finding cites `path:line` (add `:col` when a tool reports it). No generic claims without evidence.
- Commands must be non-mutating. Skip anything that writes lockfiles, caches, or build output. Do not run networked or state-changing commands (for example dependency audits that fetch advisories) without asking.
- Adapt searches to the detected stack. The TypeScript/JavaScript patterns below are examples; translate them to the repo's languages.

## Tool Availability

Check once in Phase 0 and record the result in the report.

- Structural search: use `sg` (ast-grep) only if `command -v sg` succeeds. See the `omo-ast-grep` skill for pattern syntax. Otherwise fall back to Grep and state that structural checks were approximated.
- Type diagnostics and references: use LSP only if available in the session. Otherwise use the project's own type checker if it runs without side effects, or mark the metric `unmeasured`.
- Tests: run the project's test command only if it is read-only in effect and reasonably fast; otherwise inventory tests statically and mark runtime health `unmeasured`.

## Phase 0: Orient

1. Map the language stack with Glob on source extensions.
2. Read manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`, etc.) for dependencies and build tooling.
3. Churn: `git log --format= --name-only -200 | sort | uniq -c | sort -rn | head -30`.
4. Size: list files over 300 LOC (`wc -l` on source files, excluding vendored and generated paths).
5. Cross-reference high churn with large size to find hot zones.
6. Write a one-paragraph mental model: what the repo does, stack, module boundaries.

## Phase 1: Audit Across 9 Dimensions

For large codebases (roughly >50k LOC), split dimensions across parallel `omo-orchestrator:omo-researcher` agents via the Agent tool, sent in one message. Suggested lanes:

- Lane A: dimensions 1, 2
- Lane B: dimensions 3, 7
- Lane C: dimensions 4, 5, 6
- Lane D: dimensions 8, 9

Each prompt includes: the mental model, scope, tool availability, the dimension checklist below, and the requirement to return every finding as `ID, category, path:line, severity, effort hours, description, recommendation`. Researchers stay read-only. For smaller repos, run the dimensions directly with parallel tool calls. After one bounded follow-up, mark a stalled lane as `unmeasured` rather than blocking.

### 1. Architectural Decay

- Search: import graph (`sg -p "import { $$$ } from '$SRC'"`), large classes, `TODO|FIXME|HACK|XXX|WORKAROUND|TEMP` markers, `wc -l` on Phase 0 large files.
- Flag: files >500 LOC, functions >80 LOC or >4 nesting levels, classes >15 methods or >400 LOC, import cycles, dead exports (confirm with LSP references or exhaustive Grep), commented-out blocks of more than 3 lines.

### 2. Consistency Rot

- Search: HTTP client imports, direct `console.*` versus a logger, try/catch shapes, lint suppressions (`eslint-disable`, `noqa`, `# type: ignore`, `nolint`).
- Flag: 3+ ways of doing the same thing (HTTP, logging, validation, config), mixed naming conventions, multiple date/time libraries, mixed error response shapes.

### 3. Type and Contract Debt

- Search: `as any`, `: any`, `@ts-ignore`, `@ts-expect-error`, `as unknown`, or the stack's equivalents; LSP or type checker diagnostics if available.
- Flag: `any` on public APIs and exported types, untyped parameters, missing schema validation at API and IO boundaries, type errors grouped by file.

### 4. Test Debt

- Search: test file inventory, `.skip`/`.only`/`todo`/`xfail` markers, test run results if permitted.
- Flag: high-churn or critical-path files with no tests, skipped tests, tests asserting implementation details, slow tests (>1s) when measurable.

### 5. Dependency and Config Debt

- Search: manifests and lockfiles, env var reads (`process.env`, `os.environ`, `getenv`), `API_KEY|SECRET|PASSWORD|TOKEN` outside config.
- Flag: outdated major versions, duplicate libraries for the same job, env vars not documented in README or examples, hardcoded environment-specific values.

### 6. Performance and Resource Hygiene

- Search: `await` inside loops (`sg -p "for ($$$ of $$$) { $$$ await $$$ }"`), sequential async iteration, existing `Promise.all` patterns (good signal), listener or interval registration without matching cleanup.
- Flag: sequential awaits that could be parallel, N+1 queries, missing cleanup of listeners, intervals, and handles, needless serialization round trips.

### 7. Error Handling and Observability

- Search: catch blocks, empty catches, `.catch(() => {})`, error logging calls, thrown error types.
- Flag: empty catch blocks (worst offense), log-and-continue without recovery, inconsistent error shapes, missing structured logging on critical paths, swallowed promise errors.

### 8. Security Hygiene

- Search: credential-like names in source, SQL string construction, `innerHTML`/`dangerouslySetInnerHTML`, `eval`, `Function(`, string-based timers, CORS and auth middleware config.
- Flag: hardcoded secrets, string-concatenated SQL, unsafe HTML sinks, dynamic code execution, permissive CORS or auth. Hand confirmed exploitable issues to the `omo-security-research` skill instead of deep-diving here. Never copy secret values into the report; cite location only.

### 9. Documentation Drift

- Search: README claims versus code, doc comment coverage on public functions, marker density, README examples versus actual signatures, ADRs if present.
- Flag: documented features that do not exist, public functions with no doc comment, comments contradicting code, stale ADRs.

## Phase 2: Synthesize

1. Merge direct and lane findings; deduplicate issues reported by several dimensions.
2. Classify severity:
   - Critical: actively causing incorrect behavior, data loss, or security holes.
   - High: will cause problems under normal operation; blocks changes.
   - Medium: reduces maintainability; inconsistent; violates conventions.
   - Low: cosmetic; fix when nearby.
3. Estimate effort in hours per finding, conservatively.
4. Rank by impact/effort ratio.
5. Confirm the output path, then write the report.

## Report Contract

`TECH_DEBT_AUDIT.md` contains, in order:

1. Executive Summary: 3 to 5 sentences covering overall health, worst dimension, quick-win count.
2. Mental Model: one paragraph.
3. Tooling: what was available (`sg`, LSP, type checker, tests) and which metrics are `unmeasured`.
4. Findings Table: ID, Category, File:Line, Severity, Effort (h), Description, Recommendation.
5. Top 5 Priorities: ranked by impact/effort.
6. Quick Wins Checklist: items under 30 minutes each.
7. Looks Bad But Is Fine: at least 2 patterns that resemble debt but are intentional, with reasoning.
8. Open Questions: things the maintainer should clarify.

## Final Checks

- Every concrete finding has a `path:line` citation.
- No source files were modified; `git status` shows only the report.
- Unavailable tooling is reported as `unmeasured`, not guessed.
- Top 5 is ranked by impact/effort; quick wins are genuinely under 30 minutes.
- Reply to the user with the report path, finding counts by severity, and the top 3 priorities.
