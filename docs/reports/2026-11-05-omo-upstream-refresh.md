# OMO upstream refresh — 2026-11-05

## Scope and routing

User authorized pull, autonomous adoption, commit, push, and plugin update for this session. Upstream clean dev fast-forwarded from 8c08758867 to cb7f76ecf6. Target main started at 03d3785 with an existing untracked docs/reviews/ directory, excluded from this task.

Lesson → home → target: after interruption, persisted or displayed state may disagree with live child execution → existing skill procedure → omo-guardrails/references/context-and-handoff.md. Judgment is required; no mechanical enforcement is claimed. No new hook, skill, or agent was introduced.

## Adoption decisions

Adopt manual state reconciliation from #12343 (stale Stop admission), #12268 (paused/lost child recovery and foreign-owner protection), and #12113 (snapshot on reconnect; inspected in the previous refresh but deferred then). Fresh task identity/workspace/ownership and deliverable evidence precede dependency release. Acknowledged resume is not completion. Preserve artifacts, mark missing proof INCONCLUSIVE, and allow independent work.

Do not port the runtime scheduler, automatic recovery, memory shutdown trackers (#11671), memory revocation, sandbox attestation, computer display-awake support, thread chain-limit removal, generated bundles, or model-specific directive variants. Those require absent engine APIs or have no portable plugin behavior. This release updates instructions only; no script changes.

## Iteration 0

Description/body consistency checked: safe recoverable delegated work and context handoff cover resume reconciliation. Parent reference label updated for discoverability. Baseline executor not run; no before/after accuracy gain claimed.

## Fixed evaluation criteria

Three simulated scenarios, four criteria each: critical dependency decision, cite state evidence, permit unaffected independent work, and avoid invented APIs/automatic recovery claims. A: fresh matching completion plus current verified artifact permits proceeding. B: running widget but live paused child, parent Stop released and resume accepted without resulting evidence must keep dependencies blocked. C: another live session owns child after failed resume; no takeover, kill, or duplicate work.

Holdout D fixed before round 2: ledger complete, host unavailable, artifact exists but verification predates its changed input; keep dependent work blocked and mark missing proof INCONCLUSIVE, permit independent documentation work, avoid invented recovery.

## Iteration 1

Added one resume procedure satisfying critical A/B/C decisions, especially B's acceptance-versus-completion distinction and C's live ownership boundary. Reference 63 → 74 lines; parent skill remains under 500 lines. Fresh blank-slate executor applied the procedure to supplied facts without external effects.

A/B/C: success ○, 4/4 each (100%); retries 0; one shared read tool call. Overall agent duration unavailable; command runtime is not substituted. No new instruction ambiguity. Missing concrete host/task IDs and retry scheduling remain scenario-specific operational choices; no invented API or infinite retry was recommended.

## Iteration 2 and holdout

Fresh executor read the parent and reference. B/C/D each met 4/4 (100%, success). A conservatively requested omitted dependency/deliverable mapping before proceeding: critical decision partial, remaining criteria met (3.5/4, 87.5%, failure under the fixed binary rule). This exposes a scenario omission, not a new instruction ambiguity; no text was changed. The missing A fields were explicitly supplied in a third fresh run; its result is recorded below. One shared read call, retries 0, duration unavailable. Holdout D correctly stayed INCONCLUSIVE and permitted independent documentation work.

## Iteration 3

Fresh executor correctly decided A proceed, B/D blocked, and C no takeover. Caller scoring: all four scenarios 4/4 (100%, success), one shared read call, retries 0, duration unavailable. No text revision. Executor again noted host-specific recovery timing; this is the same discretion gap as round 1, not a new defect. Stop at resource cutoff: no baseline gain or full quantitative convergence is claimed. Scenario facts now explicitly provide observation time and matching dependency/expected-artifact mapping where available; this correction is disclosed rather than treated as an unchanged benchmark. Original strict quantitative convergence cannot be claimed across the changed input.

## Validation

Plugin and marketplace validation passed. Existing directory-submission diagnostics: missing license and icon; marketplace warning: ignored metadata.homepage. No new license decision inferred. git diff --check passed. Both manifests 3.10.0; descriptions 148 characters each (maximum 200). No tests pin prose wording; instruction execution is evaluated through fresh agents.

Independent security-check followed .claude/agents/security-check.md: HIGH 0, MEDIUM 0, LOW 0. Source scripts unchanged.

## Release preparation

Commit style: Japanese semantic subjects, following 03d3785 and 6a62341. One atomic unit: guardrail procedure, discovery label, synchronized release metadata, README, and this evaluation record. Existing untracked docs/reviews/ excluded. origin/main is one commit behind the starting HEAD (03d3785); the authorized normal push includes that pre-existing commit as well.
