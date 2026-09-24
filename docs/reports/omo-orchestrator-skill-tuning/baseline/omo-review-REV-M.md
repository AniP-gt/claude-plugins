# omo-review Baseline, REV-M

## Evaluation Record

- Target: `omo-orchestrator/skills/omo-review/SKILL.md`
- Scenario: `REV-M`, median
- Mode: artifact-only simulation
- Fixture boundary: no disposable fixture, synthetic multi-file diff, caller graph, contract, or fixture tests were supplied to this run.
- Target changes: none.
- Protocol changes: none.
- External effects: none.

## Simulated Output

No PR-style review decision was produced. The target requires concrete evidence for findings and forbids approval from inspection alone. With no diff or fixture evidence, a real executor should return `INCONCLUSIVE`, name the missing review inputs, and avoid inventing defects or verified non-issues.

## Requirements Scoring

| Item | Result | Score | Reason |
|---|---:|---:|---|
| 1. [critical] Confirms uncertain concerns against callers, contracts, tests, or patterns before making them blocking. | × | 0 | No synthetic diff, callers, contracts, tests, or patterns were available. The target requires this confirmation, but artifact-only simulation cannot perform it. |
| 2. Separates blocking findings, verified non-issues, missing validation, and residual risks. | ○ | 1 | The target's report contract explicitly requires each of these categories. This artifact keeps unavailable categories separate rather than presenting unsupported findings. |
| 3. Gives a gate decision supported by concrete evidence. | × | 0 | The target permits `INCONCLUSIVE` for missing evidence, but no fixture-specific evidence exists to support a completed REV-M review decision. |

## Result

- Success: ×
- Success reason: critical item 1 is ×.
- Accuracy: 33.3% (`1 / 3`)
- Decision for the simulated review: `INCONCLUSIVE`
- Decision reason: the required multi-file diff and fixture-test evidence are unavailable.

## Execution Metadata

| Metric | Value | Reason |
|---|---|---|
| `tool_uses` | unavailable | No fresh executor was dispatched in artifact-only simulation. The protocol prohibits estimating missing metadata. |
| `duration_ms` | unavailable | No fresh executor was dispatched in artifact-only simulation. The protocol prohibits estimating missing metadata. |
| Retries | 0 | No review judgment was executed or repeated. |

## Unclear Points

- Item 1 [critical] failed: no supplied fixture defines the changed files, relevant callers, contracts, tests, or patterns that a reviewer must inspect before classifying a concern as blocking.
- The target says to identify every changed file's role and local change, but it does not prescribe a minimum evidence record for each file before a finding is issued.
- The target requires approval evidence for dependency and retry state, but it does not say how a PR-style reviewer should record those checks when they are not applicable to a small diff.

## Discretion Gaps

- A reviewer must choose which callers, contracts, tests, or patterns are sufficient to confirm each uncertain concern.
- A reviewer must decide whether an unavailable manual QA surface is a missing-validation row, a residual risk, or both.
- A reviewer must choose the report granularity for file roles and local changes because the report contract requires scope but not a per-file evidence layout.

## Item-Linked Proposal

- Item 1 [critical]: add a required pre-finding evidence table with columns for changed file, local role, concern, verification source, and result. State that a blocking finding needs at least one populated verification source.
- Item 2: add fixed report headings for blocking findings, verified non-issues, missing validation, and residual risks, including an explicit `none found` form for each heading.
- Item 3: add a gate-evidence matrix that maps `APPROVE`, `REQUEST_CHANGES`, and `INCONCLUSIVE` to required evidence, missing-evidence wording, and one next action.

No proposal was applied. This baseline leaves the target and protocol unchanged.
