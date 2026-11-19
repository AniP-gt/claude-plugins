# Deep Research

Deep research is an opt-in tier for hard investigation questions. The main agent runs two independent read-only investigators in the same turn, `omo-deep-researcher` (Fable, effort medium) and a Codex consult of kind `deep-research`, then merges the two answers itself. It is never the default, and it costs more than any other research route: Fable costs twice Opus per token, and the Codex run sends the brief to OpenAI.

## When

The main agent decides, by judgment. Run it when a wrong answer is expensive and a cheaper route has not settled the question:

- A root cause that crosses modules, including on a first bug investigation (a first fix attempt is still not a reason to consult `omo-oracle`).
- A design investigation that needs deep understanding of existing code before a `HEAVY` plan.
- An `omo-researcher` run with `model: "sonnet"` that came back unsure.

Do not run it for a lookup, a known file, a single keyword, a question the code already read answers, or external docs (`omo-librarian`). Run it at most once per question; a re-run needs a new question.

Who runs it: any session that has the Agent or Task tool, controllers included. A sub-agent without it returns the request (the question and relevant paths) to its caller.

## Boundary

| Route | Use for |
|---|---|
| `omo-researcher` (haiku, low; `model: "sonnet"` for bug hypotheses) | Locations, patterns, references, ordinary hypotheses |
| Deep research (this file) | Hard root cause or design investigation, before or without a failed fix |
| Debug rescue (`codex-consult.md`) with `omo-oracle` | After 2 failed fix attempts on the same problem; it takes over from deep research |
| `omo-oracle` | A judgment or tradeoff decision, plan review before `HEAVY` work |
| `omo-research` mode `ultraresearch` | Exhaustive or saturation research (`ulw research`) across many sources |

## Running

In one turn, dispatch both in parallel:

1. Agent `omo-deep-researcher`, with the question, the relevant paths, and the symptom or reproduction if there is one. No `model` override on the first run.
2. The Codex consult of kind `deep-research` in `codex-consult.md`, with the same facts.

Both get the same facts-only question. Do not send either one Claude's hypotheses, suspected cause, or the other's answer. Both stay read-only and the working tree must be unchanged afterwards, so run it only while no other lane is writing to the tree (in a controller, between waves).

## Merging

Read both answers, then classify every claim:

- Agree: both sources give it. Keep it with its `path:line`.
- One-source: only one gives it. Read the cited code before relying on it when it changes the decision.
- Conflict: they disagree. Read the cited code and decide by what it shows; never by which source sounds more certain, and never by averaging.

Keep `path:line` on every kept claim, and label its source `(fable)`, `(opus)`, or `(codex)`; an Agree claim carries both labels, such as `(fable)(codex)`. Treat the merged answer as evidence for the next step, not as a decision, and still check it against the reproduction or tests before changing code.

## Failure

- `omo-deep-researcher` refuses or returns no usable answer: re-run it once with `model: "opus"` without asking, and label the answer `(opus)`.
- Codex `NOT_EXECUTED` (not on PATH, not logged in, timeout, or the model `gpt-6.2-astra` rejected): record `codex-consult: NOT_EXECUTED - <reason>`, never re-run on another model, and use the `omo-deep-researcher` answer alone (Fable, or Opus after the fallback), keeping its label and marking it single-source.
- Codex `NOT_EXECUTED - working tree changed`: this is not an ordinary Codex failure. Stop, use neither answer, and hand the changed paths to the user (as `omo-review` `references/codex-lane.md` does). `omo-deep-researcher` has Bash, so the change may come from either side.
- Only Codex answered: use it alone, labeled single-source `(codex)`, and read the cited code for what changes the decision.
- Both fail: report both reasons and fall back to `omo-researcher` with `model: "sonnet"`.

## Cost

Run it only when the question is hard enough to justify two expensive investigators plus the merge reading. When in doubt, start with `omo-researcher`, and move to deep research only if its answer comes back unsure.
