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
- State the requested boundary explicitly: what was requested, which files or behaviors changed to satisfy it, and which adjacent work remained out of scope.

## Hard Rules

- Do not use `as any`, `@ts-ignore`, or `@ts-expect-error` to silence errors.
- Do not claim validation passed unless you ran it in the current session.
- Do not invent test results, diagnostics, or build results.
- Do not widen scope with cleanup or refactors unless they are required for the requested change.
- Do not edit unrelated dirty files.
- Do not add fallback logic unless an existing contract requires it.
- Do not delete code as dead unless references, registries, tests, docs, and runtime entry points have been checked or explicitly marked inconclusive.
- Before deleting generated files, metadata, or registrations, identify their generator or owning metadata and check every registration or manifest that can publish, load, package, or reference them. Report the evidence, or mark the check inconclusive and do not claim deletion safety.

## Delivery Contract

Report the requested-boundary statement, behavior change, changed files, validation that was actually run, generated or metadata registration evidence for any deletion, and any area left unverified.
