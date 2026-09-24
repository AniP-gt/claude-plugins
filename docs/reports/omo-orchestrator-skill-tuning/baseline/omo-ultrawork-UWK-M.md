# OMO Ultrawork Baseline, UWK-M

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
| 0 | Identify the four fixture files, their contracts, and write ownership | coordinator | Must finish before dispatch because the scenario does not name files or relationships | Each file has a declared role, write owner, and dependency classification | Fixture inventory and dependency map | Blocked, fixture contents unavailable |
| 1 | Independent fixture-only work identified by Wave 0 | one executor per independent file or question | May run in parallel only after Wave 0 proves no shared contract, mutable state, or same-file write | Declared file-local behavior is complete without changing another wave's contract | Changed-file list, targeted validation result, and executor report | Not dispatched |
| 2 | Shared contract or state change identified by Wave 0 | one named executor | Serialized after all prerequisite contract evidence; no concurrent same-file writes | Contract update and all dependent fixture changes agree | Contract diff, dependent validation, and executor report | Not dispatched |
| 3 | Merge and final verification | coordinator plus independent reviewer when triggered | Begins only after Waves 1 and 2 provide concrete evidence | Every wave claim is independently checked against its declared evidence | Evidence ledger, real-surface QA record, and review decision when required | Not dispatched |

### QA Plan

| Check | Surface | Pass assertion | Evidence location | Status |
|---|---|---|---|---|
| Targeted behavior check | Real fixture surface selected after Wave 0 | A user-visible or import-and-use path shows the requested behavior | Wave 3 QA record | Unavailable until the fixture identifies the surface |
| Dependency regression check | Fixture test or equivalent validation target | Dependent files accept the final shared contract | Wave 2 evidence entry | Unavailable until dependencies are identified |
| Independent final review | Required only if Wave 0 classifies the work `HEAVY`, or the change affects public behavior, security, persistence, or release-facing content | One independent reviewer checks the final tree and declared evidence | Wave 3 review entry | Conditional, trigger status unavailable |

## Requirements Met

1. [critical] **partial**. The artifact serializes discovery before dispatch and explicitly serializes same-file writes, shared state, and contract work. It cannot classify risk once with a scenario-specific reason because the synthetic files, requested behavior, and risk signals were not supplied.
2. **partial**. Every prospective independent wave has a scope, owner model, success criteria, and evidence target. No concrete independent wave can be named without the fixture inventory.
3. **partial**. The QA plan requires real-surface QA and defines the independent-review triggers from the skill. It cannot select the actual surface or decide whether review is required without the fixture and change characteristics.

## Result

- Overall success: `×`
- Accuracy: `50%` (`1.5 / 3`)
- Scoring: three `partial` results score `0.5` each.

## Unclear Points

- UWK-M item 1 [critical] failed to reach `○`: the scenario requires a one-time risk classification and dependency serialization, but supplies neither the four files nor their contracts, state, or risk characteristics. Naming a risk class or concrete dependency would be invented rather than evidence-backed.
- The phrase "synthetic four-file task" does not state which work is independent, which work is dependent, or the real surface to test.

## Discretion Gaps

- The skill says to classify `LIGHT` or `HEAVY` from risk, but the scenario gives no risk evidence. This report did not select either classification.
- The skill requires real-surface QA, but the scenario does not identify a CLI, API, UI, library entry point, or other executable surface.
- The skill makes independent review conditional on `HEAVY` work or specified impact. The trigger cannot be resolved without the missing fixture facts.

## Retries

- `0`. No judgment was redone. The missing fixture evidence blocks a concrete classification rather than calling for a retry.

## Fix Proposal

- Frozen UWK-M item 1: no prompt change proposed from this baseline. The gap is in the fixed scenario packet, and the freeze rule prohibits changing it during baseline execution.
