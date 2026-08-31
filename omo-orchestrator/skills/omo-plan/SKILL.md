---
name: omo-plan
description: Create OMO-style executable plans with acceptance criteria, dependency matrix, QA scenarios, plan review, and verification commands.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, TodoWrite
user-invocable: true
---

# OMO Plan

Create an implementation-ready plan before work that touches 2+ files, depends on caller/callee order or shared state, changes user-visible/API/CLI behavior, or needs 2+ validation checks. The plan should be strong enough for another agent to execute without reinterpreting the goal.

## Plan Requirements

- State the goal and non-goals.
- Identify files, modules, or systems likely involved.
- Define acceptance criteria.
- Break work into atomic steps.
- Mark safe parallel waves.
- Include tests, diagnostics, build commands, and manual QA where they fit the deliverable.
- Include the evidence each step must produce, such as changed files, tests, diagnostics, or review output.
- Identify true blockers and one precise question for each blocker.
- Add a dependency matrix that shows which steps must precede others.
- Add the blocking QA scenarios defined below to every task.
- Classify gaps as critical, minor, or ambiguous.
- Review the plan for executability before handing it to an implementer.
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
