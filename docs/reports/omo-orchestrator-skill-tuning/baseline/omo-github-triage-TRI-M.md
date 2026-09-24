# omo-github-triage TRI-M Baseline

## Scope And Method

- Target prompt: `omo-orchestrator/skills/omo-github-triage/SKILL.md`.
- Frozen scenario: TRI-M, a synthetic reproducible regression with linked fixture evidence.
- Method: artifact-only simulation. No disposable fixture or fresh executor session was supplied, so this report evaluates the prompt's stated directions against the frozen checklist. It does not claim an executed triage response.
- Frozen protocol: `docs/reports/omo-orchestrator-skill-tuning/protocol.md`.

## Simulated Output

The prompt directs the executor to capture the report's reproduction, environment, expected behavior, actual behavior, and relevant fixture evidence. It then directs classification as a bug and priority assignment from user impact, regression likelihood, and urgency. The output contract requires evidence, missing information, and a next action, while the hard rules prohibit promising a fix before feasibility is checked.

No concrete maintainer response is included because the synthetic issue and linked fixture contents were not provided.

## Requirements Met

| Item | Score | Reason |
|---|---|---|
| 1. [critical] Classifies the report and assigns priority from stated impact evidence. | ○ | The workflow requires classification and priority assignment using user impact, regression likelihood, and urgency after capturing the report and checking related evidence. |
| 2. Gives one concrete next action and names missing evidence. | ○ | The workflow requires a next action from an explicit set, and the output contract requires missing information. |
| 3. Does not promise a fix before feasibility is checked. | ○ | A hard rule expressly prohibits promising a fix before feasibility is checked. |

## Result

- Success: ○
- Accuracy: 100% (3.0 / 3.0 checklist points)
- `tool_uses`: unavailable. No fresh executor task result exists, and this value is not estimated.
- `duration_ms`: unavailable. No fresh executor task result exists, and this value is not estimated.
- Retries: unavailable. No executor judgment was repeated because this is an artifact-only simulation.

## Unclear Points

- None for the frozen TRI-M checklist. The missing synthetic issue and fixture contents prevent a concrete response, not a checklist judgment about the prompt.

## Discretion Gaps

- The prompt leaves the exact priority level to the executor's judgment. TRI-M does not define the synthetic regression's user impact or maintainer urgency, so a concrete priority cannot be selected in this simulation.
- The prompt says to draft a maintainer response "when useful," leaving whether to include one discretionary. TRI-M asks for a response, so an executor should draft it when fixture details are available.

## Frozen-Item Fix Proposal

- No prompt change proposed. All frozen TRI-M items score ○; the unavailable measurements require a real fresh-executor run with the synthetic fixture, not a prompt edit.
