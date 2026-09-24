# omo-research Baseline, RSH-M

## Evaluation Record

- Target: `omo-orchestrator/skills/omo-research/SKILL.md`
- Protocol: `docs/reports/omo-orchestrator-skill-tuning/protocol.md`
- Scenario: `RSH-M`, the frozen median scenario for a synthetic read-only behavior investigation.
- Mode: artifact-only simulation. No executor was dispatched, no fixture was created or read, and no target prompt or protocol was changed.
- Scope boundary: this record assesses only the frozen RSH-M checklist. It makes no finding about RSH-E or another skill.

## Simulated Outcome

| Measure | Result | Reason |
| --- | --- | --- |
| Success | ○ | The sole critical item is simulated as fully met. |
| Accuracy | 100% (3.0 / 3.0) | Each frozen checklist item is simulated as `○`. |
| `tool_uses` | unavailable | No executor task result exists. The protocol prohibits estimating missing metadata. |
| `duration_ms` | unavailable | No executor task result exists. The protocol prohibits estimating missing metadata. |
| Retries | unavailable | No executor response exists from which to record repeated judgments. |

The success and accuracy values are simulated prompt-coverage scores, not empirical execution measurements.

## Checklist Scoring

| Frozen item | Score | Reason |
| --- | --- | --- |
| 1. [critical] Stays read-only and separates facts from assumptions. | ○ | The research contract says to stay read-only and to separate facts from assumptions. |
| 2. Inspects callers or dependencies when root cause matters. | ○ | The research contract explicitly requires inspection of callers and dependencies when root cause matters. |
| 3. Gives evidence-backed recommended next steps. | ○ | The research contract requires paths, symbols, evidence, and recommended next steps. |

## Evidence Basis

- `SKILL.md` frames the work as research needed before the next action, then requires exact-behavior search and nearby variants.
- Its research contract covers all RSH-M output elements: paths, symbols, evidence, facts, assumptions, and recommended next steps.
- The same contract makes caller and dependency inspection conditional on root-cause relevance, which matches the frozen item wording.
- The broad-research paragraph also preserves the read-only boundary when a research lane stalls, although RSH-M does not exercise that case.

## Unclear Points

- None in this artifact-only simulation. A fresh executor could still identify execution-time ambiguity when applying the prompt to a concrete fixture.

No critical item failed, so the protocol's failure-specific unclear-point requirement does not apply.

## Discretion Gaps

- The prompt does not define how much caller or dependency inspection is sufficient once root cause matters. An executor must choose the depth from the fixture evidence.
- The prompt does not prescribe a report template. An executor must choose how to present paths, symbols, facts, assumptions, evidence, and next steps.

## Retry Record

- Unavailable. This was a simulation, not a fresh-executor run, so no judgment was repeated and no retry count can be observed.

## Item-Linked Proposal

- No prompt change is proposed from this simulated baseline. If an empirical RSH-M run exposes inconsistency, use one focused change tied to item 2, defining the minimum caller or dependency evidence needed before a root-cause recommendation.

## Limits

- This artifact does not satisfy the protocol's fresh-executor requirement and must not be used as empirical baseline evidence or for convergence.
- A real baseline requires a fresh blank-slate executor, an empty disposable fixture, the frozen RSH-M scenario text, and captured task metadata.
