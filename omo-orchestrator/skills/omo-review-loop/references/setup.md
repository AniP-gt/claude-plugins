# Setup: Phase -1, 0, 1, 2

## Phase -1: Load Existing Documents

Before anything else, resolve `REPO_ROOT`, `LAYOUT`, and `TASK_ID` (see SKILL.md "Paths"), then look for existing work documents.

Scan, in order:

- `docs/issues/{number}/` or `docs/issues/{name}/` (numeric or named issue)
- `.claude/omo/plans/<task-slug>.md` (written by `omo-plan`)
- `.claude/omo/reviews/{TASK_ID}/` (a previous run of this skill)
- `.claude/omo/handoffs/{TASK_ID}.md` (ledger)

Files of interest: `spec.md`, `task.md`, `plan.md`, `metis-analysis.md` or other pre-planning analysis, and any `*.md` describing the implementation.

| Situation | Action |
|---|---|
| Documents found | Read them. Extract issue number, goal, scope, directives, acceptance criteria. Use them as Phase 2 input and skip Phase 1 when the plan is complete. |
| Ledger found | Read it in full and run SKILL.md "Resume and Stop-Continuation" first. Resume from its latest next exact action (`omo-handoff`) only when that check finds no block or the user confirmed the plan. |
| Nothing found | Proceed Phase 0 -> Phase 1 -> Phase 2. |

Create the ledger if missing (`omo-handoff` template) and append a kickoff entry with the resolved paths.

## Phase 0: Detection

### Code search (optional)

When a semantic code search tool is available (for example the `compass` plugin), query it with the task description and put the top file paths into `SPEC` References. Otherwise dispatch `omo-orchestrator:omo-researcher` for entry points. Skip silently when neither helps.

### Stack

```
Gemfile                      -> ruby (+ rails if config/routes.rb)
package.json                 -> node (+ vue if *.vue, + typescript if tsconfig.json)
Cargo.toml                   -> rust
go.mod                       -> go
*.xcodeproj / Package.swift  -> swift
diff or task touches .github/workflows/*.yml, action.yml, Dockerfile*,
  docker-compose*, or CI config -> + ci (IS_CI_CHANGE=true)
```

Store as `DETECTED_STACK`. `IS_CI_CHANGE=true` makes the security lane apply its CI / GitHub Actions / IaC checklist. A CI or tooling change that is the task's deliverable is not out-of-scope harness noise.

### Frontend flag

`IS_FRONTEND=true` when the task mentions UI, UX, design, component, layout, style, CSS, visual, page, or screen; or target files are `*.vue`, `*.tsx`, `*.jsx`, `*.css`, `*.scss`, `*.html`, `components/`, `pages/`, `views/`; or the stack includes a frontend framework.

### GOAL / CONSTRAINTS / BACKGROUND

Extract from the docs, issue, and task description:

- `GOAL`: what the task achieves; the yardstick for over- and under-implementation.
- `CONSTRAINTS`: stack limits, compatibility, performance, design constraints.
- `BACKGROUND`: why the change is needed, issue number, related context.

If one is missing and matters, ask one question (no checklists).

### Risk classification

| Risk | Area | Review policy |
|---|---|---|
| critical | payment/billing, authn/authz, migrations, personal data | scrutinize everything |
| high | transactions, external APIs, batch jobs, data integrity, query/index changes | safety and robustness first |
| medium | controllers, services, forms, query objects | standard |
| low | views, serializers, config, tests, docs | suggestion-focused |

`db/migrate/`, SQL, `add_index`, explicit transactions, bulk data processing, or lock queries force `RISK_LEVEL=high` or above and require `db-checklist.md`. Robustness review must then also verify batch/import fault isolation: one record or auxiliary-step failure must not skip later required steps after earlier writes committed.

Store `RISK_LEVEL` and `RISK_REASON`.

### External Library Contract Check

Mandatory whenever changed logic imports, calls, configures, extends, or relies on a third-party library's API, defaults, lifecycle, errors, cleanup, retry, caching, rendering, serialization, or platform behavior. A dependency version change or API syntax change is not required to trigger it.

1. Resolve the exact installed version from the lockfile or package manager output, not a loose manifest constraint.
2. Fetch version-applicable docs: Context7 MCP tools (`resolve-library-id`, `query-docs`) when available, otherwise dispatch `omo-orchestrator:omo-librarian`.
3. Confirm which version the docs cover. Verify the installed-version contract and check the latest migration/release notes for deprecations and breaking changes.
4. Fallback order when Context7 lacks version-applicable material: versioned official docs, official release notes, installed package types/source. Record the fallback and any limitation.
5. Memory or training knowledge alone is not evidence.

Record in `SPEC`:

```
External Library Contract Check:
- Library: <name>
- Resolved version: <exact version>
- Source: <Context7 ID and/or official URL/source path>
- Version applicability: <why the source applies to the resolved version>
- Verified contract: <API/default/deprecation/breaking-change findings>
- Runtime evidence: <installed source/help/execution, or N/A>
- Limitations: <none or unresolved item>
```

No third-party dependency in changed logic: `External Library Contract Check: N/A - <reason>`.

## Phase 1: Plan

