---
name: omo-plan
description: Create OMO-style executable plans or task files with acceptance criteria, dependency matrix, QA scenarios, and plan review. Use only when the user explicitly asks for a plan or work breakdown.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Write, Task, TodoWrite, AskUserQuestion
user-invocable: true
---

# OMO Plan

Use only on an explicit user request for a plan.

Act as a planning consultant. Use `omo-plan-consultant` for read-only intent and gap analysis when available, explore before planning, never implement product changes, and produce one decision-complete plan that another agent can execute without reinterpreting the goal. This is a content-only workflow. It creates no hooks, runtime automation, automatic execution, or automatic continuation.

## Planning Boundary

1. State that planning mode is active and that this workflow will not edit product code, dispatch implementation, or run implementation commands.
2. Treat requests to build, fix, or change something as a request to plan that work while this skill is active.
3. Start with read-only repository exploration. Use external research only when repository evidence cannot answer a material question.
4. Announce one intent verdict after grounding: `CLEAR` when the requested outcome is specific enough to plan, or `UNCLEAR` when the outcome itself needs practical defaults.
5. Name affected users, state their concrete `IS-*` ideal-state rows, and record each current shortfall as a `GAP-*` row before questions or the approval brief.
6. Show a visible draft before the approval gate. The draft must include the intent verdict, evidence, assumptions, decisions, open blockers, affected users, `IS-*` rows, `GAP-*` rows, proposed scope, and the next planning action.
7. Do not present an executable final plan before the user explicitly approves the draft or approval brief.
8. Approval authorizes writing the final plan only. Plan approval never authorizes implementation, delegation of implementation, edits, or execution commands. A separate user-directed workflow starts execution.

## Intent And Decision Routing

1. For `CLEAR` intent, ask only questions that exploration cannot settle and that require an owner decision. An owner decision is irreversible, safety-critical, destructive, or a lasting product choice such as a public contract, data shape, external dependency, budget, compliance limit, or target capacity.
2. For `UNCLEAR` intent, research practical defaults, select the smallest defensible option, and announce each selected default with its rationale. Don't ask the user to make ordinary design decisions.
3. For an intent verdict that remains genuinely uncertain, treat it as `CLEAR` and ask one precise question rather than silently applying a default.
4. For every candidate question, first ask whether repository or external evidence can answer it. Then ask whether the stated goal supports a reversible default. Ask the user only when an owner decision remains.
5. Explore each open question only until the decision is supported. Stop when new searches repeat known evidence or cannot change the plan.
6. Record material discovered work in the draft. Add it to the proposed plan only if it is required for the requested outcome. Otherwise record it as an explicit observation or deferral with a reason.
7. For build or refactor work, inspect the test framework, config, and nearby tests. Decide each task's test strategy by change scale: test-first for tasks that add or change branching, calculations, state transitions, data writes, parsing or validation, a public contract, or a bug fix; no new tests for wording (including only the text of an existing message), docs, renames, config values, or wiring that adds no branch. Exception: a rename or text change needs a test only when an in-repo consumer matches on the old name or text (a lookup by string, a caller comparing an error message); an outside consumer that could not be verified is reported as unverified, not a reason to add a test. When a task needs tests but the touched area has no test convention, how to test it is an owner decision.
8. When the plan adds, upgrades, or changes usage of a library, fetch version-applicable docs (Context7 when available, otherwise `omo-librarian`) and cite them in task references.
9. Before the approval brief, confirm clearance: objective defined, scope IN and OUT set, no critical ambiguity, approach decided, test strategy known, no blocking question outstanding. If any item fails, ask that one question. End every interview turn with a question or the brief, never a passive summary or `let me know`.

## Draft And Approval Gate

