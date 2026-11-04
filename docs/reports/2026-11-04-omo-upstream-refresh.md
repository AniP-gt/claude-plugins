# OMO upstream refresh — 2026-11-04

## Scope and routing

- User authorized autonomous upstream pull, plugin improvement, commit, push, and installed plugin update without questions.
- Upstream clean `dev` fast-forwarded from `0ef1af9d2392697f257067e7c7d531bcdd83d24e` to `8c087588677b63ccb80affb46f2c485625f929b1`.
- Target started clean on `main`, aligned with `origin/main`.
- Lesson: external injected instructions and tool availability affect comparison validity → existing skill procedure → `omo-research/modes/eval-integrity/MODE.md`. No new hook, agent, or skill.

## Adoption decisions

Adopt upstream #12256 (`a708319a0b`, `f30147198f`) in original wording as read-only evaluation guidance. Inspect code/model/instruction/tool/environment provenance; isolate unrelated integrations equally in a run-scoped sandbox; preserve required capabilities; distinguish startup settlement from functional evidence. Golden parity establishes only captured-surface parity. No sandbox implementation or runtime is bundled. Version 3.7.0 → 3.8.0 in plugin and marketplace, with README release paragraph.

Deferred: #12113 (`2096d16d34`) reconnect snapshots may inform a future handoff-state reconciliation change, but constitute a separate procedure requiring its own scenarios. Recovery DAG install/wait separation (`7d42470a26`) requires an absent scheduler. Architect write permissions (#12239) would change this plugin's advisor/implementer boundary. Model defaults/reverts, memory sync, liveness/fake-timer fixes, and generated bundles depend on absent runtimes and were not copied.

## Empirical method and fixed criteria

Fresh executors read the mode and audit supplied scenarios without edits, network calls, delegation, or running benchmarks. The first post-change round receives the fixed checklist; the second receives facts only. These are caller-scored synthetic checks of instruction application, not independent ground truth or evidence of broad quality improvement.

Four criteria per scenario: the critical judgment below, evidence citation, bounded claim scope with minimal repair only when needed, and read-only execution.

- A [critical]: reject attributing better tool selection to a prompt when remote MCP instructions changed too; distinguish environmental drift from treatment.
- B [critical]: accept documented offline captured-golden parity with unrelated MCP disabled equally in sandbox-only configuration; do not require enabling unrelated services or changing normal user configuration.
- C [critical]: reject live-search quality evidence with the required search MCP disabled; `settled` does not establish functionality.
- Holdout D, fixed before execution: latency A/B with missing remote version captures but no observed drift → [critical] `INCONCLUSIVE`, not proven drift or misconduct; name needed captures, bound attribution, remain read-only.

## Iteration 0

Description/body consistency: the existing evaluation-integrity trigger covers this topic, but its procedure omitted runtime environment provenance. Baseline A/B/C each passed 4/4 (100%, success). The executor supplied the MCP environmental and startup/functionality distinctions from discretion and scenario facts. Retries 0; one exec call. Full executor duration unavailable.

## Iteration 1

Minimum fix satisfies A's environmental attribution criterion, B's equal sandbox isolation criterion, and C's required-functionality criterion. Added one procedure step and upstream source paragraph. MODE.md: 23 → 26 lines; parent SKILL.md unchanged at 50 lines, below 500-line budget.

| Scenario | Success | Accuracy | Tool calls | Duration | Retries |
|---|---|---|---|---|---|
| A | ○ | 100% | 1 shared read | unavailable | 0 |
| B | ○ | 100% | 1 shared read | unavailable | 0 |
| C | ○ | 100% | 1 shared read | unavailable | 0 |

No new instructional ambiguity. Executor noted absent concrete run IDs and population records in the synthetic facts; these are evidence limits, not instruction defects. No text revision needed. Full executor timing is unavailable; the reported ~0.3s read-command time is not substituted for it.

## Iteration 2 and holdout

No text changes. A/B/C again passed 4/4 each (100%, success); holdout D passed 4/4 (100%, success), selecting `INCONCLUSIVE` for missing captures without asserting actual drift. One shared read call; retries 0; duration unavailable. No new instructional ambiguity. Claim scoping and known-versus-unknown differences remained task judgments rather than missing procedure.

Two consecutive qualitatively clear post-change rounds; accuracy improvement 0 points, tool-count variation 0%, holdout drop 0 points. Timing variation cannot be assessed because executor duration metadata is unavailable. Stop at resource cutoff with this limitation recorded, rather than claiming all quantitative convergence conditions were met. Baseline already passed, so no measured accuracy gain is claimed.

## Validation

- `claude plugin validate ./omo-orchestrator`: passed. Existing directory-submission diagnostics: missing license and icon. No licensing decision inferred from this task.
- `claude plugin validate .`: passed; existing unknown `metadata.homepage` warning.
- README semantic validation: passed.
- `git diff --check`: passed.
- Version synchronization and both descriptions ≤200 characters: passed.
- Independent security-check agent followed `.claude/agents/security-check.md`: HIGH 0, MEDIUM 0, LOW 0; no new execution/configuration authority or contradiction found. No scripts changed.
