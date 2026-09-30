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
2. Remove comments that restate the code or sound machine-generated. Classify each added comment with `references/comment-patterns.md` (detection signals, KEEP cases, report table). Use it on its own for a comment-only check after editing code.
3. Collapse duplicate code and repeated branches.
4. Reduce needless indirection, nesting, and placeholder abstractions.
5. Tighten names, types, and control flow.
6. Re-verify after each cleanup cluster.
7. For deletion candidates, follow `/omo-remove-deadcode`, the canonical reachability policy.

## Cleanup Clusters And Evidence

A cleanup cluster is one behavior-preserving group of related edits in one concern, such as noisy comments in a module, one duplicated branch family, or one unnecessary helper layer. Do not mix unrelated concerns in a cluster.

For each cluster, record:

```text
Cluster and files:
Behavior lock before cleanup:
Validation before cleanup: command or procedure, result, evidence location
Validation after cleanup: command or procedure, result, evidence location
Removed patterns and retained exceptions:
```

For a deletion candidate, hand off to `/omo-remove-deadcode` with the candidate path or symbol, reachability evidence, protected validation target, uncertainty, and next exact action. Record the handoff outcome before claiming that deletion is complete.

## Targets

- useless or noisy comments
- duplicate code paths
- speculative abstraction
- overly long condition chains
- fake helper layers that hide simple logic
- unnecessary fallback logic

## Decision Rules

- KEEP system-boundary validation, I/O error handling, public compatibility behavior, type information, BDD comments, and comments that explain non-obvious intent.
- REMOVE only code or comments whose behavior and reachability are understood and whose removal is protected by the validation target.
- SKIP WHEN UNCERTAIN. Preserve the candidate, record the uncertainty, and ask for evidence rather than guessing.

## Hard Rules

- Do not claim slop is removed without regression protection.
- Do not replace one vague abstraction with another.
- Do not preserve bad comments for sentimentality.
- Do not turn cleanup into a feature change.
- Default to KEEP when the evidence does not support removal.

## Delivery Contract

Report each cleanup cluster, what patterns were removed, which files changed, the before and after validation fields, and any `/omo-remove-deadcode` handoff record.
