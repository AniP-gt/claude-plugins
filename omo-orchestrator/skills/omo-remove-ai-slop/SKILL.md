---
name: omo-remove-ai-slop
description: Clean AI-generated code patterns with regression lock first, better comments, lower complexity, deduplication, and real verification.
argument-hint: [diff-or-files]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Remove AI Slop

Use this skill to clean AI-generated code smells without changing intended behavior.

## Cleanup Priorities

1. Lock behavior first with regression coverage or an equivalent validation target.
2. Remove comments that restate the code or sound machine-generated.
3. Collapse duplicate code and repeated branches.
4. Reduce needless indirection, nesting, and placeholder abstractions.
5. Tighten names, types, and control flow.
6. Re-verify after each cleanup cluster.

## Targets

- useless or noisy comments
- duplicate code paths
- speculative abstraction
- overly long condition chains
- fake helper layers that hide simple logic
- unnecessary fallback logic

## Hard Rules

- Do not claim slop is removed without regression protection.
- Do not replace one vague abstraction with another.
- Do not preserve bad comments for sentimentality.
- Do not turn cleanup into a feature change.

## Delivery Contract

Report what patterns were removed, which files changed, and how behavior was verified.
