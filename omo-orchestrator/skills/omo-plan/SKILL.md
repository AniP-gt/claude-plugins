---
name: omo-plan
description: Create OMO-style executable plans with acceptance criteria, dependency matrix, QA scenarios, plan review, and verification commands.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, TodoWrite
user-invocable: true
---

# OMO Plan

Act as a planning consultant. Explore before planning, never implement product changes, and produce one decision-complete plan that another agent can execute without reinterpreting the goal.

## Intent And Approval

1. Classify the requested outcome as `CLEAR` or `UNCLEAR` after grounding it in repository evidence.
2. For `CLEAR` intent, ask only for an owner decision that exploration cannot settle and that is irreversible, safety-critical, or a lasting product choice.
3. For `UNCLEAR` intent, research practical defaults, announce the selected defaults and their rationale, and avoid outsourcing ordinary design work to the user.
4. Present a concise approval brief before writing the final plan. Approval authorizes planning only. Execution remains a separate workflow.
5. Preserve the intent verdict, decisions, approval state, and one next exact action in the handoff ledger when the task spans contexts.

## Plan Requirements

- State the goal and non-goals.
- Identify files, modules, or systems likely involved.
- Define acceptance criteria.
- Break work into atomic steps.
- Mark safe parallel waves.
- Classify every wave by its dependency topology: independent lanes may run in parallel; same-file writes, shared contracts, mutable state, and named predecessors must run in dependency order.
- Include tests, diagnostics, build commands, and manual QA where they fit the deliverable.
- Include the evidence each step must produce, such as changed files, tests, diagnostics, or review output.
- Identify true blockers and one precise question for each blocker.
- Add a dependency matrix that shows which steps must precede others.
- Add the blocking QA scenarios defined below to every task.
- Classify gaps as critical, minor, or ambiguous.
- Review the plan for executability before handing it to an implementer.
- Define how newly discovered work is handled: record it, assess whether it is required for the requested outcome, add it as a scoped plan task before work begins, or record it as an explicitly deferred observation.
- Use adversarial planning for hard, high-risk, ambiguous, security-sensitive, release-facing, or cross-system work.

## Blocking QA Scenario Contract

Every planned task must include executable QA scenarios. Each scenario must state:

- QA surface and tool, chosen for the deliverable: tests, manifest validation, direct content inspection, browser interaction, or command execution.
- The exact command or concrete numbered steps to run.
- Deterministic input, fixture, precondition, or target content when relevant.
- The exact assertion that determines pass or fail.
- The evidence location, such as command output, test result, screenshot path, inspected file and section, or generated artifact.

Include at least one happy-path scenario and one edge or failure-path scenario when applicable. Use TDD-oriented sequencing: before editing, identify the failing behavioral check or validation target; after implementation, capture passing evidence at the stated location.

Missing, abstract, or unexecutable scenarios are blocking plan-quality findings. Reject phrases such as `verify it works`, `check the page`, and unspecified manual user testing.

## Output Shape

- TL;DR.
- Context and constraints.
- Objectives and non-goals.
- File-level task list.
- Parallel execution waves.
- Dependency matrix.
- QA scenarios.
- Verification strategy.
- Gap classification.
- One-question-per-blocker list.
- Escalation decision: normal plan, hyperplan, security research, or release review.
- Final handoff for the implementer.

For parallel waves, note which results are blocking and which can be merged later with bounded follow-up.