Skip when Phase -1 found a written plan, task, or spec that covers Goal, files, and Done when.

Otherwise dispatch `omo-orchestrator:omo-planner` (read-only) with the task, GOAL/CONSTRAINTS, stack, and risk. For `high` or `critical` risk, run `omo-orchestrator:omo-plan-reviewer` once on the result; a `REJECT` goes back to the planner. The coordinator writes the approved plan into `SPEC`. When the user explicitly asked for a plan first, use the `omo-plan` skill and its approval gate instead.

## Phase 2: Implement

### 2a-pre. Base branch state (required)

```bash
git branch --show-current
git log --oneline {BASE_BRANCH}..HEAD
git diff {BASE_BRANCH}...HEAD -- {FILES_TO_MODIFY}
git show {BASE_BRANCH}:{FILE}      # per target file as needed
git status --porcelain             # record pre-existing dirty files
```

`BASE_BRANCH` comes from the task or docs; default is the repository's default branch. Do not start implementation without this check. Create a new branch (`git checkout -b {NEW_BRANCH} {BASE_BRANCH}`) only when the user or task asks for one, and never switch branches over a dirty tree.

### 2a-pre2. Validation source of truth and error message (when adding or changing validation)

Triggers: a new or changed existence/presence check against a master or reference data source (DB table, cached master data, any authoritative data set), or a validation whose user-facing message is not dictated by an unambiguous precedent in the same class definition.

Exclusion: a plain type/range/presence check with no data lookup, with a precedent for both check and message in the exact class being edited (not a base class, concern, or sibling file). Record `2a-pre2 not applicable: <reason>` in `SPEC`. When in doubt, do not apply the exclusion.

Resolve both and record in `SPEC` Implementation details:

- (a) Source of truth: read the downstream consumers of the validated value (jobs, services, queries that join or filter on a table). Search sibling forms/services in other files for the same or similar validation and use it as precedent unless the task says otherwise (cite its path). Confirm the intended population (any master record, or only records reachable in the current scope). If table, precedent, and population cannot all be identified from code, this is `ASK_USER`.
- (b) Error message: internal error-code key versus user-facing sentence; how the consumer renders it (raw string in an alert or form field makes its wording a spec); what it must and must not include. If unspecified and no precedent exists, this is `ASK_USER`.

Batch (a) and (b) into one `ASK_USER` turn when both are unresolved.

### 2a-pre3. Runtime-behavior verification (when relying on how a library or CLI behaves)

Triggers when correctness depends on runtime behavior ("falls back to X", "flag defaults to Y", "raises instead of returning nil", "`--limit N` is accepted"). Docs are not sufficient. Verify by reading the installed source (`bundle show <gem>`, `gem which <lib>`, the resolved `node_modules` path; cite `file:line`) or by a minimal run or `<cli> --help` with captured output. Record it in `SPEC` as `External behavior verified: <behavior> (<evidence>)`. If it cannot be verified, `ASK_USER` or choose the branch that does not depend on it.

### 2a. Write SPEC

Required sections: Goal / Stack / Issue or TASK_ID / Base branch / Files to modify / Constraints / Implementation details / Test requirements / Done when / External Library Contract Check.

- Constraints must include:
  - "Change only the specified locations. Do not reformat nearby code (for example auto-applied Prettier)."
  - "Avoid new circular references (a callback referencing the object being constructed). Pass needed objects as callback arguments. ActiveRecord associations are not circular references here. Follow `.claude/rules/circular-reference.md` if it exists. Follow an existing shared API's self-reference shape rather than changing the API."
  - Task-specific constraints.
- Implementation details include the 2a-pre2 and 2a-pre3 findings when they apply.
- Test requirements (when tests are written): 100% coverage of changed and added code (statements, branches, functions, lines) and test cases per major branch (happy, error, edge).
- Done when (when tests are written): the exact coverage command and "all tests pass".

### 2b. Delegate

```
Agent(
  subagent_type="omo-orchestrator:omo-implementer",
  description="Implement {TASK_ID} cycle {OUTER_CYCLE}",
  prompt="""
  Implement SPEC. Finish when every Done when condition is satisfied and verified.
  Ledger: {LEDGER} (append entries per omo-handoff).
  ## SPEC
  {full SPEC}
  ## Fix directives (outer cycle >= 2 only)
  {blocking findings and oracle directives from CYCLE_LOG}
  Make additional fixes only on top of the existing implementation. Do not rewrite it.
  """
)
```

When `IS_FRONTEND=true`, add an aesthetic direction section to `SPEC` (purpose, tone, constraints, the one thing users remember) and plan an `omo-visual-qa` check for Phase 3.5. If the user has a dedicated frontend design skill listed, it may drive the design direction; implementation still goes to `omo-implementer`.

### 2c. Post-implementation check

Dispatch to a sub-agent and require the output:

```bash
git diff --name-only {CYCLE_START_SHA}
git ls-files --others --exclude-standard
git grep -nE '^(<{7}|={7}|>{7})( |$)' && echo "CONFLICT MARKERS FOUND" || echo clean
git diff {BASE_BRANCH}...HEAD -- {FILES_TO_MODIFY}
```

Resolve conflict markers or out-of-scope changes before Phase 3.
