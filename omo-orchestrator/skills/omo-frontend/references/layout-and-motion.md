# Layout and Motion

Mechanics only. Visual values still come from the design system.

## Scroll Ownership

Decide before writing layout CSS for any app shell (dashboard, settings, inbox, list-detail, split panes):

- Which ONE element owns vertical scroll in each region?
- Which regions stay fixed (header, sidebar, toolbar, footer)?
- Which ancestor bounds the height? A scroll container without a bounded ancestor grows instead of scrolling.

One scroll container per region unless each extra one has a named job. Full-height shells use `100dvh`, never `100vh` (iOS address bar jump). Do not mix sticky-in-document and fixed-shell models in one region without a reason.

## Two Contracts That Fail Silently

Bounded scroll shell:

```css
.shell { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; max-block-size: 100dvh; }
.shell__body { min-block-size: 0; overflow: auto; }
```

Without `min-block-size: 0` (or `min-height: 0` in a flex column) the child refuses to shrink and pushes the footer off-screen.

Overflow-safe intrinsic grid:

```css
.grid { display: grid; gap: var(--gap); grid-template-columns: repeat(auto-fit, minmax(min(16rem, 100%), 1fr)); }
```

The inner `min(16rem, 100%)` prevents horizontal overflow on narrow containers.

## Layout Primitives

| Primitive | Job | Mechanic |
|---|---|---|
| stack | Vertical rhythm | flex column + `gap` |
| cluster | Wrapping row of tags or actions | `flex-wrap: wrap` + `gap` |
| content-limiter | Readable measure | `max-inline-size: ~65ch; margin-inline: auto` |
| sidebar | Narrow aside + fluid main, wraps when tight | flex with a fixed basis aside and a `min-inline-size` main |
| switcher | Row when roomy, stack when tight, no breakpoint | flex + `min()` basis |
| cover | Centered region between header and footer | rows `auto 1fr auto`, `min-block-size: 100dvh` |
| frame | Media at an aspect ratio | `aspect-ratio` + `object-fit: cover` |
| reel | Horizontal scroll row | `overflow-x: auto` + `scroll-snap`, keyboard reachable |
| list-detail | List beside its detail | two columns, each pane's scroll owner named |

Choose by spatial shape, not product label. Settings and docs both want a fixed side nav shell.

## Responsiveness

- The component adapts to its own width (a card in main vs in a rail): `container-type: inline-size` + `@container`.
- The page frame changes (sidebar collapses): `@media`.
- Prefer intrinsic adaptation (switcher, sidebar, intrinsic grid, `clamp()`) over any query. Name breakpoints by layout state, not device.

## Motion Follows Meaning

| Meaning | Motion | Not |
|---|---|---|
| Press acknowledged | Scale or wash on the element, same frame | A ripple that lands after the action |
| In progress | A moving indicator | A static one that reads as frozen |
| Live or new | One brief highlight | A permanent loop |
| Arrived from elsewhere | Enter from the origin direction | A fade from nowhere |
| Moved | Travels there | Vanish here, appear there |

## Motion Rules

- Animate only `transform`, `opacity`, `filter`. Never `width`, `height`, `top`, `left`, `margin`, `padding`. No `transition: all`.
- Springs for spatial movement (interruptible, retargetable); short easings for color, opacity, blur. Continuous input (drag, wheel, slider) tracks 1:1, then settles on release.
- Interruptible: hover-out, press, or route change mid-animation retargets smoothly and never blocks input.
- Transitions keep identity. A surface that resizes or swaps content morphs from old geometry to new; it does not unmount and remount. A panel leaves the way it came.
- One event, one feedback, on the object that changed. Success shows as the changed state; failure is reported next to the object with the cause. Toast only for outcomes not visible in place. Prefer undo over a confirmation dialog.
- Scroll-triggered effects use `IntersectionObserver` or CSS scroll-driven animations, never scroll listeners.
- Background loops pause off-screen and on hidden tabs, tear down on unmount, and cap `devicePixelRatio` at 2. Decorative layers get `aria-hidden="true"` and `pointer-events: none`.
- One atmosphere per page. A reveal on every paragraph is slop.
- Large-area motion stays low contrast with still surrounding chrome as a reference frame.

## Feedback Thresholds

| Event | Feedback |
|---|---|
| Press, tap, drag start | State change on the element in the same frame |
| Async action started | Disabled control or placeholder at once; spinner or skeleton only past about 1 s |
| Long wait | Determinate progress at an even pace; indeterminate only when the total is unknown |
| Hover-revealed controls | Appear after hover intent, not on pointer entry |

## Reduced Motion

Reduce, do not remove. Under `prefers-reduced-motion: reduce`, positional, scale, and depth motion becomes a cross-fade; fades, gesture-tracked motion, and progress indicators stay. Backgrounds render one static frame. Text reveals render at their final state. State conveyed by motion is also announced (`aria-live` or a label change).
