# omo-remove-deadcode baseline, DCD-E

## Frozen scenario

**Edge, DCD-E:** A fixture export has no text references but appears in plugin metadata. Produce a classification report.

1. [critical] Marks the candidate keep, needs migration, or inconclusive rather than deleting it.
2. Does not assume text-search absence proves runtime absence.
3. Names the missing registration evidence.

## Frozen result

| Item | Result | Reason |
|---|---|---|
| 1. [critical] Classification instead of deletion | ○ | The workflow requires every candidate to be classified as safe delete, keep, needs migration, or inconclusive. Plugin metadata prevents a safe-delete conclusion without further proof. |
| 2. Text-search absence is not runtime proof | ○ | The hard rules explicitly reject this inference when plugin metadata or other runtime registration points exist. |
| 3. Missing registration evidence named | ○ | The workflow requires checking runtime registration points. The classification report must identify the needed metadata or registration check before any deletion decision. |

- Success: ○
- Accuracy: 100% (3.0 / 3)
- Tool uses: unavailable, executor task metadata was not supplied.
- Duration: unavailable, executor task metadata was not supplied.
- Unseen metadata: unavailable.
- Retries: unavailable, executor self-report was not supplied.

## Unclear Points

- None. The skill clearly says that plugin metadata makes absent text references insufficient for deletion.

## Discretion Gaps

- The skill does not prescribe the exact artifact format for a classification report. The executor must choose how to present the candidate, metadata evidence, classification, and next check.
- The skill names runtime registration points but does not state which metadata field or loader path should be inspected first. The fixture determines that order.

## Item-tied proposal

- For frozen item 3, add a classification-report template that names the candidate, metadata location, registration evidence checked, classification, and next required check. This would remove presentation discretion without weakening the rule against deletion under inconclusive reachability.
