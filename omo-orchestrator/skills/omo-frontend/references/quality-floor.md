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
