---
name: omo-remove-deadcode
description: Safely remove dead code with reference checks, behavior locks, dependency analysis, and zero-false-positive deletion discipline.
argument-hint: [scope]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Remove Deadcode

Use this skill to remove unused code without deleting behavior that is still reachable through dynamic loading, public contracts, generated references, tests, or plugin metadata.

## Workflow

1. Define the deletion scope and non-goals.
2. Build an inventory of candidate files, symbols, exports, commands, and metadata entries.
3. Check references with text search, structural search when available, type or LSP references when available, tests, docs, and runtime registration points.
4. Classify each candidate as safe delete, keep, needs migration, or inconclusive.
5. Delete in small batches and update registration, docs, tests, and snapshots that legitimately referenced the removed code.
6. Run targeted tests, diagnostics, build checks, and manual smoke checks when the code is user-visible.

## Hard Rules

- Do not delete a candidate with inconclusive references.
- Do not assume no references means no runtime use when registries, reflection, plugin metadata, shell scripts, or generated files exist.
- Do not delete tests to make removal pass.
- Do not combine dead-code removal with unrelated refactors.

## Output Contract

- Deleted files or symbols.
- Evidence that each was unreachable.
- Kept or inconclusive candidates.
- Validation run.
- Residual risk.
