# CAS-M Baseline: omo-coding-agent-sessions

## Scope

- Target prompt: `omo-orchestrator/skills/omo-coding-agent-sessions/SKILL.md`
- Frozen scenario: CAS-M, one synthetic parent session and one linked child, with a redacted evidence table answering whether the child completed a named task.
- Evaluation mode: artifact-only simulation. No disposable store, transcript artifacts, or task-result metadata was supplied or inspected.
- Prompt and protocol mutation: none.

## Simulated Output Shape

The prompt requires an evidence table containing source paths, parent and child session IDs, relationship evidence, inspection state, separated transcript evidence and accounting metadata, redactions, confidence, and a direct answer or an explicit gap. It also requires inspecting a linked child before concluding whether delegated work was completed.

No completion answer is claimed here because the synthetic child transcript and named task were not provided to this artifact-only simulation.

## Requirements Met

| Frozen item | Score | Reason |
| --- | --- | --- |
| 1. [critical] Separates transcript evidence from accounting metadata and inspects the linked child. | ○ | The Evidence Rules explicitly distinguish transcript evidence from accounting metadata. The workflow requires child linkage inspection, and the Child Session Contract requires inspecting a child transcript when delegated work may contain the answer. |
| 2. Lists source paths, session IDs, linkage evidence, and inspection state. | ○ | The Evidence Rules and Output Contract require session IDs, source paths, parent or child relationship, supporting evidence, and inspection state for each inspected session. |
| 3. Redacts synthetic secret-like text and states an evidence-backed answer or gap. | ○ | The prompt requires redaction of credentials, tokens, and private content, minimum necessary excerpts, and a direct answer only when raw transcript evidence supports it. Otherwise it requires stating what is unknown and the exact next artifact or decision needed. |

## Result

- Success: ○
- Accuracy: 100% (3.0 / 3.0)
- `tool_uses`: unavailable. This artifact-only simulation has no task-result metadata; no estimate was made.
- `duration_ms`: unavailable. This artifact-only simulation has no task-result metadata; no estimate was made.
- Retries: 0. No judgment was redone.

## Unclear Points

- None found for the frozen CAS-M checklist. The prompt specifies both the evidence categories and the required linked-child inspection before a completion conclusion.

## Discretion Gaps

- The named task, synthetic paths, session IDs, and transcript contents are not supplied in this artifact-only simulation. A real executor would need those fixture facts to produce the requested evidence table and answer the completion question.
- The prompt leaves the table's visual column order open. That does not affect any frozen checklist item because the required fields are explicitly named.

## Frozen-Item Fix Proposal

- No prompt change proposed. All frozen CAS-M items score ○ in this baseline. If a later executor fails item 1, clarify the item by adding an explicit output-table row for each linked child with `inspection state` and separate `transcript evidence` and `accounting metadata` cells. This is a conditional later-iteration proposal only, not a baseline change.
