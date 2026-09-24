# omo-plan PLN-E Baseline

## Freeze Record

- Skill: `omo-orchestrator/skills/omo-plan/SKILL.md`
- Frozen scenario: `PLN-E`
- Scenario: An ambiguous request has a reversible default and one lasting public-contract choice. Produce the decision route.
- Execution mode: artifact-only simulation. No fixture, product repository, external service, credential, transcript, runtime command, or Git state was accessed or changed.
- Metadata: `tool_uses` unavailable. `duration_ms` unavailable. The protocol requires runner metadata, and no runner metadata was supplied for this artifact-only simulation.

## Simulated Decision Route

Planning mode is active. This route does not edit product code, dispatch implementation, or run implementation commands.

### Evidence And Intent Verdict

The frozen scenario establishes two material facts: one choice is reversible, and one choice creates a lasting public contract. It supplies no repository packet, existing contract, consumer inventory, or implementation surface. That is sufficient to route the decisions but not to write a decision-complete final plan.

Intent verdict: `UNCLEAR`.

### Selected Reversible Default

Use the smallest reversible internal configuration or behavior that does not expose a new public field, endpoint, file format, or compatibility promise. This is the default because it can be replaced later without breaking consumers, while the requested public-contract choice cannot be safely inferred.

### Owner Decision

What exact public contract should consumers receive for this feature, including its stable name and shape?

This is the only owner question. Its answer creates a lasting consumer-facing commitment, so a reversible default would not be appropriate.

### Later-Plan QA Contract

After the owner answers and before implementation starts, the final plan must include these executable QA assertions:

1. Happy path: with a deterministic fixture or request that uses the approved public contract, run the named test or concrete surface steps and assert the consumer receives the approved name and shape.
2. Edge path: with a fixture or request that omits, misspells, or uses an unsupported version of that contract, run the same named test or concrete surface steps and assert the defined rejection, fallback, or compatibility result.
3. Evidence: save the test output, diagnostics, or inspected surface result at the final-plan evidence location for the task.

### Approval State

No approval brief is presented yet because the public-contract decision remains open. No final executable plan is produced. Approval, once requested and granted, writes the plan only. It does not authorize implementation. Implementation and runtime execution remain separate, user-directed workflows.

## Frozen Checklist Scores

| Item | Result | Reason |
| --- | --- | --- |
| PLN-E.1 `[critical]` Selects and explains the reversible default while asking one precise owner question for the lasting choice. | ○ | The route chooses a minimal internal, non-public default, explains why reversibility matters, and asks one exact question about the stable public contract. |
| PLN-E.2 Keeps implementation and runtime execution out of planning mode. | ○ | The route explicitly excludes edits, implementation dispatch, runtime commands, and final-plan execution from planning mode. |
| PLN-E.3 Defines executable happy and edge QA assertions for the later plan. | ○ | The route requires deterministic fixtures or requests, named tests or concrete surface steps, explicit happy and edge assertions, and saved evidence. |

## Result

- Success: ○
- Accuracy: 100% (3.0 / 3 checklist points)
- Retries: unavailable. No executor retry metadata was supplied for this artifact-only simulation.

## Unclear Points

- None observed in the frozen scenario for this simulation. The absent repository packet limits final-plan detail, but it does not block the required decision route.

## Discretion Gaps

- The scenario does not identify the product domain, so the reversible default is stated as a constraint-based internal choice rather than a domain-specific behavior.
- The scenario does not define the approved error or compatibility behavior for the edge assertion. The later plan must set that behavior after the public-contract owner decision.

## Proposed Fix

- No prompt change proposed. Frozen item `PLN-E.1` is satisfied because the current skill already distinguishes reversible defaults from lasting owner decisions. Re-evaluate only if a fresh executor fails to make that distinction.
