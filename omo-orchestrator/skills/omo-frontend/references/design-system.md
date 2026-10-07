# Design System

The design system is the implementation contract. It can live in `DESIGN.md`, token files, CSS custom properties, or a Tailwind theme. Use whatever the project already has; create `DESIGN.md` only when nothing exists.

## Token Usage Rules

| Element | Correct | Rejected |
|---|---|---|
| Color | Token or CSS variable (`var(--accent-primary)`, `text-brand-500`) | `#3b82f6`, `rgb(59,130,246)` |
| Spacing | Scale value (`space-4`, `gap-md`, `var(--space-4)`) | `margin: 13px`, `padding: 7px` |
| Typography | Scale step (`text-lg`, `heading-2`) | `font-size: 17px` |
| Radius | Radius token | `border-radius: 6px` |
| Shadow | Elevation token | Inline one-off `box-shadow` |
| Component | Compose or extend existing primitives | One-off div soup with inline styles |

Tokenize design intent: spacing steps, content width, gutters, section gaps, density. Keep browser mechanics raw: `auto`, `%`, `min-content`, `fit-content`, `clamp()`, viewport and container units, intrinsic sizing. `minmax(min(16rem, 100%), 1fr)` is mechanics, not a magic number.

If the design needs something outside the system, extend the system first (add the token or primitive), then use it. Never one-off override. That is how design systems die.

## Minimal System Structure

When creating one, cover these sections. Keep each short.

1. **Atmosphere.** One paragraph on how the product feels, plus the named signature.
2. **Color.** Table of role, token, light value, dark value, usage. Roles: surface (primary, secondary, elevated), text (primary, secondary, tertiary), border (default, subtle), accent (primary, hover), status (success, warning, error, info). Rule: no color outside the table.
3. **Typography.** Scale table (display, h1 to h3, body lg / base / sm, caption, overline) with size, weight, line height, tracking. Font stacks for display, body, mono.
4. **Spacing and layout.** Base unit (usually 4px) and a scale from 4 to 96. Max content width, column system, breakpoint names.
5. **Components.** For each primitive: structure, variants, spacing tokens, states (default, hover, active, focus, disabled, loading, empty, error), accessibility, motion, layout primitive and scroll owner. For externally informed mechanisms, cite the source and record the token mapping and adaptations; keep source code out of this document. Use `component-references.md` for source and reuse checks.
6. **Motion.** Timing table (micro 100 to 150ms ease-out, standard 200 to 300ms, emphasis 400 to 600ms with a strong ease-out curve) and the feedback thresholds in `layout-and-motion.md`.
7. **Depth.** The one chosen strategy, its elevation values, and the radius scale (sm, md, lg, full).
8. **Accessibility and accepted debt.** WCAG target and contrast floor, plus a debt table (item, location, why accepted, exit). New debt is recorded when accepted, never silently.

## Extraction From Existing Code

1. Read all styling sources: global CSS, theme files, Tailwind config, component styles.
2. Count repeats: which colors, sizes, spacings, radii, shadows, and components recur.
3. Codify what exists into the structure above. Map near-duplicates to one token and list the deviations with file:line.
4. Propose consolidation separately. Do not apply it without approval.

## Validation After Each Component

- Colors, font sizes, spacing, radii, and shadows all trace to tokens.
- Interactive elements have every required state.
- Depth matches the chosen strategy; nested radii are concentric.
- Motion follows the timing table and has a reduced-motion path.
- A pattern used 2+ times is documented as a primitive.
- Survives content stress (see `quality-floor.md`).

## Growth Discipline

Add to the system when a reusable component appears (2+ uses), a color serves a genuinely new semantic role, a spacing step is missing for a real need, or the user changes direction.

Do not add for a one-off section, for "might need later", or for experiments.

A system that grows every week is dying. One that holds its size or shrinks is getting sharper. Every addition must remove ambiguity, not add options.
