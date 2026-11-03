# OMO upstream refresh — 2026-11-03

## Scope and routing

- User authorized upstream pull, autonomous updates, commit, push, and installed Claude plugin update for this session.
- Upstream clean checkout fast-forwarded from `7c37db199c` to `0ef1af9d23` on `dev`.
- Lesson: measurement claims need independent evidence and explicit uncertainty → existing skill procedure → `omo-research/modes/eval-integrity/MODE.md`. No new hook, agent, or top-level skill.
- Baseline `claude-plugins`: clean `main`, `c08e2bc`, aligned with upstream. No pre-existing edits.

## Adoption decisions

Compared upstream file changes and recent history over the pulled range. PR #7593's evaluation-integrity method is reusable without the upstream runtime: integrate it as a read-only research mode, using original wording and a direct mode entry. Version: 3.6.1 → 3.7.0 in plugin, marketplace, and README.

- #7662 suppresses unchanged `task_output` snapshots in Senpi. No equivalent task-output server exists in this plugin; do not claim a runtime guard by adding prose. Existing bounded follow-up research guidance remains sufficient.
- #12040 fixes SVG `foreignObject` parsing in the upstream `fact verify` implementation. This repository has no corresponding tokenizer; do not copy an unrelated parser or claim the fix here.
- Native device bootstrap/signature checks, memory sync/path hardening, designated model fallback, telemetry, generated bundles, and platform releases depend on upstream packages absent here. They are not transferable plugin changes.

## Empirical method and fixed criteria

Executed supplied scenarios with fresh agents, read-only and without external reviewers, commits, posts, or file edits. The first post-change round receives the checklist as required by the empirical skill's normal launch contract. The second receives only scenario facts to reduce answer priming. Scores are caller judgments, not independent ground truth or evidence of a general performance improvement.

Four criteria per baseline/A/B scenario, fixed before execution:

- A: [critical] reject broad quality claim from circular judging; distinguish scorer score from quality; propose frozen independent held-out external labels; explain evidence and residual uncertainty.
- B: [critical] accept documented validity in scope without invented findings; identify evidence; retain population limit; avoid certification.
- Post-change A/B additionally must route to the mode and use its correct verdict; this is part of the critical requirement, not a retroactive baseline penalty.
- Holdout C, fixed before receiving its output: [critical] INCONCLUSIVE when provenance is absent; do not assert contamination as fact; request split/label/judge records; keep conclusion limited to the claim and avoid deployment approval.

## Iteration 0 — baseline and structural consistency

Existing research description and body are consistent for code/library research, but omit evaluation-integrity procedure and triggers. A/B each satisfy 4/4 baseline criteria (100%, success). Executor reports no blocking ambiguity, but supplies independence, post-result tuning, and acceptance criteria from discretion and visible checklist. Retries: 0; one read tool call; overall duration unavailable.

Fix targets the A critical judgment and B false-positive criterion: explicit PASS/FAIL/INCONCLUSIVE rules, provenance mapping, relevant dependence checks, and a bounded return contract. Parent skill: 49 → 50 lines; new mode: 23 lines. Parent description stays under 1,024 characters; skill body stays under 500 lines.

## Iteration 1

Fresh executor followed the new mode: A FAIL, B PASS; each 4/4 (100%, success), retries 0. No new instruction ambiguity; missing scenario detail was left unknown. The visible checklist primes verdict selection, so this round establishes instruction following only. Three `functions.exec` calls contain two file reads and two clock calls. Clock values were inconsistent; total duration is unavailable.

## Iteration 2 and holdout

Another fresh executor received facts without the checklist: A FAIL, B PASS, C INCONCLUSIVE; each 4/4 (100%, success), retries 0. C explicitly avoids treating missing provenance as contamination and requests the relevant records. No new instruction ambiguity; judgments remain bounded to supplied design facts. Three `functions.exec` calls contain two file reads and two clock calls. Measured interval: 4 seconds, but it excludes initial reading and is not total duration.

No text changes between rounds 1 and 2. Qualitative clear rounds: 2; accuracy change: 0 points; holdout drop: 0 points. Tool-call counts are executor self-reports because Agent metadata exposes no usage counts. Full timing stability cannot be established; stop at resource cutoff with the qualitative result, not a claim of formal convergence. No general reliability improvement is inferred from these synthetic scenarios or the already-perfect baseline scores.

## Validation and security

- `claude plugin validate ./omo-orchestrator`: passed normal validation. Directory submission profile separately reports existing missing license and icon; these do not fail the normal load check.
- `claude plugin validate .`: passed with existing ignored `metadata.homepage` warning.
- `git diff --check`: passed.
- `node --test omo-orchestrator/hooks/*.test.mjs omo-orchestrator/scripts/*.test.mjs`: 130 passed, 0 failed, exit 0. Repeated once to extract the summary after indexed output omitted it; no additional tests added for this instruction-only feature.
- Fresh `security-check` executor followed `.claude/agents/security-check.md`, inspected diff, new mode, existing scripts/hooks: HIGH 0, MEDIUM 0, LOW 0. No scripts or permissions changed.

## Delivery

One atomic feature commit: mode, routing, version synchronization, README usage, and this evaluation record. Commit style follows recent Japanese semantic subjects (`fix(omo-orchestrator): ... (3.6.1)`, `feat(omo-orchestrator): ... (3.6.0)`). Push and installed-plugin update follow successful verification; exact completion is reported in the session.
