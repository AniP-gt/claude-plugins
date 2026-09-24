# Baseline: omo-get-unpublished-changes, UPC-E

## Evaluation Record

- Target: `omo-orchestrator/skills/omo-get-unpublished-changes/SKILL.md`
- Frozen scenario: `UPC-E`, unrelated dirty files and a missing baseline tag.
- Basis: prompt-only assessment. No disposable fixture or fresh executor result was supplied to this run.
- Empirical status: empirical evaluation skipped: dispatch unavailable.
- Fixture boundary: no fixture files were read or changed.

## Frozen Checklist Results

| Item | Score | Reason |
| --- | --- | --- |
| 1. [critical] Excludes unrelated dirty work and marks the baseline uncertainty. | partial | The hard rule excludes unrelated dirty work unless it belongs to the release candidate, and the workflow requires uncertainty to be recorded when evidence is missing. It does not state what to do when the selected baseline tag is absent, such as stop, select an agreed fallback, or name the missing reference. |
| 2. Does not infer a version bump without behavior or contract evidence. | ○ | The hard rules prohibit a version recommendation without cited behavior or contract change, while the workflow requires actual diffs rather than titles. |
| 3. Names the files or evidence needed before release judgment. | ○ | The output contract requires missing evidence or release risks and files or commits needing review before publishing. |

## Score

- Success: ×
- Accuracy: 83.3% (2.5 / 3)
- Success rationale: the critical item is `partial`, and the frozen protocol requires every critical item to be `○`.

## Execution Metadata

- Executor: unavailable
- `tool_uses`: unavailable
- `duration_ms`: unavailable
- Retries: unavailable. No executor judgment was performed or repeated.

## Unclear Points

- [critical] Item 1: the prompt identifies possible baseline types but does not define a bounded response when the chosen tag is missing. An executor must decide whether to stop, use another baseline, or continue with an uncertainty-only report.
- The release-candidate boundary is named, but the prompt does not say how to determine that boundary when unrelated dirty files are present in the fixture.

## Discretion Gaps

- An executor must choose whether a supplied baseline snapshot can replace a missing tag without explicit confirmation.
- An executor must choose the evidence needed to classify a dirty file as release-candidate work rather than unrelated work.
- An executor must choose whether insufficient baseline evidence permits a version recommendation when the current diff appears to include a contract change.

## Frozen-Item Fix Proposal

- For frozen item 1, add a single workflow branch: when the requested baseline tag is missing, state the baseline as unavailable, exclude unrelated dirty files, name the exact fallback reference or evidence required, and do not issue a release-impact or version-bump judgment until that reference is supplied.
