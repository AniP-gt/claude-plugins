---
name: omo-research
description: Read-only OMO-style research for codebase structure, existing patterns, library references, and bug hypotheses.
argument-hint: [question]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO Research

Use this skill when the next action depends on understanding existing code or reference material.

## Research Contract

- Stay read-only.
- Search for the exact behavior, then nearby variants.
- Inspect callers and dependencies when root cause matters.
- Return paths, symbols, evidence, and recommended next steps.
- Separate facts from assumptions.

## Pick The Tool By Question

- Relationship questions (who calls this, what breaks if it changes, which tests to run): start with `node "${CLAUDE_PLUGIN_ROOT}/scripts/impact.mjs" --symbol <name>` or `--file <path>`. With no arguments it covers every changed file. It returns callers and tests in a few lines instead of a chain of Grep and Read results. Follow up with LSP references, `omo-ast-grep`, or a semantic code search tool when names are overloaded or reached indirectly.
- Literal questions (where a message, key, or config value appears): Grep. Index and graph tools match symbols, not arbitrary text, and miss these.
- Everything a search returns stays in the conversation for the rest of the session. Run broad or verbose searches inside a sub-agent and bring back `path:line` and the conclusion, not the matched source.

For broad research, split independent questions across agents and merge the findings before planning. Do not block the plan on a stalled research agent: after one bounded follow-up, mark the missing result as stalled or blocked, separate the evidence gap from confirmed facts, and proceed only if the remaining evidence is sufficient.
