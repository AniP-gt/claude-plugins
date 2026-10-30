# OMO upstream refresh evaluation

## Frozen scenarios and scoring

Defined before reading the baseline executor's result. This evaluates instruction
execution by generating implementer briefs, not rendered UI quality. No screenshots,
computed measurements, or runtime passes may be invented. Each item is scored
1 (met), 0.5 (partial), or 0 (missing); success requires every critical item fully met.
The executor receives the scenario facts but not this scoring key.

### A: Unspecified monitoring UI draft

1. [critical] Replace the draft heading ladder with adjacent used headings and smallest-heading/body ratios >=1.25; require computed verification.
2. Set heading space above/below >=1.5 and inter/intra-group spacing >=2; require computed verification.
3. Set desktop Latin prose to 65-75ch, display default <=6rem, tracking >=-0.04em, without applying a Latin minimum character count to CJK or narrow screens.
4. Specify token-backed selection, caret, visible scrollbar, focus, link underline, and aligned numeric styles; preserve overlay behavior and native-control exceptions.
5. [critical] Remove unsupported repeated kicker/icon-card scaffolds, nested cards, decorative mono, gray-on-blue secondary text, and zero-offset glow; supply meaningful replacements.
6. Do not invent measurements, install dependencies, or claim QA approval; give explicit final rendered-evidence steps.

### B: Explicit neo-brutalist contract

1. [critical] Preserve the intentional 8rem display, -0.05em tracking, chosen kicker, hard offset shadow, and mono heading; record their source and scope rather than redesigning them.
2. Preserve intentionally unstyled native controls; do not force decorative scrollbar gutters.
3. [critical] Reject removing keyboard focus or ignoring reduced motion; retain accessibility and usability checks despite style exceptions.
4. Require final rendered and computed evidence with both existing themes, responsive states, and named exceptions; do not fabricate approval.

### Hold-out C: Japanese narrow-screen native form

Introduce only after the repeated scenarios pass. A 320px Japanese form intentionally
uses native inputs, has no prose columns or numeric tables, and inherits the system
palette; the hero has no display role. The proposal forces a 45-character minimum
line width, hides scrollbars, and removes focus to match a screenshot.

1. [critical] Reject forced Latin character counts / horizontal overflow on Japanese mobile text; preserve readable reflow and CJK wrapping.
2. Preserve native inputs and mark absent caret customization, numeric columns, and display checks N/A where appropriate; do not invent elements or custom decoration.
3. [critical] Preserve visible keyboard focus and usable scrolling despite the screenshot; scope the visual-reference exception without waiving accessibility.
4. State that implementation and fresh rendered evidence remain necessary; do not claim a simulated brief is visual approval.

## Results

| Round | A | B | C | Retries |
|---|---|---|---|---|
| Baseline | 58.3%, fail (critical 1 missing, critical 5 partial) | 100%, pass | not run | 0 |
| Iteration 1 | 100%, pass | 100%, pass | not run | 0 |
| Iteration 2 | 100%, pass | 100%, pass | 100%, pass | 0 |

Tool count and duration are reported only when exposed or measured; missing runtime
metadata is labelled unavailable. See report.md for observed output and discretion
gaps. C is held out from the repeated scenarios.
The run stopped by resource cutoff, not by claiming the full zero-ambiguity and
timing-based convergence conditions were satisfied.
