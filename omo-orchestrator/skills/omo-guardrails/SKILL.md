---
name: omo-guardrails
description: "Safety rules for OMO-style work: anti-duplication, context guard, circuit breaker, error recovery, and explicit handoffs."
argument-hint: [situation]
allowed-tools: Read, Grep, Glob, TodoWrite
user-invocable: true
---

# OMO Guardrails

Use this skill to keep long-running or delegated work safe and recoverable.

Main-context boundary: when OMO is used as an orchestration layer, the main context must stay coordinator-only. It may route, track state, synthesize evidence, and hand off, but implementation, investigation, review, validation commands, and fixes must be assigned to sub-agents.

## Rules

- Do not duplicate a search already assigned to a specialist.
- Do not let the main context take over substantive work that should be delegated to a specialist sub-agent.
- Stop loops after repeated identical attempts and change strategy.
- Treat stalled delegated agents as recoverable blockers: wait for one bounded follow-up, then stop retrying, record the gap, and continue with available evidence when safe.
- Preserve state through a short handoff when context may be lost.
- Classify errors before retrying: retryable, non-retryable, blocked, or stop.
- Ask one precise question when missing information materially changes the result.
- Keep final claims tied to actual verification.
- Convert runtime-only OMO ideas into manual checkpoints. If Claude Code cannot enforce something automatically, write down who must check it, what evidence is required, and when to stop.
- Treat runtime fallback, hook enforcement, automatic continuation, comment scanning, rule injection, and provider routing as unavailable unless the current environment proves otherwise.
- For content-only equivalents, make the operator-visible control point explicit: trigger condition, evidence required, stop condition, and handoff field.

## Handoff Minimum

Record goal, current state, completion promise when iterative, files changed, validation, stalled or blocked agents, blockers, next action, and files not to touch.
