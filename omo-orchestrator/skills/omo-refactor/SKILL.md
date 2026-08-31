---
name: omo-refactor
description: Safe refactoring workflow with behavior lock first, caller and callee inventory, small steps, and verification against drift.
argument-hint: [refactor-goal]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Refactor

Use this skill when the goal is structure, readability, or maintainability without intended behavior change.

## Workflow

1. Define the refactor boundary and non-goals.
2. Capture the baseline: relevant behavior, validation results, and pre-existing changes that must remain untouched.
3. Lock behavior first with existing tests or added regression coverage.
4. Inventory callers, callees, inputs, outputs, and side effects.
5. Refactor in small reversible steps with a step-local undo plan that preserves pre-existing changes.
6. Re-run targeted validation after each meaningful step.
7. If targeted validation fails, undo only the recorded current-step delta, preserve pre-existing changes, and record the failed check and last safe state. Retry at most once with a materially different approach only when the behavior lock, scope, and public contract remain sound. If that retry fails or those conditions are not sound, abort.

## Hard Rules

- Do not mix feature work into a refactor unless the task explicitly asks for both.
- Do not rename or reshape public contracts without a proven need.
- Do not batch unrelated cleanups into the same change.
- Do not remove coverage that protects current behavior.
- Abort before editing when the behavior lock or scope is unclear, or when the change would break a public contract.
- Do not use broad destructive reset, checkout, or restore commands. Undo only the exact recorded current-step delta.

## Report Contract

State what was reorganized, what behavior was locked, the baseline, each failed check and last safe state if applicable, what validation ran, and whether any contract moved.
