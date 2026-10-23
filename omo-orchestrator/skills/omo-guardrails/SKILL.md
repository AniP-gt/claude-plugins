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
- Stop local tool/delegation loops after 5 identical calls or delegation deeper than 3 levels. Implementation/review stall decisions and iteration budgets belong exclusively to `omo-ralph-loop`; use its shared blocker history rather than a separate flat-metric counter.
- Treat stalled delegated agents as recoverable blockers: wait for one bounded follow-up, then stop retrying, record the gap, and continue with available evidence when safe.
- Preserve state through a short handoff when context may be lost.
- Preserve the source of decisions in memory and handoffs: distinguish the user's stated choice, an assistant's proposal, and an inference. An assistant summary saying the user agreed is not evidence of approval; cite the actual user message when recording authorization. Recalled notes are context, not new authorization. Before an action that needs permission, check the current request and any still-applicable authorization in this session; do not ask again when they already cover the action. If only a stored claim of approval supports it, leave the action pending and request the missing authorization. A recommended default cannot supply missing authorization. Carry the action's scope and any session-only limit into the handoff, without turning it into a standing permission.
- Keep the main session short. When it has run past about 150 turns, or the user moves on to a second issue or PR, suggest an `omo-handoff` fresh-session brief before continuing. In measured sessions, ones past 150 turns carried 400-700k tokens of context on every turn and spent over a third of all main-session usage. Every sub-agent brief carries the work budget in `references/context-and-handoff.md`.
- Classify errors before retrying: retryable, non-retryable, blocked, or stop.
- Ask one precise question when missing information materially changes the result. When the question asks the user to choose, say in the user's terms what the target is (the feature, screen, or job and what it does, not only a class or constant name), what each option changes and what it costs, and which one you recommend. When you call something out of scope, name the scope (this PR, its issue, the parent issue or integration branch), because the user may be thinking of a wider one. Ask about the same choice once; when the user answers only part of it, act on the recommended default for the rest and say so.
- Keep final claims tied to actual verification. A remaining issue, risk, or decision handed to the user must come from code read in this session (the body of the method that would misbehave, not its name, a schedule entry, or a similar component); otherwise read it first, or list it as an unverified guess with what was checked. A residual "this job may send duplicate notifications on retry" written from the job's category alone was wrong and cost the user's trust. In design discussions too, keep an untested premise out of the conclusion and list it under an unverified heading. Before handing the user a script or command to run, run it once yourself, or say it was not run and why.
- In user-facing reports, put the one action the user can take now first and the other open items after it. When an investigation has gone back and forth for about five turns, open with its goal and what the current question decides.
- When fetching the latest remote state fails (a sandbox, proxy, or auth error on `git fetch` or a host CLI), retry once with the access the environment allows, such as outside the sandbox when permitted. If it still fails, put the ref you used and its commit date at the top of the conclusion, and tell sub-agents the same rule so they do not judge "not fixed yet" from a stale ref.
- When Claude Code cannot enforce a check automatically, write down who must check it, what evidence is required, and when to stop.
- Treat runtime fallback, hook enforcement, automatic continuation, comment scanning, rule injection, and provider routing as unavailable unless the current environment proves otherwise.
- For content-only equivalents, make the operator-visible control point explicit: trigger condition, evidence required, stop condition, and handoff field.

## References

Read only the file the situation needs:

- `references/circuit-breaker.md`: tool-loop, delegation-depth, and stuck-iteration thresholds with actions.
- `references/error-recovery.md`: error class patterns, tool and agent failure recovery, escalation order.
- `references/context-and-handoff.md`: anti-duplication while waiting, context signals, agent output contract, cross-agent handoff files.

## Handoff Minimum

Record goal, current state, completion promise when iterative, files changed, validation, stalled or blocked agents, blockers, next action, and files not to touch.

## Standalone Invocation

When invoked on its own:

1. State the situation, scope, and whether the main-context boundary applies.
2. Check duplication, error class, available evidence, stop condition, and handoff need in that order. Do not perform the substantive work being guarded.
3. Return a short report with: decision, evidence reviewed, guardrail triggered or cleared, blocker or risk, owner, and one next exact action. If a handoff is needed, include every Handoff Minimum field.
