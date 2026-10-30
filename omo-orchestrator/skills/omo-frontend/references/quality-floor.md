# Quality Floor

Beauty with a broken bundle fails. A fast page that looks generic fails. Both win or neither does.

## Before Writing Code

1. Verify dependencies in `package.json`. Do not assume `framer-motion`, `gsap`, `lucide-react`, or `tailwindcss` exist, or which major version. Missing means: use what exists, or give the user the install command and wait. Never install it yourself.
2. Lock the Tailwind version. v4 uses `@tailwindcss/postcss` or the Vite plugin; v3 uses `tailwind.config.*` and different syntax.
3. Next.js App Router: isolate motion, state, and portals in a `'use client'` leaf. Do not mark the whole page as client.
4. Full-height heroes use `min-height: 100dvh`, never `h-screen` / `100vh`.

## Accessibility

- Semantic HTML: `<button>` for actions, `<a href>` for navigation, landmarks (`header`, `nav`, `main`, `footer`), labeled inputs, alt text for meaningful images, one `<title>` per route, `lang` on `<html>`.
- Contrast: at least 4.5:1 body text, 3:1 large text and UI boundaries.
- Visible `focus-visible` on every interactive element; full keyboard reachability; logical tab order.
- Touch targets at least 44 by 44 px on touch surfaces.
- `prefers-reduced-motion` respected (see `layout-and-motion.md`).
- Split or animated text keeps the full string readable to screen readers.

When goals conflict: accessibility over aesthetics, usability over style, the brief over opinion. Escalate unresolved trade-offs to the user.

## Rendered Craft Checks

Use these defaults when establishing or extending a system, including a greenfield draft. An explicit project design rule, user-designated visual target, or chosen direction may override a default for the named item only. Record its source, affected roles/states, intended value, and proof in the brief; keep established patterns on unrelated surfaces. A style exception never waives accessibility, usable reflow, keyboard focus, or reduced motion.

An unapproved draft value is not itself an exception. When choosing a direction, justify any deviation by the brief's purpose and label it as a design choice; do not present it as user approval. Apply an existing explicit contract directly without requesting approval again.

| Check | Default and evidence to collect after implementation |
|---|---|
| Heading hierarchy | Adjacent heading roles in use, and the smallest heading versus body, differ by at least 1.25x in computed font size. Body-family roles closer in size also differ in weight, color, or case. Record the used roles and ratios. |
| Section rhythm | Above-heading space is at least 1.5x below-heading space; between-group space is at least 2x within-group space. Measure effective rendered separation, including parent gaps and collapsed margins. |
| Text measure | Aim for 65-75 characters per desktop line of Latin prose; confirm with actual copy. This is not a minimum width: narrow screens, CJK text, labels, and dense data use readable wrapping and reflow without forced character counts or overflow. |
| Display type | Default display size is at most 6rem and tracking no tighter than -0.04em; body tracking is 0. Inspect computed values at required widths. Intentional larger or tighter display type needs the scoped design exception above. |
| Browser-drawn details | From existing palette tokens, define selection background/ink, caret color, visible scrollbar thumb/track, focus-visible outline, link underline offset/thickness, and tabular numerals for aligned or changing values. Verify actual selection, focused input, links, scrolling, and numeric alignment in every existing theme. Keep overlay scrollbars overlay; never add a decorative gutter or hide usable scrolling. |

Absent elements are N/A; do not add inputs or numbers to satisfy a check. Intentionally native controls and system or forced-color accessibility rendering may keep platform styling. Preserve a visible keyboard focus indicator. Color changes still need the Accessibility contrast checks, including alpha text against its painted background.

The pattern choices are in `aesthetics.md`; scoped exceptions and planned computed probes belong in the implementer brief's constraint and proof map. Source lineage and modification notices: [ATTRIBUTION.md](../ATTRIBUTION.md).

## Performance Root Causes

Fix at the source, not with band-aids. Check these first:

- Render-blocking JS or CSS in the critical path. Code-split by route, defer non-critical work.
- Unsized media. Every `img`, `video`, `iframe` has `width`/`height` or an `aspect-ratio` container (prevents layout shift).
- Wrong image format or size. Serve modern formats at the rendered size; `fetchpriority="high"` on the LCP image.
- Fonts: `font-display: swap`, preload only the one critical font, subset when possible.
- Hydration or client JS on routes that do not need interactivity.
- Heavy effects (WebGL, large animation libs) lazy-loaded after the LCP element, with a static fallback.
- `will-change` only on the property that animates, only while it animates. `content-visibility: auto` for long offscreen sections.

Measure on a production build in a real browser when that tooling is available in the environment. If it is not, report performance as unverified rather than guessing a score.

## Never Weaken UX To Buy Points

Reject any fix that removes a hover state, drops a transition, replaces an animated mount with an abrupt one, hides content, or flattens a surface to improve a metric. Split bundles, defer work, move work off the main thread, or use compositor-only animation instead.

## Content Stress

A layout is not done until every region survives:

- **Empty.** No rows, no avatar, no value. Collapses gracefully.
- **Long label.** A 40-character name in a 12-character slot truncates or wraps by design.
- **Long paragraph.** Measure stays readable.
- **Unbroken string.** URLs and tokens need `overflow-wrap: anywhere` and `min-width: 0` on flex/grid children.
- **Reflow.** At 375px, one readable column with no horizontal scroll of primary content.
- **Direction.** If RTL is supported, logical properties (`margin-inline`, `inset-inline-start`) mirror correctly.
- **CJK.** Line breaks do not strand a single character or particle; glyphs are not clipped.
