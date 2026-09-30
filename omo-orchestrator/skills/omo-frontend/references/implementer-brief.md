# Implementer Brief

Every `omo-orchestrator:omo-implementer` brief is self-contained. The implementer did not see your analysis. Without a binary `Done when` it has no exit.

For multi-step work, append the brief to the task ledger at `.claude/omo/handoffs/<task-slug>.md` and reference that path in the prompt. For a single delegation, pass the brief inline.

## Template

```markdown
## Goal
What UI is being built or changed, and for whom.

## Direction
Tone, the one signature element, and the brief lane (expressive or operational).
Reference (screenshot path, URL, or none) and what must match it.

## Design system
- Location: path(s) to DESIGN.md, token files, theme, or Tailwind config
- Naming: BEM / utility classes / CSS Modules / component-scoped
- Tokens to use: exact names for color, spacing, type, radius, shadow, motion
- New tokens: names and values to add to the system BEFORE use (or "none")

## Pattern to copy
- path/to/Existing.tsx:12-48 (structure and composition)
- path/to/other.css:5-30 (state styling)

## Files
- Create: ...
- Modify: ...
- Do not touch: ...

## States and behavior
Default, hover, active, focus-visible, disabled, loading, empty, error, as applicable.
Scroll owner for any shell. Reduced-motion behavior for any animation.

## Constraints
- Framework and styling approach already in the project; no new infrastructure
- Only installed dependencies; do not install packages or run npx
- No raw hex, arbitrary px, or one-off radii outside the token set
- Animate only transform, opacity, filter
- Accessibility target (e.g. WCAG 2.2 AA)

## Done when
- [ ] Each listed file exists or is changed as described
- [ ] Grep of changed styles finds no raw color or arbitrary px outside tokens
- [ ] Every listed state is implemented
- [ ] Project diagnostics, lint, type check, and build pass (commands: ...)
- [ ] The surface renders at <route or story> without console errors
```

## Delegation

Use the Task tool:

- `subagent_type`: `omo-orchestrator:omo-implementer`
- `description`: short, for example `Frontend: pricing page hero`
- `prompt`: the full brief, plus: "Follow the design system. Use tokens, never hardcoded visual values. If a needed token is missing, add it to the system first. Stop when every Done when item is met and report changed files and validation results."

Split independent file sets across separate implementers in one message. Keep dependent work (new tokens before components that use them, primitives before screens) in order.

## After The Implementer Returns

1. Read the diff, not just the report.
2. Run the token audit and consistency checklist from SKILL.md Phase 5.
3. Send confirmed gaps back to the same implementer with the exact file:line and fix.
4. Only then run `omo-visual-qa` on the rendered surface.
