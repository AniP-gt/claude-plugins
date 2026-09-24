# OMO Start Work Baseline, STW-E

## Frozen Scenario

**Scenario:** A fixture has disagreeing TodoWrite and ledger states before a review boundary. Produce a corrective kickoff action.

**Execution mode:** Artifact-only simulation. No fixture, service, Git state, or skill file was changed.

## Output

### Corrective Kickoff Action

1. Stop at the review boundary. Do not dispatch, hand off, retry, review, complete, or edit while the current TodoWrite item and latest ledger phase entry disagree.
2. Read the current TodoWrite item and the latest ledger entry together. Retain the ledger's recorded failed attempts, validation results, evidence locations, owner, dependency status, completion criteria, final-gate state, and next exact action as historical evidence.
3. Update only the current TodoWrite item so its owner, dependency status, completion criteria or final-gate state, and next exact action match the corrective state below.
4. Append, without replacing any earlier ledger text, a corrective entry that identifies the disagreement and records the same corrective state.

### Proposed Matching State

| Field | Corrective value |
|---|---|
| Owner | Recorded fixture owner, unchanged |
| Dependency status | Review boundary pending reconciliation |
| Completion criteria / final gate | Completion blocked until TodoWrite and latest ledger entry agree; if a review gate applies, only `APPROVE` permits completion |
| Failed attempts | Preserved from the prior ledger entry |
| Validation and evidence | Preserved from the prior ledger entry, including unavailable values where no evidence exists |
| Next exact action | Compare the corrected TodoWrite item with the appended ledger entry, then begin the recorded review action only if every matching field agrees |

### Proposed Appended Ledger Entry

```markdown
## Corrective checkpoint: review-boundary reconciliation

Correction: TodoWrite and the latest ledger entry disagreed before review. Progress is blocked.
Owner: <recorded fixture owner>
Dependency status: review boundary pending reconciliation
Failed attempts: <preserved from prior entry>
Validation and evidence: <preserved from prior entry; use unavailable where absent>
Completion criteria / final gate: both views must agree; only APPROVE permits completion when review applies
Next exact action: compare this entry with the corrected TodoWrite item, then start the recorded review action only when they agree
```

Plan approval remains insufficient permission to edit. The kickoff contract, including aligned state and validation targets, must be complete first.

## Requirements Met

1. [critical] `○` Progress is explicitly blocked at the review boundary until TodoWrite and the latest ledger entry agree. The proposed remedy updates the current TodoWrite item and appends a corrective ledger checkpoint without rewriting prior history.
2. `○` The proposed state and appended entry preserve the recorded owner, failed attempts, validation results, and evidence locations rather than replacing them.
3. `○` The output states that plan approval alone does not authorize editing and requires the kickoff contract before any edit.

## Scoring

| Measure | Result |
|---|---|
| Overall success | `○` |
| Accuracy | 100% (3.0 / 3.0) |
| tool_uses | unavailable |
| duration_ms | unavailable |
| Retries | 0, no judgment was redone |

## Unclear Points

- None. The fixture does not provide literal owner, failure, validation, or evidence values, so the artifact preserves those values by reference instead of inventing them.

## Discretion Gaps

- The supplied scenario does not name the conflicting fields. The corrective entry therefore covers every field the skill requires synchronized at a phase boundary.
- The scenario does not say whether a review gate applies. The completion condition is conditional on an applicable review gate, matching the skill contract.

## Next Fix Proposal

- None. No frozen checklist item failed in this baseline execution.
