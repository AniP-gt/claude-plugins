# Aesthetics

How to make designed choices instead of default ones. The design system says what values exist; this file says how to choose them.

## Brief Ambition

| Lane | Signals | Posture |
|---|---|---|
| Expressive | landing, marketing, "premium", "glossy", "make it beautiful", a named product to feel like | Rich material is the deliverable. Commit to a bold direction and a signature moment. |
| Operational | internal tool, dashboard, admin, settings, "just make it usable" | Restraint, precision, density control, excellent state feedback. |

Match implementation complexity to the vision. Maximalist work needs elaborate layering and motion. Minimalist work needs precise spacing and typography, not less effort.

## Work Principles

1. Complete exactly what is asked. No scope creep, but work until it works.
2. Study before acting: existing patterns, conventions, and commit history.
3. Blend in. The result should look like the team wrote it.
4. Leave the project in a working state.
5. Be transparent: state the direction, the references loaded, and what was verified.

## Typography

- Choose type with character. Pair a distinctive display face with a refined body face. Max 2 families (3 only with a reason).
- Do not reach for default families (Inter, Roboto, Arial, system stack, Space Grotesk) on an expressive brief unless the project already uses them.
- Load the declared fonts. A silent fallback to system fonts is a regression.
- Body text is never below 14px. Headings that wrap to 4+ lines are too large; use `clamp()`.
- Tight negative tracking on large display sizes, slight positive tracking on small uppercase labels.

## Color

- Commit to a cohesive palette with roles (surface, text, border, accent, status). Dominant neutrals with one sharp accent beat timid, evenly spread palettes.
- Build a real ramp: multiple perceptual stops (OKLCH works well), not one brand hex reused at varied opacity.
- Accent marks the one or two most likely actions on a screen, on the control's background. A restrained accent heading or glyph can identify a group; avoid decorative edge stripes as described below.
- Define light and dark values together when the product supports both.
- Avoid: purple-to-blue gradients on white, rainbow gradients, every card a different tint.

## Depth and Surface

- Pick one depth strategy and commit: borders-only, shadows, tonal shift, or a documented mix.
- Surfaces should read as materials. Give the background and the hero depth: gradient, glow, layered light, grain, a real image. One flat fill for an expressive hero is the flat trap.
- Glass is not a single `backdrop-filter: blur`. It is tint, blur, rim light, sheen, and shadow together.
- Elevation reads only when scale, shadow, and highlight change together.
- Nested corners are concentric: inner radius equals outer radius minus the padding between them.

## Spatial Composition

- For expressive work: asymmetry, overlap, diagonal flow, grid-breaking elements, generous negative space or deliberately controlled density.
- Before laying out sections, inventory the content blocks and give each a job (hook, explain, prove, compare, convert, navigate, retain). Order sections by the visitor's decision path, not visual symmetry.
- Do not force marketing structure (hero, zigzag, bento) onto a task app.

## Motion

- One well-orchestrated page load with staggered reveals beats scattered micro-interactions.
- Motion serves meaning. Every animation maps to a real interaction, state change, or affordance. Mechanics are in `layout-and-motion.md`.
- Prefer CSS. Use a motion library only if the project already has one.

## Anti-Patterns

- Invented proof: testimonials, quotations, ratings, customer logos, user counts, and prices need project evidence. Omit unsupported proof or leave an explicitly empty owner-fill slot; a sample testimonial is still fabricated.
- Static promotional badges, duplicated figures, and stat tiles without a decision to support. Keep chips that carry real status, counts, or filter categories. Product previews show real readable states; remove floating reassurance cards, sparkles, and props with no product meaning. State what the interface does in plain copy.
- A repeated eyebrow-heading-subtitle formula in every section. Keep explanatory copy only when it adds information; each required datum and input keeps its own place even when decorative repetition is removed.

- By default, remove decorative labels above headings, repeated icon-tile/heading/card grids, cards nested in cards, giant metrics without a decision to support, and monospace chosen only to look technical. Use headings, task-shaped lists or tables, space between inner groups, and the project's reading face; keep mono for code, IDs, data, or measurements. Preserve each required datum and meaningful status label.
- Secondary text on a tinted surface uses a compatible hue or foreground alpha that passes contrast on the actual background. Prefer a soft, offset shadow over a zero-offset colored glow. A named visual contract or chosen direction can require a kicker, mono heading, glow, or hard offset shadow; record that item's source and scope rather than redesigning it. These defaults do not ban an intentional material from Depth and Surface. Accessibility and usable states still apply; see `quality-floor.md` Rendered Craft Checks.

- Freestyling without a direction: rounded-2xl on everything, three feature cards in a grid, generic font, lorem ipsum.
- **Coloured bars along one side of a box, rounded or square, for decoration or state.** A feature card with `border-top: 4px solid <accent>` or a callout with `border-l-4 border-primary` has the same problem. A `::before`/`::after` bar, inset `box-shadow`, hard-stop gradient band, or gradient `border-image` is not a workaround. Also avoid accent underlines on headings, tabs, or links, and accent outlines 2px or wider on rounded cards, including inset rings. Replace these treatments with a tonal surface, accent text, a leading glyph, or spacing; encode hover/selected/active state with ink-alpha washes and a selection glyph. Preserve keyboard `focus-visible` rings, validation borders on form inputs, neutral 1px hairlines/dividers, table rules, and neutral blockquote rules. Apply this to pre-existing instances on surfaces you touch, but retain an edge required by a user-designated visual target and record that reference exception.
- Emojis as icons, in markup, alt text, or visible UI.
- Decorative motion on non-interactive elements; hovers that change nothing.
- Applying a named brand verbatim to a project that is not that brand. Extract tokens and layout grammar; never copy logos, trademarked imagery, or brand copy.
- A design system description that could describe any generic dark SaaS. If it could, the distinctive material was lost; put it back.
