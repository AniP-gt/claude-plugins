---
name: omo-hyperplan
description: Adversarial OMO planning for hard work. Runs hostile plan critique rounds, then distills an executable plan with evidence and gates.
argument-hint: [goal]
allowed-tools: Read, Grep, Glob, Task, TodoWrite
user-invocable: true
---

# OMO Hyperplan

Use this skill when normal planning is not enough: broad scope, ambiguous architecture, risky migrations, cross-system behavior, or user-visible changes that need skeptical design before implementation.

This is a content-only translation of OMO adversarial planning. It does not assume automatic team-mode runtime support; use parallel reviewers or manual sections when agents are unavailable.

## Flow

1. State the goal, non-goals, constraints, and acceptance criteria.
2. Build a baseline plan with file-level tasks, dependencies, verification, and rollback or stop conditions.
3. Run adversarial critique from five angles: executability, strategy, security, robustness, and goal alignment.
4. Require each critique to cite concrete evidence: files, contracts, tests, commands, or documented assumptions.
5. Distill the critiques into one plan. Do not paste competing plans side by side.
6. Mark each critique finding as accepted, rejected with evidence, or blocked by missing information.
7. Hand the final plan to an implementer only after the plan has clear owners, ordered dependencies, and validation gates.

## Hard Rules

- Do not use hyperplanning to delay small obvious fixes.
- Do not accept a critique that lacks evidence or a reproducible risk.
- Do not let adversarial review create scope creep. Add new work only when it is required for the stated goal.
- Do not start implementation while a critical planning blocker remains unresolved.

## Output Contract

- TL;DR decision.
- Final executable plan.
- Accepted critique findings.
- Rejected critique findings with evidence.
- Blockers and one precise question per blocker.
- Verification gates and final handoff.
