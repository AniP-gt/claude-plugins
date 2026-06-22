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

1. Identify the baseline: latest published version, release tag, main branch, or user-provided commit.
2. Compare actual diffs, not only commit messages.
3. Group changes by user-facing behavior, API or CLI contract, data or persistence, security, performance, tests, docs, and internal refactor.
4. Classify each group as patch, minor, major, or non-release-impacting.
5. Call out breaking changes, migration needs, removed behavior, new required configuration, and changed defaults.
6. Record uncertainty separately when evidence is missing.

## Hard Rules

- Do not infer release impact from titles alone.
- Do not hide internal changes that affect public behavior.
- Do not recommend a version bump without citing the behavior or contract change that justifies it.
- Do not include unrelated dirty work unless it is part of the release candidate.

## Output Contract

- Baseline used.
- Change groups with evidence.
- Breaking-change candidates.
- Recommended version bump.
- Missing evidence or release risks.
- Files or commits that need review before publishing.
