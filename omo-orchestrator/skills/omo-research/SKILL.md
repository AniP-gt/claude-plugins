---
name: omo-research
description: Read-only OMO-style research for codebase structure, existing patterns, library references, and bug hypotheses.
argument-hint: [question]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Research

Use this skill when the next action depends on understanding existing code or reference material.

## Research Contract

- Stay read-only.
- Search for the exact behavior, then nearby variants.
- Inspect callers and dependencies when root cause matters.
- Return paths, symbols, evidence, and recommended next steps.
- Separate facts from assumptions.

For broad research, split independent questions across agents and merge the findings before planning. Do not block the plan on a stalled research agent: after one bounded follow-up, mark the missing result as stalled or blocked, separate the evidence gap from confirmed facts, and proceed only if the remaining evidence is sufficient.
