---
name: omo-visual-qa
description: Manual visual verification for browser pages and terminal TUIs with fresh evidence and APPROVE, REQUEST_CHANGES, or INCONCLUSIVE outcomes.
argument-hint: [surface-or-goal]
allowed-tools: Read, Grep, Glob, Bash, TodoWrite
user-invocable: true
---

# OMO Visual QA

Use this skill after changing a browser-rendered page or terminal/TUI surface. It is a content-only workflow. It does not provide browser automation, screenshot or diff scripts, browser runtimes, profile tooling, hooks, or services.

## Select The Target

1. Create a preflight inventory of the supplied rendered fixture or surface, access route or launch command, required states, viewports or terminal sizes, references, credentials, and available inspection tools. Mark every missing item before testing.
2. Classify the target as `BROWSER_PAGE` or `TERMINAL_TUI`. If it has both surfaces, test each separately.
3. List every required route, screen, tab, modal, state, viewport, terminal size, scroll position, color mode, and motion setting. Do not approve a sampled subset.
4. Use a browser, terminal, renderer, or inspection tool already available in the current environment. Drive the real rendered surface. Reading source code is not visual evidence.
5. For authenticated work, use an isolated or cloned test profile with only the access required for the check. Never use, inspect, copy, or alter a live user browser profile.
6. Record unavailable tools, credentials, references, or surfaces as evidence gaps. Do not infer success from source code or an unrendered artifact.

## Capture Plan And Integrity

1. Project, task, and reference requirements win. If they name stricter breakpoints, devices, states, or scroll coverage, use every named requirement and do not replace it with defaults.
2. Without stricter browser requirements, capture each page and required state at fixed `390x844` phone and `1440x900` desktop viewports. For every scrollable page or independently scrollable region, capture its initial and scrolled-to-end views.
3. If both light and dark modes exist, capture the same required item in paired modes. Record the mode with each capture.
4. For every meaningful motion, retain normal-motion rest, transition, and settled frames. Drive one applicable interruption while motion is active and capture the resulting state. Record the same action with reduced motion enabled. Mark motion `N/A` only when the item has no motion.
5. Before judging a capture, validate that its file signature matches its format, the image opens fully composited without blank, black, or unpainted regions, its pixel dimensions match the recorded plan, and its frame matches the route, mode, viewport, state, scroll position, and timing. A bad or unavailable artifact is an evidence gap, never a pass.

## Evidence Freshness

1. Capture current visual evidence after the final relevant edit. Record the source revision or exact changed files with each capture.
2. An edit to a rendered source file, style, asset, configuration, fixture, or data that can affect a checked surface makes affected evidence stale.
3. Discard stale rows, recapture the affected surfaces, and repeat their checks before returning `APPROVE`.
4. Revalidate every artifact under Capture Plan And Integrity after recapture. Mark corrupted, partial, mismatched, or untrusted artifacts as unavailable evidence.

## Browser Page Checks

For every listed browser page or state, interact with the actual page and record:

- Responsive layout at every required viewport. Check overflow, clipping, scroll behavior, navigation, focus, hover, active, disabled, loading, empty, error, and modal states where they apply.
- Functional and design-system integrity. Confirm live controls work, semantic content is present, reusable components render as intended, and no screenshot or static image substitutes for an interactive surface.
- Visual fidelity. Compare layout, hierarchy, spacing, typography, colors, icons, borders, radii, shadows, assets, copy, and alignment with the stated intent or reference. When a reference exists, inspect matching viewports and settled states.
- Motion and interaction. Check the planned normal, reduced-motion, and interruption evidence for meaningful animation, hover, focus, click, load, and scroll effects. A moving surface is not evidence until its settled state is checked.
- Text and CJK precision. Check line breaks, orphaned particles or final characters, clipped glyphs, missing glyphs, detached labels, wrapped citations, baselines, and natural Korean, Japanese, and Chinese phrase wrapping.
- Browser console and rendered error state when the available surface exposes them. Record console errors, warnings that affect the result, failed assets, and visible error boundaries.

