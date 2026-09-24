---
name: omo-get-unpublished-changes
description: Compare current work against the latest published baseline and classify unpublished changes by behavior, risk, and version impact.
argument-hint: [package-or-baseline]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Get Unpublished Changes

Use this skill before release planning, pre-publish review, or PR handoff when you need to know what has changed since the last published or agreed baseline.

## Workflow

1. Select one explicit baseline: a user-provided commit or tag takes precedence; otherwise use the latest verifiable published version or release tag; use the main branch only when it is the agreed release baseline. Record why that baseline applies.
2. If no baseline can be verified or agreed, stop before classifying release impact. Report the baseline-selection failure, the evidence needed to resolve it, and no recommended version bump.
3. Compare actual diffs, not only commit messages.
4. Group changes by user-facing behavior, API or CLI contract, data or persistence, security, performance, tests, docs, and internal refactor.
5. Classify each evidenced group as patch, minor, major, or non-release-impacting: patch is a backward-compatible fix, minor adds backward-compatible behavior, major changes or removes an existing contract, and non-release-impacting has no evidenced public or packaged effect.
6. Call out breaking changes, migration needs, removed behavior, new required configuration, and changed defaults.
7. Record uncertainty separately when evidence is missing.

## Hard Rules

- Do not infer release impact from titles alone.
- Do not hide internal changes that affect public behavior.
- Do not recommend a version bump without citing the behavior or contract change that justifies it.
- Identify unrelated dirty work separately. Exclude it from the release diff and version recommendation unless the owner explicitly confirms it is part of the release candidate; report that exclusion and confirmation status.

## Output Contract

- Baseline used.
- Baseline-selection evidence or failure.
- Change groups with evidence.
- Breaking-change candidates.
- Recommended version bump.
- Missing evidence or release risks.
- Files or commits that need review before publishing.
