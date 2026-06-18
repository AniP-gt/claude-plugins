---
name: omo-ultraresearch
description: Exhaustive read-only research mode with source matrix, evidence thresholds, explicit non-goals, and stop conditions.
argument-hint: [question]
allowed-tools: Read, Grep, Glob, Bash, TodoWrite
user-invocable: true
---

# OMO Ultraresearch

Use this skill for exhaustive read-only investigation when the next decision depends on broad evidence, not a quick scan.

## Research Workflow

1. State the research question.
2. State explicit non-goals.
3. Build a source matrix: files, symbols, tests, docs, configs, and command outputs to inspect.
4. Set evidence thresholds for a usable answer.
5. Search exact matches first, then variants, callers, callees, and neighboring modules.
6. Separate confirmed facts, likely inferences, and open gaps.
7. Stop when the evidence threshold is met or a declared stop condition is hit.

## Stop Conditions

- The key question is answered with direct evidence.
- Remaining gaps are non-critical and clearly labeled.
- Further searching only repeats known results.
- A missing source blocks confidence and must be escalated.

## Hard Rules

- Stay read-only.
- Do not turn research into implementation.
- Do not flatten conflicting evidence into a single claim.
- Do not hide uncertainty when the sources disagree.

## Output Contract

Return the source matrix, findings, open questions, confidence level, and recommended next action.
