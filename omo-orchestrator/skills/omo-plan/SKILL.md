---
name: omo-plan
description: Create OMO-style executable plans with acceptance criteria, dependency matrix, QA scenarios, plan review, and verification commands.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, TodoWrite
user-invocable: true
---

# OMO Plan

Use this skill only when the user explicitly asks for a plan, planning, a work breakdown, or a plan before coding. Do not activate from a bare orchestration request, an agent-side routing decision, or reading this file.

Act as a planning consultant. Explore before planning, never implement product changes, and produce one decision-complete plan that another agent can execute without reinterpreting the goal. This is a content-only workflow. It creates no hooks, runtime automation, automatic execution, or automatic continuation.

## Planning Boundary

1. State that planning mode is active and that this workflow will not edit product code, dispatch implementation, or run implementation commands.
2. Treat requests to build, fix, or change something as a request to plan that work while this skill is active.
3. Start with read-only repository exploration. Use external research only when repository evidence cannot answer a material question.
4. Announce one intent verdict after grounding: `CLEAR` when the requested outcome is specific enough to plan, or `UNCLEAR` when the outcome itself needs practical defaults.
5. Show a visible draft before the approval gate. The draft must include the intent verdict, evidence, assumptions, decisions, open blockers, proposed scope, and the next planning action.
6. Do not present an executable final plan before the user explicitly approves the draft or approval brief.
7. Approval authorizes writing the final plan only. Plan approval never authorizes implementation, delegation of implementation, edits, or execution commands. A separate user-directed workflow starts execution.

## Intent And Decision Routing

1. For `CLEAR` intent, ask only questions that exploration cannot settle and that require an owner decision. An owner decision is irreversible, safety-critical, destructive, or a lasting product choice such as a public contract, data shape, external dependency, budget, compliance limit, or target capacity.
2. For `UNCLEAR` intent, research practical defaults, select the smallest defensible option, and announce each selected default with its rationale. Don't ask the user to make ordinary design decisions.
3. For an intent verdict that remains genuinely uncertain, treat it as `CLEAR` and ask one precise question rather than silently applying a default.
4. For every candidate question, first ask whether repository or external evidence can answer it. Then ask whether the stated goal supports a reversible default. Ask the user only when an owner decision remains.
5. Explore each open question only until the decision is supported. Stop when new searches repeat known evidence or cannot change the plan.
6. Record material discovered work in the draft. Add it to the proposed plan only if it is required for the requested outcome. Otherwise record it as an explicit observation or deferral with a reason.

## Draft And Approval Gate

1. Present one concise approval brief after exploration and before final-plan writing.
2. The brief must name the goal, non-goals, chosen defaults, owner decisions, proposed files or systems, dependency shape, QA approach, blockers, and the statement: `Approval writes the plan only. It does not authorize implementation.`
3. If a decision-changing question remains, ask that question before the brief and wait for the answer. Don't substitute an unapproved default for an owner decision.
4. After the user approves, write one final decision-complete plan. Do not reduce the requested scope unless the user requested the reduction.
5. If the user changes scope before approval, update and show the draft again. If scope changes after approval, return to the approval gate for the changed portion.

## Final Plan Requirements

- State the goal, constraints, assumptions, selected defaults, and explicit non-goals.
- Name exact files, symbols, or systems for every task. Use `all matching <symbol or path pattern>` only when the affected set is intentionally broad and explain how it is identified.
- Give each task one exact action and the expected result.
- Name each task's dependencies and the tasks it unblocks.
- Define measurable acceptance criteria for every task.
- Include an evidence target for every task, such as changed files, test output, diagnostics, command output, review result, screenshot path, or inspected content.
- Define how newly discovered work is recorded, assessed, scoped before dispatch when required, or explicitly deferred.
- Classify gaps as critical, minor, or ambiguous. Give each true blocker one precise question.
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

Use TDD-oriented sequencing when the codebase supports it: identify the failing behavioral check or validation target before editing, then record the passing result afterward. Missing, abstract, or unexecutable QA is a blocking plan-quality finding. Reject phrases such as `verify it works`, `check the page`, or unspecified manual testing.

## Bounded Plan Review

1. Review the draft for executability, goal alignment, scope control, dependencies, security-sensitive risks, and QA completeness before handoff.
2. Escalate hard, high-risk, ambiguous, security-sensitive, release-facing, or cross-system work to `omo-hyperplan` before the approval brief.
3. Use one independent read-only review or an explicit manual critique when a reviewer is unavailable. Keep review bounded to one initial pass and at most two materially different revisions.
4. A review finding needs evidence from a file, symbol, contract, test, command, or documented assumption. Keep verified non-issues separate from findings.
5. If a critical blocker survives the review budget, record the evidence and one exact question or next action. Do not claim the plan is ready.

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
   - TL;DR.
   - Context and constraints.
   - Objectives, assumptions, and non-goals.
   - File and symbol-level task list.
   - Parallel execution waves.
   - Dependency matrix.
   - Per-task acceptance criteria and QA scenarios.
   - Verification strategy.
   - Gap classification and one-question-per-blocker list.
   - Escalation decision: normal plan, hyperplan, security research, or release review.
   - Cross-context handoff checkpoint when applicable.
6. Explicit stop statement that implementation remains a separate, user-directed workflow.
