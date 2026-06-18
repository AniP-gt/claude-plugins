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
2. Lock behavior first with existing tests or added regression coverage.
3. Inventory callers, callees, inputs, outputs, and side effects.
4. Refactor in small reversible steps.
5. Re-run targeted validation after each meaningful step.
6. Stop if behavior drift appears and fix the drift before continuing.

## Hard Rules

- Do not mix feature work into a refactor unless the task explicitly asks for both.
- Do not rename or reshape public contracts without a proven need.
- Do not batch unrelated cleanups into the same change.
- Do not remove coverage that protects current behavior.

## Report Contract

State what was reorganized, what behavior was locked, what validation ran, and whether any contract moved.