## Terminal TUI Checks

For every listed TUI screen, render and operate the actual program in a terminal or available rendered terminal surface. Record:

- The initial screen, named happy path, one relevant invalid or error path, and each requested interaction.
- Terminal dimensions, resizing behavior, viewport scrolling, focus and input handling, terminal color output, and redraw behavior where they apply.
- Box drawing, columns, borders, padding, truncation, wrapping, overflow, and status lines at every required terminal size.
- CJK and wide-character width. Check that wide glyphs consume the correct columns, borders stay aligned, and wrapped Korean, Japanese, and Chinese text remains readable without orphaned characters or clipped glyphs.
- Runtime errors, warnings, or logs exposed by the available terminal surface.

## Per-Item Capture Checklist

For every listed browser or terminal item, mark each applicable cell `PASS`, `FAIL`, or `N/A`. `N/A` means the check cannot apply, never that evidence is missing. Missing required evidence remains an evidence gap and can only produce `INCONCLUSIVE`.

| Item | Coverage | Mode | Artifact | Motion | Text / CJK | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `BROWSER_PAGE: /settings, phone, light, end scroll` | `PASS` | `PASS` | `PASS` | `PASS` | `PASS` | [current capture paths] |
| `TERMINAL_TUI: dashboard, 100x30` | `PASS` | `N/A` | `PASS` | `N/A` | `PASS` | [current capture or log path] |

`Coverage` includes every required route, state, viewport or terminal size, and end-scroll view. `Mode` requires paired light and dark captures when both exist. `Artifact` covers signature, compositing, dimensions, and frame identity. `Motion` covers normal, reduced-motion, and interruption evidence.

## QA Matrix

Create one row per checked surface and action. Every row must contain all fields below.

| Surface | Action | Expected | Observed | Evidence | Verdict |
| --- | --- | --- | --- | --- |
| `BROWSER_PAGE: /settings, 1440x900, saved state` | Open page, change theme, reload | Selection persists and layout remains unclipped | [record actual observation] | [current capture or log path] | `APPROVE` / `REQUEST_CHANGES` / `INCONCLUSIVE` |
| `TERMINAL_TUI: dashboard, 100x30` | Resize, navigate, submit invalid input | Borders align and validation is readable | [record actual observation] | [current capture or log path] | `APPROVE` / `REQUEST_CHANGES` / `INCONCLUSIVE` |

Use exact paths, route names, dimensions, terminal sizes, actions, expected results, and observed results. A row without an evidence location is incomplete.

## Review Perspectives

Review the matrix from both perspectives before the final verdict:

1. Functional and design-system perspective. Check that the surface is live, interactions work, required states are covered, and the structure supports the intended behavior.
2. Visual-fidelity perspective. Check the rendered result, responsive behavior, clipping, wrapping, motion, CJK layout, and reference match where one exists.

When an independent read-only reviewer is available, give it the scope list, current captures, matrix, source revision, console or error evidence, and references. Its review does not replace missing rendered evidence.

## Final Verdict

Return one outcome only:

- `APPROVE`: every required matrix row and applicable checklist cell passes with fresh, trusted evidence from the final tree; expected and observed results agree; and both review perspectives have no blocking finding. Only `APPROVE` permits completion.
- `REQUEST_CHANGES`: one or more rows show a confirmed failure. Name the failed surface, action, evidence path, and bounded fix required. Recheck affected rows on fresh evidence after the fix.
- `INCONCLUSIVE`: required evidence is missing, stale, corrupted, untrusted, inaccessible, or insufficient to judge. If no rendered fixture or runnable surface was supplied, return `INCONCLUSIVE` without attempting to infer or create one; name the missing fixture or surface, owner if known, and the exact next action needed to supply it. Never treat missing or stale evidence as approval.

## Report

Return the target classification, complete capture checklist and QA matrix, final verdict, blocking findings or evidence gaps, evidence paths, source revision or final-tree identity, and one next exact action. Keep secrets, private user content, and authentication material out of captures and reports.
