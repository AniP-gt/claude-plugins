---
name: omo-principles
description: "Engineering principles ported from pstack (subtract before you add, attack the premise, fix root causes, prove it works, model the domain, and 19 more), each with its trigger. Use when planning, implementing, debugging, testing, or reviewing a change and a principle's trigger matches."
argument-hint: "[principle-or-situation]"
allowed-tools: Read, Grep, Glob
user-invocable: true
---

# OMO Principles

Ported from the `principle-*` skills of pstack (cursor/plugins `pstack`, commit `7a58391`, MIT, Copyright (c) 2026 Lauren Tan; license in `LICENSE.pstack` next to this file). Each principle lives in `references/<name>.md`, with its trigger on the third line.

## How to apply

- Before a decision, check the triggers below against the task. When one matches, Read that reference in full before acting on it. Do not apply a principle from its one-line summary here.
- In the report or plan, name each principle that shaped a decision and the specific choice it changed. Name only principles whose reference you read in this session.
- A principle is a default, not a rule that overrides the task. On a conflict, this order wins: the user's instructions, then the project's rules (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/`), then the other omo skills, then these principles. Say which one won when you set a principle aside.
- Read-only workers apply the principles to what they report: a researcher or reviewer names the principle a finding rests on, and a planner names the one that ordered the steps.

## Index

The file name is the title in kebab case: `references/<name>.md`.

**Core**

- `laziness-protocol`: refactoring, sizing a diff, or tempted to add abstractions, layers, or signal threading. Bias to deletion and the smallest change.
- `foundational-thinking`: before writing logic. Core types and data structures first, scaffold before features, what concurrent actors share.
- `redesign-from-first-principles`: integrating a new requirement into an existing design. Redesign as if it had been there from the start, deliver incrementally.
- `attack-the-premise`: two or more fixes sharing one premise failed the same gate. Write the premise down and test it before the next fix.
- `subtract-before-you-add`: sequencing an addition, refactor, or rewrite. Remove dead weight first.
- `minimize-reader-load`: code that is hard to trace. Collapse one-caller wrappers, shrink mutable scope.
- `outcome-oriented-execution`: planned rewrites and migrations with explicit phase boundaries. Converge on the target, no throwaway compatibility states.
- `experience-first`: product, UX, or feature-scope tradeoffs. Choose the consumer's experience over implementation convenience.
- `exhaust-the-design-space`: a novel interaction or architectural decision with no precedent. Compare 2-3 prototypes before committing.
- `build-the-lever`: any non-trivial work. Build the script, codemod, or check that does or proves it, so a reviewer can rerun it.

**Architecture**

- `model-the-domain`: stateful logic, or code that branches a lot or repeats a shape assumption across files.
- `boundary-discipline`: wiring validation, error handling, or framework adapters. Guards at system boundaries, pure logic inside.
- `type-system-discipline`: designing types or a signature in a typed language. Illegal states unrepresentable, parse at boundaries.
- `make-operations-idempotent`: commands, lifecycle steps, or loops that run amid crashes and retries.
- `migrate-callers-then-delete-legacy-apis`: a new internal API while old callers exist. Migrate and delete in one wave.
- `separate-before-serializing-shared-state`: concurrent actors might write the same file, branch, key, or object.

**Verification**

- `prove-it-works`: before declaring done. Check the real artifact, not a proxy.
- `fix-root-causes`: debugging. Fix the first place the system went wrong; a guard is a fix only for a legitimate state.
- `sequence-verifiable-units`: multi-step work and how commits and PRs are stacked. Small units, each checked before the next.
- `test-behavior-not-implementation`: writing, changing, or keeping a test. Assert what users of the code can observe.
- `explain-the-number`: before measuring, and before trusting or reporting a measured number. Find the limiter, rule out other explanations.

**Delegation**

- `guard-the-context-window`: context filling up. Route bulk to sub-agents, keep summaries in the main thread.
- `never-block-on-the-human`: tempted to ask "should I do X?" on reversible work. Proceed and present, within the omo rules that require asking.

**Meta**

- `encode-lessons-in-structure`: the same instruction written a second time, or a recurring correction. Encode it as a lint, check, or script.

## Where omo already covers a principle

These omo rules are more specific and stay in force; the principle adds the reasoning behind them.

- `prove-it-works`: `omo-implement` `references/real-surface-qa.md` and the review gates.
- `fix-root-causes`, `attack-the-premise`: `omo-programming` mode `debugging`.
- `explain-the-number`: `omo-implement` `references/measured-verification.md` and `omo-research` mode `eval-integrity`.
- `guard-the-context-window`: `omo-guardrails` `references/context-and-handoff.md`.
- `exhaust-the-design-space`: `omo-ultrawork` mode `arena`.
- `encode-lessons-in-structure`: `omo-implement` mode `correct-mistakes`.
