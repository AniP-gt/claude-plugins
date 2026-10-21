# OMO upstream refresh / 2026-10-20

## Scope and routing

The user authorized upstream pull, portable Claude Code improvements, empirical tuning, commit, push, and installed plugin updates without interview. Both repositories started clean. Upstream `dev` fast-forwarded from `3ed403b600` to `5f6b6bbb3e`; the local plugin started at 1.50.0.

- Decorative stripe guidance and legitimate exceptions → existing frontend skill and aesthetics reference.
- Evidence-based visual selection, provenance, and rendering status → existing ultraresearch skill.
- No new hook, skill, agent, script, runtime, dependency, or credential behavior.

Upstream sources: `400f6aeda455c52666c3a1ed274729be3ce9958c` and `0041fce4b6`, `packages/shared-skills/skills/frontend/{SKILL.md,references/design/README.md}`; `f4cdb2b17e8ecc76ffacfbaf07a5f28e94f49cef`, `671655d449`, `005a42026c`, `packages/shared-skills/skills/ulw-research/references/{report-visualization.md,report-gates.md}`.

Excluded: native thread/RPC lifecycle, telemetry, memory infrastructure, model catalogs, browser daemons, and the upstream accent-stripe linter. Those require runtime components absent here. The local research skill remains read-only: visual specifications and source may be returned in the reply, while writing/rendering assets belongs to a separately authorized writable owner. A quantitative chart is required only when quantitative evidence exists; structural findings use a diagram. User-designated visual references take precedence over generic styling guidance.

## Fixed evaluation protocol

The evaluated artifact is an implementer brief or research report excerpt, not a rendered UI. Executors read the target skills independently and produce concrete output using supplied facts. They may not edit files, install tools, browse, launch agents, commit, or push. No runtime parser, browser renderer, or visual linter is introduced or claimed tested.

Before editing, the following checklist was fixed:

- A, rounded feature card: [critical] replace a decorative accent stripe before implementation; catch pseudo-element, inset-shadow and hard-stop-gradient substitutes; [critical] preserve keyboard focus rings, invalid-input borders, neutral hairlines and table rules; preserve a user-designated screenshot instead of silently redesigning it.
- B, quantitative research with unavailable rendering: [critical] use the supplied `bench.csv` values and units with provenance (A: 40 ms, 120 MiB; B: 25 ms, 210 MiB; dated 2026-10-20); choose a quantitative chart; [critical] remain read-only and never claim an unrun render; include caption, accessible description and exact next rendering action.
- C, architecture-only research: [critical] use only `browser → gateway → database` from `architecture.md` revision `abc`, without invented numerical charts; [critical] logo-only content, a zero-height diagram and raw Mermaid source are not rendered evidence; distinguish informative descriptions from intentional decoration; remain read-only and state rendering limitations.

Iteration 0 checks description/body consistency. Frontend already covers styling decisions; ultraresearch already covers exhaustive decision research. The additions refine existing outputs without expanding triggers.

Collaboration metadata does not expose complete tool-use or duration measurements. Unavailable metrics will be recorded as unavailable, never estimated. Convergence will not be claimed from accuracy alone.

## Baseline

The executor returned concrete A–C output snippets. A replaces the proposed border with a neutral surface, hairline, heading hierarchy and spacing, preserves functional borders and the reference exception, and audits equivalent stripe implementations. B reproduces all four supplied values and specifies separate latency and memory bar panels with captions. C describes only the three supplied architecture nodes and rejects the logo, zero-height figure and raw source as rendered evidence. All scenarios retain read-only behavior and explicit rendering handoffs.

| Scenario | Success | Accuracy | Steps | Duration | Retries |
|---|---|---|---|---|---|
| A | yes | 4/4, 100% | unavailable | unavailable | 0 |
| B | yes | 4/4, 100% | unavailable | unavailable | 0 |
| C | yes | 4/4, 100% | unavailable | unavailable | 0 |