1. Present one concise approval brief after exploration and before final-plan writing.
2. The brief must name the goal, non-goals, chosen defaults, owner decisions, proposed files or systems, dependency shape, QA approach, blockers, and the statement: `Approval writes the plan only. It does not authorize implementation.`
3. If a decision-changing question remains, ask that question before the brief and wait for the answer. Don't substitute an unapproved default for an owner decision.
4. After the brief, request approval even when no owner question remains, unless the user has already explicitly authorized this approach and scope. Use Claude Code's `AskUserQuestion` when available, with a clear approval question and the recommended option first. Otherwise ask in chat and state that the question tool is unavailable. Use only parameters exposed by the current tool; do not copy another runtime's `required` or wait flags. A timed-out, dismissed, or unavailable answer is not approval, even if a tool advises proceeding on best judgment. Keep the visible draft's state `awaiting-approval`, report the pending decision, and end the turn without a final executable plan. This pending-status response replaces the usual question-or-brief ending on an unanswered gate. Optional reversible defaults do not replace approval. Honor explicit authorization already given for this scope; do not ask for the same permission again. An initial request to make a plan alone is not approval of an unseen approach.
5. After the user approves, return one final decision-complete plan in the current response. Write it to `.claude/omo/plans/<task-slug>.md` only when the user requests a plan file, then state that path. When the user asks for a task file for one already-researched task, use the layout and path in `references/task-file.md` instead. Do not reduce the requested scope unless the user requested the reduction.
6. If the user changes scope before approval, update and show the draft again. If scope changes after approval, return to the approval gate for the changed portion.

## Final Plan Requirements

- State the goal, constraints, assumptions, selected defaults, and explicit non-goals.
- Open the scope with affected users, how they use the result, concrete `IS-*` ideal-state rows, and `GAP-*` rows before must-have and must-not-have boundaries.
- Name exact files, symbols, or systems for every task. Use `all matching <symbol or path pattern>` only when the affected set is intentionally broad and explain how it is identified.
- Give each task one exact action and the expected result.
- Name each task's dependencies and the tasks it unblocks.
- Define measurable acceptance criteria for every task.
- Include an evidence target for every task, such as changed files, test output, diagnostics, command output, review result, screenshot path, or inspected content.
- Map every `IS-*` row to at least one delivering task, proving QA scenario, and evidence location. Close every `GAP-*` row with a task. Do not leave an ideal state unproven or a gap open.
- Define how newly discovered work is recorded, assessed, scoped before dispatch when required, or explicitly deferred.
- Classify gaps as critical, minor, or ambiguous. Give each true blocker one precise question. Fix minor gaps and list them as auto-resolved; apply a default to ambiguous gaps and list it as a default the user can override.
- Record `RISK_LEVEL` and its reason in the TL;DR, plus the applicable risk notes, per `references/rigorous-review.md`.
- Spec check: list the cases the request leaves undefined (empty, boundary, duplicate, repeated or concurrent use, partial failure, each permission level, data that already exists) and contradictions between its sources, each with the chosen default or one owner question.
- Exhaustive check: when the spec involves concurrent or ordered access to shared state, permission rules across roles and resource states, or interacting numeric constraints, add a task that checks every case within stated bounds (model check, exhaustive table test, or solver search) and turns counterexamples into regression tests, per `references/exhaustive-checks.md`. Do not add one for simple parts.
- For work that modifies existing code, include a risk map: each modified unit with its visible callers, its hidden reach (indirect references, queued or scheduled work, persisted data, consumers outside the repository, environment settings, implicit contracts) marked found, none, or could not verify, the guardrail that covers it, and its business impact. Every row with impact and no guardrail gets a task or QA step; every could-not-verify row is a listed unknown.
- Keep one plan; never split it. One task is one concern touching one to three files; split a task that touches four or more. Implementation and its tests are one task.
- End with the F1 to F4 final verification wave from `references/rigorous-review.md`.
- Include a verification strategy, review gate, and final handoff checkpoint.

## Dependency-Aware Waves

1. Group only genuinely independent tasks into parallel waves and state why they are independent.
2. Serialize same-file writes, shared contracts, mutable state, and named predecessors.
3. Treat a task that changes a contract as a predecessor of every consumer, test, document, migration, or validation task that depends on that contract.
4. Include a dependency matrix with each task, its predecessors, its blocked successors, and its wave.
5. Mark which results are required before the next wave and which independent results can merge later through one bounded follow-up.

## Per-Task QA Contract

Every task must include executable QA. Each task row must state:

