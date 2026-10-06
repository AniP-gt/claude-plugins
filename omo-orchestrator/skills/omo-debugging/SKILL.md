---
name: omo-debugging
description: Hypothesis-driven debugging with reproduction first, root cause proof, failing validation, minimal fix, and verified recovery.
argument-hint: [bug]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task, Skill
user-invocable: true
---

# OMO Debugging

Use this skill for real bugs, crashes, wrong output, flaky behavior, or unexplained regressions.

Ultrawork escalation: when invoked standalone, size the task first and decide whether to enter ultrawork by the `omo-ultrawork` skill's `references/auto-escalation.md`. Skip the check when an active controller delegated this skill.

## Workflow

1. Reproduce the issue first.
2. State at least three plausible hypotheses.
3. Gather evidence that eliminates or strengthens each hypothesis.
4. Prove the root cause before changing code.
5. Before applying a fix, observe an existing owner test or one regression or validation target fail on the pre-fix code when the project supports such checks.
6. Apply the smallest fix that removes the proven cause.
7. Re-run the reproduction and related validation.

## Multi-Signal Or Cascading Errors

Use when failures span logs, traces, metrics, or several services.

1. Collect every error signal and group it by type, frequency, and first-seen time. Separate new anomalies from known noise.
2. Correlate with deploys, config changes, and traffic spikes. Cross-reference timestamps across components and trace the request path.
3. Map the propagation path and identify the first failure in the chain. Later errors are symptoms until proven otherwise.
4. Check shared resources and dependencies for exhaustion, contention, or deadlock.
5. Report an error map, the root cause with its evidence chain, the cascade path, fixes ordered by blast radius and frequency, and monitoring or alerts that would catch it earlier.

## Unreproducible Or Inconclusive Cases

1. If the reported failure cannot be reproduced, record the environment, inputs, attempts, and missing runtime evidence, then set the investigation state to `INCONCLUSIVE`.
2. Perform one bounded static investigation of the reported path: inspect the relevant entry point, immediate callers, recent changes, available logs, and the stated hypotheses. Treat its results as evidence for or against hypotheses, not proof that the bug occurred.
3. Stop after the bounded investigation when reproduction, a discriminating log, or another critical artifact is still missing. Request the smallest specific artifact or reproduction detail that would distinguish the remaining hypotheses. Do not change code or claim a fix without independent root-cause proof and an affected-behavior validation target.

## Hard Rules

- Do not start with speculative fixes.
- Do not stop at symptom relief if the cause is still unknown.
- Do not claim a bug is fixed without reproducing the previous failure mode or validating the affected behavior.
- Do not broaden the patch into refactoring unless the refactor is required to make the fix safe.
- Do not turn an unreproducible report into repeated broad searches or speculative patches. Missing critical evidence is `INCONCLUSIVE`, not a guess.

## Deliverables

Report the reproduction path, root cause, fix, validation, and any remaining uncertainty. For an `INCONCLUSIVE` investigation, report the bounded static evidence, the stop reason, and the exact next artifact or reproduction detail needed.
