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
- Accent marks the one or two most likely actions on a screen, on the control's background. Nothing decorative carries accent.
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

- Freestyling without a direction: rounded-2xl on everything, three feature cards in a grid, generic font, lorem ipsum.
- **Coloured accent border to mark state.** `border-l-2 border-primary` on a selected row, a primary outline on a focused card. Encode state with ink-alpha washes (hover, selected, active ramps), a glyph for selection, and tonal layering. `focus-visible` rings are the only coloured edge. Sweep out pre-existing instances on surfaces you touch.
- Emojis as icons, in markup, alt text, or visible UI.
- Decorative motion on non-interactive elements; hovers that change nothing.
- Applying a named brand verbatim to a project that is not that brand. Extract tokens and layout grammar; never copy logos, trademarked imagery, or brand copy.
- A design system description that could describe any generic dark SaaS. If it could, the distinctive material was lost; put it back.
