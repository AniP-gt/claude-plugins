# OMO upstream refresh / 2026-10-21

## Scope and decisions

User authorization covers upstream pull, portable improvements, empirical tuning, commit, push and installed Claude plugin updates without interview. Upstream `dev` fast-forwarded from `048883f206` to `c00a05835a6bb11944976263b4e945972adce538` with `git pull --ff-only`.

The local working tree already contained the frontend/research refresh and its 2026-10-20 report, plus a rigorous-plan-review convergence change. These existing changes were preserved, inspected and included in this completion; they are not represented as newly authored in this session. The previous report is historical evidence, not proof that this session began clean.

Routing before edits: decorative stripes and legitimate exceptions belong in the existing frontend skill/aesthetics reference; truthful visual research evidence belongs in the existing ultraresearch skill; review progress and blocker eligibility belong in the existing rigorous-review reference. No new hook, skill or agent was created.

The complete shared-skills diff from `5f6b6bbb3e` to the pulled tip changes git-master's trigger description and ulw-plan's convergence contract. The latest pull range `048883f206..c00a05835a` has no shared-skills changes. The plan adaptation retains this plugin's three-pass maximum while adopting stable blocker IDs and stopping rejection without progress. Upstream removes the fixed cap while allowing new blockers, which does not establish a finite bound; that removal is not ported. A broad mandatory Git trigger is not copied: the existing local skill already handles commit/history work and no additional runtime enforcement is introduced.

Senpi onboarding now selects memory candidates before writing through its native RPC tools. Its memory writer, desktop scan, session digest and consent UI have no matching runtime in this plugin, so these changes are excluded together with telemetry, model catalogs, RPC lifecycle and generated Codex hooks. Existing frontend/research sources and exclusions remain documented in the 2026-10-20 report.

## Static validation and size

- Manifest, marketplace and README synchronize at 1.52.0, superseding the already installed but uncommitted 1.51.0 snapshot.
- `git diff --check`: passed.
- `claude plugin validate ./omo-orchestrator`: passed, with missing optional directory icon warning.
- `claude plugin validate .`: passed, with existing marketplace metadata warning.
- `node --test` for the four hook test files and `scripts/impact.test.mjs`: 74 passed, 0 failed.
- Frontend SKILL.md: 114 to 118 lines; aesthetics: 65 to 65; ultraresearch SKILL.md: 115 to 126; rigorous-review reference: 93 to 98. Skills remain below 500 lines; references remain below the 100-line TOC threshold. Manifest descriptions both remain 148 characters.
- Description/body consistency: these changes refine existing frontend, exhaustive research and plan-review procedures without adding triggers.

## Security check

An independent `security_check` executor followed `.claude/agents/security-check.md` read-only. HIGH 0, MEDIUM 0, LOW 0. All five prescribed categories passed static inspection across 14 scripts/hooks files; none are Python or shell. `git diff --exit-code -- omo-orchestrator/scripts omo-orchestrator/hooks` confirms no runtime changes. Prompt-boundary inspection confirmed no new write authorization, invented measurement permission, or unobserved-rendering claim. This is static security evidence, not exploit execution.

## Empirical protocol

Fresh blank-slate executors run concrete briefs/report snippets, without editing, browsing, installations, subagents, commits or pushes. Checklists are fixed before dispatch. The original baseline and iteration 1 are preserved in the 2026-10-20 report. This session supplies independent rounds 2 and 3, including a holdout and the pre-existing plan change.

- A [critical]: reject decorative edge-stripe equivalents, preserve functional validation/focus treatments and screenshot-required warning edges.
- B [critical]: preserve bench.csv values (2026-10-20, A 40 ms/120 MiB, B 25 ms/210 MiB), units and provenance; give a quantitative visual with accessible description and explicit unrendered handoff; perform no writes.
- C [critical]: architecture.md revision abc contains only browser to gateway to database; produce structural source without invented quantities, reject logo/zero-height/raw-source rendering evidence, retain read-only ownership and rendering limitation.
- D holdout [critical]: path.md revision d12 contains producer to queue to worker; reject zero-width and decorative presentation figures as evidence, preserve screenshot-required warning stripe, give provenance/accessibility and unrendered handoff without invented quantities.
- E [critical]: maintain stable blocker IDs, reject speculative scope expansion, stop a rejection with no ledger progress and never exceed the three-pass maximum even for a genuine new critical blocker.

Full tool-use and duration telemetry is not provided by the collaboration API. Executor-observed read counts are descriptive only. No strict quantitative convergence claim will be made without the required variation measurements.

## Iterations 2 and 3 results

Both fresh executors returned concrete A–E outputs against the unchanged prompts. No additional prompt correction was justified by these fixtures.

| Scenario | Round 2 | Round 3 | Output observed |
|---|---|---|---|
| A | Pass, 100% | Pass, 100% | Accent heading replaces decorative blue band; pseudo/shadow/gradient substitutes rejected; invalid border, focus ring and screenshot-required orange stripe preserved |
| B | Pass, 100% | Pass, 100% | Exact 40/120 and 25/210 table; separately labeled ms and MiB horizontal panels, zero baselines, caption, accessible values, provenance and NOT RENDERED handoff |
| C | Pass, 100% | Pass, 100% | browser to gateway to database Mermaid; abc provenance, accessible relationships; logo/height-zero/raw-source rendering claims rejected |
| D holdout | Pass, 100% | Pass, 100% | producer to queue to worker Mermaid; d12 provenance; width-zero and presentation decoration rejected; warning reference retained |
| E | Pass, 100% | Pass, 100% | Stable closed BL-001 retained; no-progress rejection stops at pass 2; separate new-critical-blocker case stops at pass 3 without implementation authorization |

Scoring concerns the fixed output-contract checklist, not actual implementation or rendered UI. All critical requirements were met. The charts/diagrams were not rendered, supplied CSV/Markdown fixture files were not independently inspected, and no screenshot comparison or benchmark was performed. Both executors explicitly state those limits.

Representative returned source for C: `flowchart LR; browser --> gateway; gateway --> database`. D substitutes `producer --> queue; queue --> worker`. B's rendering handoff requests SVG panels embedded beside the claim, with source/date, readable labels, nonzero dimensions and accessible descriptions checked in the destination by a separately authorized owner.

New target-instruction ambiguity: none requiring a correction. Discretion gaps: actual tokens, screenshot dimensions, renderer/destination and benchmark methodology are intentionally unspecified. E supplies no open blocker behind its pass-2 rejection; both executors report that inconsistency rather than inventing a blocker or overriding rejection. Pass-3 technical details must come from real evidence, not the synthetic fixture.

Round 2 self-reports 9 underlying calls, zero scenario retries and a 30-second observed interval excluding recording/final reply; these are not API usage totals. Round 3 self-reports 3 exec calls containing 5 shell invocations plus one message, zero behavioral retries and one reread for truncated text; total duration unavailable. Round 2 wrote a local ignored evidence artifact despite its read-only assignment; target files were unchanged. This is an executor compliance limitation, not evidence that the research skill authorized writes. Round 3 wrote nothing. The report captures their outputs without depending on ignored artifacts for published evidence.

Two independent unchanged-prompt rounds and the holdout found no new content defect. Full convergence thresholds for duration/tool variation cannot be scored from available telemetry, so this is a bounded empirical acceptance with that limitation, not a claim of formal convergence. No rendered product is delivered by this prompt-only update.
