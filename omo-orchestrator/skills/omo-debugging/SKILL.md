---
name: omo-debugging
description: Hypothesis-driven debugging with reproduction first, root cause proof, failing validation, minimal fix, and verified recovery.
argument-hint: [bug]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Debugging

Use this skill for real bugs, crashes, wrong output, flaky behavior, or unexplained regressions.

## Workflow

1. Reproduce the issue first.
2. State at least three plausible hypotheses.
3. Gather evidence that eliminates or strengthens each hypothesis.
4. Prove the root cause before changing code.
5. Add or identify a failing test or validation target when the project supports it.
6. Apply the smallest fix that removes the proven cause.
7. Re-run the reproduction and related validation.

## Hard Rules

- Do not start with speculative fixes.
- Do not stop at symptom relief if the cause is still unknown.
- Do not claim a bug is fixed without reproducing the previous failure mode or validating the affected behavior.
- Do not broaden the patch into refactoring unless the refactor is required to make the fix safe.

## Deliverables

Report the reproduction path, root cause, fix, validation, and any remaining uncertainty.
