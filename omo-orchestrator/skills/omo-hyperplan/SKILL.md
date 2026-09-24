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
2. Build a request brief with the problem framing, available evidence, unresolved assumptions, and rollback or stop constraints. Do not sequence implementation tasks yet.
3. Run three critique rounds across five perspectives: skeptic, validator, researcher, architect, and creative. Every perspective returns: concern, evidence, affected assumption, severity, proposed resolution, and open question.
4. Round 1 collects independent concerns. Round 2 cross-tests only Round 1 concerns with evidence. Round 3 defends, refines, or rejects the survivors. A missing return is recorded as an evidence gap, not inferred agreement.
5. Use one manual review section per perspective when `Task` reviewers are unavailable. Keep the same fields, but scale the number of perspectives to available capacity and state which perspectives were omitted and why.
6. Distill only surviving findings into an insight bundle. Mark each candidate as accepted, rejected with evidence, or blocked by missing information.
7. Hand the bundle and its unresolved questions to `omo-planner` for plan formalization. The adversarial lead must not pre-write the executable plan.
8. The planner returns one plan with clear owners, ordered dependencies, parallel opportunities, verification gates, and every unresolved critical blocker. Hand it to an implementer only after the planner resolves or exposes those blockers.

## Hard Rules

- Do not use hyperplanning to delay small obvious fixes.
- Do not accept a critique that lacks evidence or a reproducible risk.
- Do not let adversarial review create scope creep. Add new work only when it is required for the stated goal.
- Do not start implementation while a critical planning blocker remains unresolved.
- Do not claim runtime team behavior. Preserve critique returns, omitted perspectives, and the planner handoff in the handoff.

## Output Contract

- TL;DR decision.
- Final executable plan.
- Accepted critique findings.
- Rejected critique findings with evidence.
- Blockers and one precise question per blocker.
- Verification gates and final handoff.
