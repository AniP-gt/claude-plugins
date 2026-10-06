# Ultrawork Auto-Escalation

Implementation skills (`omo-implement`, `omo-refactor`, `omo-debugging`, `omo-remove-ai-slop`, `omo-remove-deadcode`, `omo-frontend`) may enter ultrawork mode on their own judgment, without the `ulw` keyword. This file is the single source for that decision.

## When the check runs

Run the check once, at the start of the task, after reading enough context to size it. Skip it entirely when the skill was delegated by an active controller: `omo-ultrawork`, `omo-ulw-execute`, `omo-mass-ulw`, `omo-review-loop`, `omo-ralph-loop`, or `omo-orchestrate`. A delegated skill returns to its caller and never starts ultrawork, so controllers do not nest.

## Escalate when any applies

- The change touches 3+ files or more than one deliverable surface (for example CLI and config, or API and UI).
- It is migration, performance, security, persistence, or public-behavior work, or a refactor that crosses module boundaries.
- It needs 2+ dependent steps that would benefit from a plan and parallel waves.
- An earlier attempt at the same task failed or was rejected by review.
- The user asked for rigor ("strictly", "rigorously", "厳密", "深く", "しっかり").

## Stay in the current skill when any applies

- The change is trivial: 1-2 obvious lines with all context already loaded.
- It changes only wording, docs, comments, or config values and adds no branch.
- The task is read-only (investigation, review, explanation).
- The user asked for a quick or light pass ("軽く", "さっと", "quick"), or said not to use ultrawork.

When both lists match, the stay list wins only for an explicit user request; otherwise escalate.

## How to escalate

1. Print one line before anything else: `Ultrawork auto-escalation: <the matching condition>`.
2. Load `omo-ultrawork` and follow its Bootstrap from step 1. Ultrawork now owns the task, including the `omo-ralph-loop` ledger; do not also start a controller from the original skill.
3. Keep the original skill's workflow as the per-task rules inside ultrawork briefs (for example, `omo-debugging`'s reproduce-first and root-cause proof, `omo-refactor`'s behavior lock).

## Mid-task ratchet

If a task that stayed in its skill later meets an escalate condition (the scope grows to 3+ files, a fix attempt fails review, a security or persistence path appears), escalate at that point and carry over the evidence gathered so far into the ultrawork notepad. Never de-escalate once ultrawork has started.
