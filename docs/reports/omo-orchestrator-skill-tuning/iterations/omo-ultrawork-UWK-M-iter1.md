# OMO Ultrawork, UWK-M Iteration 1

## Protocol Metadata

- Target: `omo-orchestrator/skills/omo-ultrawork/SKILL.md`
- Scenario: `UWK-M`, median
- Execution mode: fresh blank-slate, artifact-only simulation
- Fixture boundary: no fixture files or contents were supplied. No repository mutation, service contact, credential use, or external action occurred.
- `tool_uses`: unavailable
- `duration_ms`: unavailable

## Output

### Work Ledger

| Wave | Scope | Owner | Dependency boundary | Success criteria | Evidence target | State |
|---|---|---|---|---|---|---|
| 0 | Inventory the four fixture files, their contracts, write ownership, and QA surface | coordinator | Must finish before classification or dispatch because the scenario does not identify the files or their relationships | Each file has a declared role, write owner, dependency classification, and surface or an explicit unavailable record | Fixture inventory, dependency map, and risk record | Blocked, fixture contents unavailable |
| 1 | Fixture-only work proven independent by Wave 0 | one executor per independent file or question | May run in parallel only after Wave 0 excludes shared contracts, mutable state, and same-file writes | Declared file-local behavior is complete without changing another wave's contract | Changed-file list, targeted validation result, and executor report | Not dispatched |
| 2 | Shared contract, state, or same-file work identified by Wave 0 | one named executor | Serialized after prerequisite contract evidence and any dependent Wave 1 work | Contract update and dependent fixture changes agree | Contract diff, dependent validation, and executor report | Not dispatched |
| 3 | Merge, real-surface QA, and final verification | coordinator plus independent reviewer when triggered | Begins only after Waves 1 and 2 provide concrete evidence | Every wave claim is independently checked against declared evidence | Evidence ledger, QA record, and review decision when required | Not dispatched |

### QA Plan

| Check | Surface | Pass assertion | Evidence location | Status |
|---|---|---|---|---|
| Targeted behavior check | Real fixture surface selected after Wave 0 | A user-visible or import-and-use path shows the requested behavior | Wave 3 QA record | Unavailable until the fixture identifies the surface |
| Dependency regression check | Fixture test or equivalent validation target | Dependent files accept the final shared contract | Wave 2 evidence entry | Unavailable until dependencies are identified |
| Independent final review | Required for `HEAVY` work or effects on public behavior, security, persistence, or release-facing content | One independent reviewer checks the final tree and declared evidence | Wave 3 review entry | Conditional, trigger status unavailable |

## Requirements Met

1. [critical] **partial**. The current skill requires an input inventory, recording unknowns as risks, one risk classification, and serialization of same-file, shared-state, and contract work. The artifact inventories the missing evidence and preserves those serialization boundaries, but it cannot assign `LIGHT` or `HEAVY` with a scenario-specific reason because the four files, their behavior, and their risk signals were not supplied.
2. **partial**. Every prospective independent wave has a scope, owner model, success criteria, and evidence target. No concrete independent wave can be named until Wave 0 identifies the fixture relationships.
3. **partial**. The QA plan includes real-surface QA and the skill's independent-review triggers. It cannot select the surface or decide whether review is required without fixture behavior and change-impact facts.

## Result

- Overall success: `×`
- Accuracy: `50%` (`1.5 / 3`)
- Scoring: three `partial` results score `0.5` each under the frozen protocol.

## Retries

- `0`. No judgment was redone. Missing fixture evidence prevents a concrete classification rather than requiring another attempt.

## New Unclear Points

- UWK-M item 1 [critical] is not `○`: the frozen scenario asks for a one-time risk classification but supplies no files, contracts, state model, requested behavior, or risk characteristics. Choosing a class or concrete dependency would be unsupported.
- No new prompt-wording ambiguity appeared. The remaining gap is the fixture packet, not an instruction that needs reinterpretation.

## Discretion Gaps

- `LIGHT` or `HEAVY` cannot be selected from the available evidence. The skill directs the operator to record unknowns as risks, which this artifact does.
- The real QA surface is not identified as a CLI, API, UI, library entry point, or other executable path.
- The independent-review trigger cannot be resolved because the fixture does not state whether the change affects public behavior, security, persistence, or release-facing content.

## Convergence Note

- This is the first rerun after the skill change. It cannot establish convergence because the frozen critical item remains partial, required metadata is unavailable, and no hold-out scenario has run. No prompt or protocol change is proposed in this report.
