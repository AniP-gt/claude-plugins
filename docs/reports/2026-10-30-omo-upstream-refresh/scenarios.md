# Brief-generation scenarios

Read `omo-orchestrator/skills/omo-frontend/SKILL.md` and its
`references/quality-floor.md`, `references/aesthetics.md`, and
`references/design-system.md`. Use only these instructions and the scenario facts.
Generate concrete implementer briefs. This is instruction execution on fictional
projects, not rendered UI QA. Do not edit files, install packages, spawn agents,
commit, push, send messages externally, or fabricate files, measurements, or captures.

## A: Monitoring UI

A new internal monitoring screen has no explicit visual target or dependencies to
add. Its unapproved DESIGN.md draft has body=16px, h3=18px, h2=20px, h1=24px;
section heading top/bottom spacing=16/16px; group/inner gap=12/8px; desktop
prose=100ch; display=7rem, tracking=-0.06em. Selection, caret, scrollbar, focus,
link underline, and numeral styles are undefined. The draft proposes equal cards
with icon tiles and FEATURES kickers, nested cards, mono everywhere to look
technical, gray secondary text on blue, and a zero-offset glow.

Decide whether to finalize the draft, what to change, and what computed evidence
the implementer must collect later.

## B: Explicit neo-brutalist contract

An existing project explicitly requires display=8rem, tracking=-0.05em, selected
section kickers, hard offset shadow=4px 4px 0, and mono headings in DESIGN.md.
Enough nearby components and installed dependencies exist. Native controls are
intentionally unstyled. Touch targets=44px and visible keyboard focus are required;
both light and dark themes exist. A proposal removes the focus ring and ignores
reduced motion.

Decide what to preserve or fix, and specify the final QA evidence.

## Return

Give each scenario's brief, then unclear instruction wording, discretion gaps,
and retries of the same judgment. Distinguish missing fictional project inputs
from unclear skill instructions. Report observed tool-call count and elapsed
time if measurable; otherwise label them unavailable. Do not read evaluation.md,
previous executor results, or the upstream repository.
