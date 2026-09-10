---
name: omo-pre-publish-review
description: Release gate for OMO work. Reviews unpublished changes across compatibility, security, packaging, docs, tests, and operational risk.
argument-hint: [release-scope]
allowed-tools: Read, Grep, Glob, Bash, Task
user-invocable: true
---

# OMO Pre-Publish Review

Use this skill before publishing a plugin, package, CLI, or release branch. It is a release-focused gate, not a general code review.

## Review Areas

- Version and changelog accuracy.
- Public API, CLI, plugin, or skill contract changes.
- Package contents, install paths, scripts, and generated artifacts.
- Security and credential exposure.
- Backward compatibility for already published behavior.
- Required docs, migration notes, and setup instructions.
- Tests, validation commands, and manual smoke checks.

## Flow

1. Start from unpublished-change analysis when available.
2. Review each release layer independently: metadata, docs, runtime files, tests, examples, and packaging.
3. Mark every finding as blocking, warning, or informational.
4. Require concrete evidence for blockers.
5. Return `APPROVE`, `REQUEST_CHANGES`, or `INCONCLUSIVE`.
6. For a publish workflow, record the exact dispatched run or release identity and monitor that owner only. Never infer ownership from the latest run.
7. Treat transient failures as an idempotent rerun only when the source revision and release inputs remain correct. A source, workflow, version, or input correction requires a new owned release attempt.

## Hard Rules

- Do not approve if version metadata is inconsistent.
- Do not approve if packaging would omit required files or include secrets.
- Do not approve if release-facing docs contradict behavior.
- Do not treat missing validation as non-blocking when the release changes executable behavior.
- Do not repair product code while publishing. Stop on a failed release gate, return the defect to normal implementation and review, then begin a new release review with fresh evidence.
- Do not bypass a failed gate, move a release tag manually, or hand-publish as a workaround.

## Output Contract

- Release scope and baseline.
- Decision.
- Blocking findings.
- Warnings.
- Required validation before publish.
- Version or documentation corrections.
