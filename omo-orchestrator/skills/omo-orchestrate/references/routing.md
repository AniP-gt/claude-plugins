# Intent Routing

Use this before the first delegation of a request. State the routing decision in one line: "Intent: <type>, because <reason>. Approach: <route>."

## Intent map

| Surface form | True intent | Route |
|---|---|---|
| "explain X", "how does Y work" | Research | `omo-researcher` / `omo-librarian` in parallel, then synthesize an answer |
| "implement X", "add Y", "create Z" | Implementation | plan when the planning threshold applies, then the implementation lane (Codex through `references/codex-implementer.md` when it applies, else `omo-implementer`) |
| "look into X", "check Y", "investigate" | Investigation | `omo-researcher`, report findings; no edits |
| "what do you think about X?" | Evaluation | evaluate, propose, then wait for user confirmation before any edit |
| "I'm seeing error X", "Y is broken" | Fix | diagnose root cause (`omo-programming` mode `debugging`), then a minimal fix; no refactor while fixing |
| "refactor", "improve", "clean up" | Open-ended change | codebase assessment first, then propose an approach (`omo-programming` mode `refactor`, `omo-remove-ai-slop`) |
| "write tests", "test cases for X", "add specs" for existing code | Test design | `omo-test-design`: detect the existing spec style, derive cases, approve the case table, then write specs. A feature or fix that also needs tests stays Implementation; `omo-implement` calls `omo-test-design` itself |
| "review this", PR link | Review | `omo-reviewer` or `omo-review`; implement plus review goes to `omo-review` mode `review-loop` |

## Request size

| Type | Signal | Action |
|---|---|---|
| Trivial | one file, known location, direct answer | one small delegation or a direct answer from evidence already read |
| Explicit | specific file or line, clear command | delegate directly without a plan only for a typo, wording, or config value change; any other change goes through `omo-plan` first |
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
| Codebase search, patterns, references | `omo-researcher` (several in parallel for broad searches) |
| Bug hypotheses (why something fails, not where it is) | `omo-researcher` with `model: "sonnet"`; Haiku stays on lookups whose mistakes are cheap to spot |
| External library docs, upstream source | `omo-librarian` |
| PDF, image, diagram content | Main context Reads PDFs/images directly (`pages` for PDFs); bulk extraction to `omo-researcher` |
| Pre-planning gap analysis | `omo-plan-consultant` |
| File-level plan | `omo-planner`; hard or risky work: `omo-plan` mode `hyperplan` |
| Plan executability check (a written plan file or omo-plan draft; not todo lists) | `omo-plan-reviewer` |
| Implementation and fixes | Implementation lane: Codex through `references/codex-implementer.md` when it applies, else `omo-implementer` |
| Standalone visual explanation, chart, table, or diagram | `omo-frontend` mode `visualize`, implementation through the implementation lane (row above), then `omo-implement` mode `visual-qa`. The controller puts the absolute MODE.md path for each requested mode in the worker brief (resolve `<plugin-root>` per `skills/omo-orchestrate/references/skill-catalog.md`). |
| Implement plus review loop | `omo-review` mode `review-loop` |
| Change review | `omo-reviewer` |
| Architecture tradeoffs, debugging after 2+ failed fix attempts | `omo-oracle`; for the debugging case and `HEAVY` plan review, also the Codex consult in `references/codex-consult.md` |
| Research that also writes files (wiki or docs lanes) | `omo-researcher` lanes read and return facts; one `omo-implementer` with a prose-only scope writes |
| Long command-driven verification (local real runs, Docker scenarios) | `omo-implementer` with a verification-only scope and the work budget from `omo-guardrails` |

Implementation lane: when `references/codex-implementer.md` applies (inside Orca, and an approved `omo-plan` exists for the change or `omo-ultrawork` runs), the implementation or fix pass goes to Codex through that protocol. Otherwise dispatch `omo-implementer`. It runs on Sonnet; pass `model: "opus"` for multi-file work with a real integration surface, and for a migration or a performance optimization even when its spec is clear. Whenever an approved plan exists or ulw runs but the lane did not run (outside Orca included; a LIGHT change without a plan needs no record), record `codex-impl: FALLBACK - <reason>`. Claude keeps exploration, design, review, verification, real-surface QA, and commits. The two `omo-implementer` rows above (prose-only wiki or docs writer, verification-only scope) stay with `omo-implementer` by design: the first is not planned product implementation, and verification is Claude's job. Git operations also stay with `omo-implementer` because Codex never makes commits.

## Model for agents outside this matrix

`general-purpose` and skill-runner agents have no model of their own and inherit the main session's model, Opus or Fable. The built-in `Explore` agent does too in current Claude Code (it no longer always runs on Haiku): use `omo-researcher` instead, and when `Explore` is the only fit, pass `model: "haiku"`. Fable costs twice Opus per token. In one week of measured sessions they spent about three quarters of all sub-agent usage, while every `omo-*` agent together spent under 5%. Prefer a row above. When no row fits and you must use one of them, pass `model: "sonnet"` on the Agent call, or `model: "haiku"` for read-only search. Use `opus` only with a one-line reason, such as a judgment the cheaper model got wrong in this task. Do not pass `fable` to them; Fable work goes to `omo-oracle`, or to `omo-planner` in the `hyperplan` mode of `omo-plan`. Every brief also carries the work budget from `omo-guardrails` `references/context-and-handoff.md`.

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
