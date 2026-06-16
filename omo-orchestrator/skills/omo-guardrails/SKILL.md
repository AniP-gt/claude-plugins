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
- Preserve state through a short handoff when context may be lost.
- Classify errors before retrying: retryable, non-retryable, blocked, or stop.
- Ask one precise question when missing information materially changes the result.
- Keep final claims tied to actual verification.

## Handoff Minimum

Record goal, current state, files changed, validation, blockers, next action, and files not to touch.
