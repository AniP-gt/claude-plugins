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
- Include tests, diagnostics, build commands, and manual QA.
- Include the evidence each step must produce, such as changed files, tests, diagnostics, or review output.
- Identify true blockers and one precise question for each blocker.
- Add a dependency matrix that shows which steps must precede others.
- Add QA scenarios for median, edge, and failure-path behavior when applicable.
- Classify gaps as critical, minor, or ambiguous.
- Review the plan for executability before handing it to an implementer.

Use TDD where the project supports it: define the failing test or validation target before implementation.

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
- Final handoff for the implementer.

For parallel waves, note which results are blocking and which can be merged later with bounded follow-up.
