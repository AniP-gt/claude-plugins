---
name: omo-programming
description: Implementation policy for type-safe, minimal, evidence-backed code changes with real diagnostics, tests, and no fake validation. Use for work on .py, .rs, .ts, or .go files. Modes: debugging (crash, silent failure, hang, wrong response, memory leak, async misbehavior), refactor (refactor, simplify, extract, restructure, modernize), remove-deadcode (dead, unused, unreachable code).
argument-hint: [task]
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, TodoWrite, Task, Skill
user-invocable: true
---

# OMO Programming

Use this skill when writing or editing production code.

## Modes

This skill has three modes. Each mode's procedure lives in `modes/<mode>/MODE.md`.

| Mode | Alias | Precedence | Use when |
|---|---|---|---|
| `debugging` | - | adds to | crash, silent failure, hang, wrong response, memory leak, async misbehavior |
| `refactor` | - | adds to | refactor, simplify, extract, restructure, modernize |
| `remove-deadcode` | - | adds to | dead, unused, unreachable code |

- "adds to" means this file's policy stays in force and the MODE.md adds its procedure.
- Selection: (a) when the first word of the arguments is a mode name, use that mode; (b) otherwise, when the brief has a `MODES:` line, use the mode it names; (c) otherwise, pick a mode by the Use-when triggers, and when none fits, follow this file's default flow. An unknown first word is part of the goal, not a mode.
- Worker rule: a `MODES: omo-programming/<mode>` line in the brief, or a matching trigger even without that line, means Read that mode's MODE.md before working.
- Path: the MODE.md path is `${CLAUDE_SKILL_DIR}/modes/<mode>/MODE.md`. If the variable is not expanded, use the Base directory shown when this skill was loaded plus `modes/<mode>/`. When this skill was preloaded and no Base directory is visible, call the Skill tool on `omo-programming` to get it. Inside a MODE.md, a bare `references/…` path is relative to that mode's directory (`modes/<mode>/`). A path qualified with another skill's name (`` `omo-x` `references/y.md` `` or "the `omo-x` skill's `references/y.md`") is relative to that skill's directory. A path of the form `skills/<name>/…` is relative to the plugin root.

## Policy

- Read nearby code first and match existing patterns.
- Prefer the smallest diff that satisfies the requested behavior.
- Keep new code modular: thin entry files, no catch-all `utils` / `helpers` files, one responsibility per file, about 200 LOC per file. These are defaults that yield to project conventions; see `references/modular-code.md`.
- Keep types honest. Fix the type problem instead of hiding it.
- Add or identify the validation target before claiming success.
- Run real diagnostics and real tests when the project supports them.
- Record evidence for each claim: changed files, diagnostics, tests, builds, or manual QA.
- Use reference checks before deleting code, exports, commands, plugin metadata, or public docs.
- Invariant ownership: enforce a rule at the entry point of the class that owns it (fail fast). Do not hand callers a mixin, an override hook, or a follow-up call they must remember; how to react to a violation (fail or report and skip) stays each caller's policy.
- When a change tightens a precondition (for example, making an identifier required), find every direct and synchronous invocation path and every test helper that reaches the code, and check that no broad error handler swallows the new failure and leaves a test passing without exercising anything.
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