- Exact file, symbol, or system.
- Exact action.
- Dependencies and expected result.
- Acceptance criteria.
- QA surface and tool.
- Exact command or concrete numbered steps.
- Deterministic input, fixture, precondition, or target content when relevant.
- One happy-path assertion.
- One failure-path or edge-case assertion when applicable.
- Evidence location.

Sequence by test necessity: a task that needs tests (see Intent And Decision Routing step 7) names the failing test to write first and the passing result to record afterward; a task that does not names the diagnostic or real-surface check instead. Missing, abstract, or unexecutable QA is a blocking plan-quality finding. Reject phrases such as `verify it works`, `check the page`, or unspecified manual testing.

## Bounded Plan Review

1. Review the draft with `omo-plan-reviewer` when available. It checks references, task startability, executable QA, affected-user coverage, `IS-*` task and QA mapping, `GAP-*` closure, and whether the approach reaches the ideal state.
2. Escalate hard, high-risk, ambiguous, security-sensitive, release-facing, or cross-system work to `omo-hyperplan` before the approval brief.
3. Use one independent read-only critique when `omo-plan-reviewer` is unavailable. Keep plan review bounded to one initial pass and at most two materially different revisions. `omo-plan-reviewer` returns `OKAY` or `REJECT`; reserve `omo-reviewer` and its `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE` lifecycle for implementation and PR-style review. The rigorous review lanes are the one exception, and they return lane findings instead of a lifecycle verdict.
4. For `RISK_LEVEL` `critical` or `high`, or when the user asks for a thorough review, replace step 1 with the six-lane rigorous review in `references/rigorous-review.md`. It keeps the same budget and adds convergence rules and a loop history table to the approval brief.
5. A review finding needs evidence from a file, symbol, contract, test, command, or documented assumption. Keep verified non-issues separate from findings.
6. If a critical blocker survives the review budget, record the evidence and one exact question or next action. Do not claim the plan is ready.

## Cross-Context Handoff

When planning crosses a context, operator, or pause, use `omo-handoff` to maintain the append-only ledger at `.claude/omo/handoffs/<task-slug>.md`. Do not claim the record is created or resumed automatically.

Before handoff, ensure the latest checkpoint includes:

- Current planning state and approval state.
- Source request, intent verdict, scope, non-goals, and selected defaults.
- Evidence and unresolved blockers.
- Dependency status and review state.
- The final-plan path or visible draft reference.
- One next exact action, written as a concrete command, review, decision, or planning step.

The handoff entry must follow the `omo-handoff` phase-entry contract. Never rewrite earlier ledger entries. Correct prior information with a later append-only entry.

## Output Shape

1. Planning-mode boundary and intent verdict.
2. Exploration evidence and visible draft.
3. Owner questions, if any, or announced defaults.
4. Approval brief and approval state.
5. Final plan after explicit approval only:
   - Returned in the current response, with `.claude/omo/plans/<task-slug>.md` named only when a requested plan file was written.
   - For a requested task file, the `references/task-file.md` sections replace the remaining items; acceptance criteria and exact QA commands stay mandatory.
   - TL;DR.
   - Context and constraints.
   - Objectives, assumptions, and non-goals.
   - File and symbol-level task list.
   - Parallel execution waves.
   - Dependency matrix.
   - Affected users, `IS-*` ideal states, `GAP-*` rows, task closure, and per-task acceptance criteria and QA scenarios.
   - `RISK_LEVEL`, risk notes, spec check, exhaustive-check decision (which parts get one and why the rest do not), risk map for modified code, verification strategy, and the F1 to F4 final verification wave.
   - Gap classification with auto-resolved gaps, applied defaults, and one question per blocker.
   - Plan review result: iterations, verdict, and remaining issues.
   - Escalation decision: normal plan, hyperplan, security research, or release review.
   - Cross-context handoff checkpoint when applicable.
6. Explicit stop statement that implementation remains a separate, user-directed workflow. Name the options the user may start: `omo-ulw-execute <plan-path>` to run the waves, or `omo-review-loop <plan-path>` for implementation with a review-fix loop (recommended when unsure). Both read a plan file, so offer to write one when none was requested.
