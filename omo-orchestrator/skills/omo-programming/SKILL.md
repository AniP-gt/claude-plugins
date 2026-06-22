---
name: omo-programming
description: Implementation policy for type-safe, minimal, evidence-backed code changes with real diagnostics, tests, and no fake validation.
argument-hint: [task]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite
user-invocable: true
---

# OMO Programming

Use this skill when writing or editing production code.

## Policy

- Read nearby code first and match existing patterns.
- Prefer the smallest diff that satisfies the requested behavior.
- Keep types honest. Fix the type problem instead of hiding it.
- Add or identify the validation target before claiming success.
- Run real diagnostics and real tests when the project supports them.
- Record evidence for each claim: changed files, diagnostics, tests, builds, or manual QA.
- Use reference checks before deleting code, exports, commands, plugin metadata, or public docs.

## Hard Rules

- Do not use `as any`, `@ts-ignore`, or `@ts-expect-error` to silence errors.
- Do not claim validation passed unless you ran it in the current session.
- Do not invent test results, diagnostics, or build results.
- Do not widen scope with cleanup or refactors unless they are required for the requested change.
- Do not edit unrelated dirty files.
- Do not add fallback logic unless an existing contract requires it.
- Do not delete code as dead unless references, registries, tests, docs, and runtime entry points have been checked or explicitly marked inconclusive.

## Delivery Contract

Report the behavior change, changed files, validation that was actually run, and any area left unverified.
