# Evaluation Integrity

Audit the evidence behind a measurement claim. Stay read-only; do not run the benchmark, change its scorer, or approve a release. Ordinary test-case design belongs to `omo-test-design`; implementation defects use the default research flow.

## Procedure

1. State the exact claim, population, outcome, and comparison. Map the evaluated system, treatment and control, data sources, reference answers, annotators, judge prompts, thresholds, and selection process. Cite supplied records or paths; identify missing provenance explicitly.
2. Trace expected answers to a source independent of the evaluated outputs and their designer. Check whether labels and scoring rules were frozen before comparison, whether raters could see treatment identity, and whether the outcome measures the claim rather than a favorable proxy. Related judges agreeing is not independent confirmation.
3. Inspect relevant dependencies: training or prompt access to held-out answers; duplicate or overlapping sources across splits; a system generating its own labels or grading its outputs; scorer and label rules sharing an optimization target; designer-selected judges; post-result rubric or threshold tuning; unequal control exposure; and framing that reveals the desired outcome to raters or subjects. Separate demonstrated dependencies from unknown provenance. Do not invent findings for risks the evidence rules out.
4. Check comparison-environment provenance: code revision, model and settings, loaded instructions, tool schemas, fixtures, and external service responses or versions. Live MCP servers can inject changing instructions even when no tool is called. Separate the intended treatment from environmental drift; missing captures leave attribution unresolved, while a documented material difference can invalidate the comparison. Recommend a run-scoped sandbox that freezes or replays relevant inputs and disables unrelated integrations equally in both arms. Do not change the user's normal configuration. If an integration is part of the claim, retain it under controlled conditions and verify its required behavior; disabling it narrows the claim. A startup state such as `disabled` or `idle` can be settled without proving functional availability. Golden prompt parity supports only parity of the captured surface, not better task performance.
5. Choose one verdict for the stated claim:
   - `PASS`: the documented design supports the claim within its stated scope, without material unresolved dependencies.
   - `FAIL`: an observed dependency or invalid comparison defeats or materially overstates the claim.
   - `INCONCLUSIVE`: missing provenance or independent ground truth prevents a supported judgment. Missing records alone do not prove misconduct or contamination.

A measured score may describe that scorer while failing to establish broader quality. If the claim explicitly concerns only that scorer's score, assess the narrower claim on its own evidence. Statistical significance, plausible numbers, and agreement among related judges do not resolve a missing independence check.

## Return Contract

Start with `VERDICT: PASS|FAIL|INCONCLUSIVE — <claim and reason>`, selecting exactly one verdict. Cite supporting evidence. For each observed issue, give the affected inference, smallest independence repair, evidence still needed, and uncertainty remaining after repair. For an inconclusive result, name the missing records and how they could resolve the judgment. Report only supported issues; a valid design needs no invented risk list. End with the population and outcome the conclusion covers. This audit is not certification or deployment approval.

## Upstream Basis

Adapted in original wording from the evaluation-integrity approach in `code-yeongyu/oh-my-openagent` PR #7593, inspected at `0ef1af9d23` (2026-11-03). Runtime-specific tools and scorer execution are outside this mode.

Comparison-environment checks adapt PR #12256 (`a708319a0b`, `f30147198f`), inspected at `8c087588677b63ccb80affb46f2c485625f929b1` (2026-11-04). The upstream sandbox implementation is not bundled; this mode audits records and recommends repairs only.
