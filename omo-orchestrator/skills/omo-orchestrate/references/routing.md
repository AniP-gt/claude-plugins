# Intent Routing

Use this before the first delegation of a request. State the routing decision in one line: "Intent: <type>, because <reason>. Approach: <route>."

## Intent map

| Surface form | True intent | Route |
|---|---|---|
| "explain X", "how does Y work" | Research | `omo-researcher` / `omo-librarian` in parallel, then synthesize an answer |
| "implement X", "add Y", "create Z" | Implementation | plan when the planning threshold applies, then `omo-implementer` |
| "look into X", "check Y", "investigate" | Investigation | `omo-researcher`, report findings; no edits |
| "what do you think about X?" | Evaluation | evaluate, propose, then wait for user confirmation before any edit |
| "I'm seeing error X", "Y is broken" | Fix | diagnose root cause (`omo-debugging`), then a minimal fix; no refactor while fixing |
| "refactor", "improve", "clean up" | Open-ended change | codebase assessment first, then propose an approach (`omo-refactor`, `omo-remove-ai-slop`) |
| "review this", PR link | Review | `omo-reviewer` or `omo-review`; implement plus review goes to `omo-review-loop` |

## Request size

| Type | Signal | Action |
|---|---|---|
| Trivial | one file, known location, direct answer | one small delegation or a direct answer from evidence already read |
| Explicit | specific file or line, clear command | delegate directly without a plan |
| Exploratory | "how does X work", "find Y" | fan out 2 to 5 read-only researchers in parallel |
| Open-ended | improve, refactor, add feature | codebase assessment, then plan |
| Ambiguous | unclear scope, several readings | ask one clarifying question |

## Ambiguity thresholds

- One valid reading: proceed.
- Several readings with similar effort: proceed with a reasonable default and record the assumption.
- Several readings where effort differs 2x or more: ask before delegating.
- Missing critical input (file, error text, environment): ask.
- The requested design looks flawed or contradicts established patterns: raise the concern before implementing.

## Codebase assessment (open-ended work)

Check linter, formatter, and type configs, sample 2 to 3 similar files, and note age signals in dependencies.

| State | Signals | Action |
|---|---|---|
| Disciplined | consistent patterns, configs, tests | follow existing style strictly |
| Transitional | mixed patterns, partial structure | ask which pattern to follow |
| Legacy or chaotic | no consistency, outdated patterns | propose conventions and wait for OK |
| Greenfield | new or empty project | apply current best practice |

Before labeling a codebase undisciplined, rule out intentional per-area patterns, an in-progress migration, and wrong reference files.

## Search stop conditions

Stop exploring when there is enough context to proceed, the same facts repeat across sources, or 2 search rounds added nothing new.

## Delegation matrix

| Task | Owner |
|---|---|
| Codebase search, patterns, bug hypotheses | `omo-researcher` (several in parallel for broad searches) |
| External library docs, upstream source | `omo-librarian` |
| PDF, image, diagram content | `omo-media-reader` |
| Pre-planning gap analysis | `omo-plan-consultant` |
| File-level plan | `omo-planner`; hard or risky work: `omo-hyperplan` |
| Plan executability check | `omo-plan-reviewer` |
| Implementation and fixes | `omo-implementer` |
| Implement plus review loop | `omo-review-loop` |
| Change review | `omo-reviewer` |
| Architecture tradeoffs, hard debugging after repeated failures | `omo-oracle` |

## Templates

Challenge the user:

```text
I notice <observation>. This may cause <problem> because <reason>.
Alternative: <suggestion>.
Proceed with the original request, or try the alternative?
```

Clarify:

```text
Understood: <interpretation>
Unsure about: <specific ambiguity>
Options:
1. <A>: <effort and implications>
2. <B>: <effort and implications>
Recommendation: <choice and reason>
```