New unclear point: the aesthetics reference calls focus rings the only colored edge, leaving validation borders ambiguous. Discretion gaps: equivalent-stripe detection and validation preservation were supplied by the scenario; visualization selection, accessible captions, rendered-evidence rejection and rendering handoffs were not explicit in ultraresearch. Therefore baseline accuracy measures scenario compliance, not reliable unaided discovery from the original skills.

One initial dispatch was rejected for missing an explicit registered role and corrected before execution. The baseline QA executor's role required a persisted matrix; it was authorized to write only `.claude/omo/reviews/2026-10-20-refresh-baseline.md`, which is ignored working evidence, not a plugin change.

## Iteration 1 changes

- Frontend theme, checklist A1–A4: early stripe check, equivalent implementations, concrete replacements, legitimate exceptions and reference priority. `SKILL.md`: 114 → 118 lines; aesthetics: 65 → 65 lines.
- Research theme, checklist B1–B4 and C1–C4: finding-to-visual selection, exact data and units, provenance, accessible description, read-only handoff, and observed-rendering requirement. `SKILL.md`: 115 → 126 lines.
- These are independent themes; each has separate scenario scores and no claim of a combined causal accuracy gain. Descriptions remain consistent with their bodies. Both skills remain under 500 lines; aesthetics is under the 100-line reference TOC threshold.
- Manifest, marketplace and README synchronize at 1.51.0; manifest descriptions remain 148 characters, below the repository's 200-character maximum.

## Command validation

- `claude plugin validate ./omo-orchestrator`: passed.
- `claude plugin validate .`: passed with the pre-existing `metadata.homepage` unknown-field warning.
- `git diff --check`: passed.
- `node --test` over `omo-dir-ignore.test.mjs`, `load-skills-gate.test.mjs`, `review-gate.test.mjs`, `pasted.test.mjs`, and `scripts/impact.test.mjs`: exit 0.
- No new plugin or script changes, so the AGENTS.md mandatory security-check trigger does not apply. No runtime execution behavior changed.

The upstream checkout advanced concurrently to `048883f20693bb53fc4b8e80f2c52acd01118121`; a diff from the original pull tip shows no subsequent changes to the selected frontend and ulw-research skill trees. No other session's changes were reverted.

## Iteration 1 results

| Scenario | Success | Accuracy | Steps | Duration | Retries |
|---|---|---|---|---|---|
| A | yes | 4/4, 100% | 1 batch read shared by A–C | unavailable | 0 |
| B | yes | 4/4, 100% | shared | unavailable | 0 |
| C | yes | 4/4, 100% | shared | unavailable | 0 |

Output A chooses an accent heading instead of the stripe, covers all equivalent implementations and legitimate exceptions, and preserves a required screenshot edge. Output B preserves the table exactly and specifies separate zero-based bar panels (latency 0–50 ms, memory 0–250 MiB), with direct labels and a supplied-source limitation. These bounds are labeled presentation choices, not measurements. Output C returns `flowchart LR; browser --> gateway; gateway --> database`, with revision provenance, accessible description, and no numeric chart. Both research snippets say not rendered, reject invalid evidence, and hand exact data/source plus inspection steps to a separately authorized owner.

New target-theme unclear points: none. Contextual choices remain: actual design tokens and screenshot, chart type and scale, renderer, destination, benchmark methodology, logo purpose, and arrow semantics. These are not resolved by inventing project or source facts. No prompt correction follows this round.

## Iteration 2 and holdout protocol

Fresh executor receives unchanged A–C and a previously unused holdout D, with this checklist fixed before its execution:

- D1 [critical]: preserve an orange left stripe explicitly required by a rounded warning-callout screenshot, adjacent invalid-input border and focus ring; record the reference exception.
- D2 [critical]: for structural-only research (`path.md`, revision `d12`, producer → queue → worker), invent no numerical chart and perform no write or installation when rendering is unavailable.
- D3: supply structural source, caption, provenance and accessible description.
- D4 [critical]: a chart with width zero and a decorative image with empty alt plus presentation role do not count as evidence; state unrendered status and the exact handoff.

This tests reference priority, false positives, the other zero-dimension case, and structural-only output without reusing the original architecture.
