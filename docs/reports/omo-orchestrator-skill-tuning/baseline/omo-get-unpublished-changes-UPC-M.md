# UPC-M Baseline Evaluation

## Scope

- Target: `omo-orchestrator/skills/omo-get-unpublished-changes/SKILL.md`
- Frozen scenario: UPC-M, compare a disposable package fixture against a supplied baseline snapshot and write a release-impact summary.
- Evaluation mode: static prompt-to-protocol assessment. No fresh executor result or disposable fixture was supplied for this artifact-only task.

## Frozen Item Scores

| Item | Score | Reason |
|---|---:|---|
| 1. [critical] Uses the supplied baseline and actual diff evidence, not change titles alone. | ○ | Workflow steps 1 and 2 require identifying a baseline and comparing actual diffs. The hard rules also prohibit inferring release impact from titles alone. |
| 2. Groups user-visible, internal, documentation, and test changes. | ○ | Workflow step 3 explicitly includes user-facing behavior, tests, docs, and internal refactor among the required change groups. |
| 3. Gives a version recommendation tied to stated contract impact. | ○ | Workflow step 4 requires release-impact classification, and the hard rules prohibit a version recommendation without the behavior or contract change that supports it. |

## Result

- Success: ○
- Accuracy: 100% (3.0 of 3.0 checklist points)
- Scoring basis: `○ = 1`, `partial = 0.5`, `× = 0`

## Execution Metadata

- `tool_uses`: unavailable, no executor task metadata was supplied.
- `duration_ms`: unavailable, no executor task metadata was supplied.
- Retries: unavailable, no executor self-report was supplied.

## Unclear Points

- No frozen checklist item is unclear in the target text during static assessment.
- A live executor would still need the fixture to establish how the supplied baseline snapshot is exposed and which diff command or comparison method is available. This is an execution-context detail, not a failed frozen item.

## Discretion Gaps

- The prompt lists multiple valid baseline types, including a published version, release tag, main branch, or user-provided commit. UPC-M supplies a baseline snapshot, but the target does not specify the preferred comparison mechanism for a snapshot-only fixture.
- The target asks for a recommended version bump but does not define a package ecosystem or versioning policy. An executor must apply the fixture’s stated contract impact to the available versioning convention.

## Frozen-Item Fix Proposal

- No prompt edit is proposed for this baseline. If a later frozen execution shows inconsistent snapshot handling, clarify the baseline selection wording to explicitly treat a supplied snapshot as the authoritative comparison source. This would target item 1, which requires use of the supplied baseline and actual diff evidence.
