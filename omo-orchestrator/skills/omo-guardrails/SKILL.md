---
name: omo-guardrails
description: "Safety rules for OMO-style work: anti-duplication, context guard, circuit breaker, error recovery, and explicit handoffs."
argument-hint: [situation]
allowed-tools: Read, Grep, Glob, TodoWrite
user-invocable: true
---

# OMO Guardrails

Use this skill to keep long-running or delegated work safe and recoverable.

## Rules

- Do not duplicate a search already assigned to a specialist.
- Stop loops after repeated identical attempts and change strategy.
- Treat stalled delegated agents as recoverable blockers: wait for one bounded follow-up, then stop retrying, record the gap, and continue with available evidence when safe.
- Preserve state through a short handoff when context may be lost.
- Classify errors before retrying: retryable, non-retryable, blocked, or stop.
- Ask one precise question when missing information materially changes the result.
- Keep final claims tied to actual verification.

## Handoff Minimum

Record goal, current state, files changed, validation, stalled or blocked agents, blockers, next action, and files not to touch.
