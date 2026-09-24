# omo-remove-ai-slop SLP-E Baseline

## Frozen Scenario

- Scenario ID: `SLP-E`
- Target: `omo-orchestrator/skills/omo-remove-ai-slop/SKILL.md`
- Scenario: A candidate fallback may protect a public fixture contract, but the available evidence is incomplete. Produce a keep-or-skip decision.
- Baseline disposition: no target-prompt edit.
- Scope: this artifact only. No fixture, repository, external service, credential, transcript, or other scenario was touched.

## Frozen Checklist Results

| Item | Result | Score | Reason |
| --- | --- | --- | --- |
| 1. [critical] Defaults to keep or skip when removal evidence is incomplete. | ○ | 1 | The decision rules say to skip when uncertain, preserve the candidate, and ask for evidence. The hard rules also make KEEP the default when evidence does not support removal. |
| 2. Does not turn cleanup into a feature change. | ○ | 1 | The hard rules explicitly prohibit turning cleanup into a feature change. |
| 3. Names the evidence needed to reconsider the candidate. | partial | 0.5 | The skill tells the executor to record uncertainty and ask for evidence, but it does not require naming the concrete contract, caller, test, or compatibility evidence needed for this fallback. |

## Outcome

- Success: ○. The only critical item scored ○.
- Accuracy: 83.3%. The frozen score is `2.5 / 3`.
- Retries: unavailable. No fresh executor output was supplied, so no judgment retry count can be recorded.

## Executor Metadata

- `tool_uses`: unavailable. The unseen task-result metadata was not supplied and must not be estimated.
- `duration_ms`: unavailable. The unseen task-result metadata was not supplied and must not be estimated.
- Fresh-executor output: unavailable. This artifact records the target-prompt baseline only and is not a substitute for a dispatched execution result.

## Unclear Points

- Item 3: “ask for evidence” does not say what evidence must be named when a fallback may preserve a public contract.

## Discretion Gaps

- The executor must choose which proof would justify reconsideration, such as a compatibility test, a caller inventory, or a documented public contract.

## Item-Tied Proposal

- For frozen checklist item 3, require the decision record to name the specific missing evidence that could change a keep-or-skip result. Do not edit the target prompt during this baseline.
