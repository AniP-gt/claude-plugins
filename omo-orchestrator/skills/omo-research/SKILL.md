---
name: omo-research
description: Read-only OMO-style research for codebase structure, existing patterns, library references, and bug hypotheses. Use when a question needs codebase or library investigation before anything is decided or changed.
argument-hint: [question]
allowed-tools: Read, Grep, Glob, Bash(node "${CLAUDE_PLUGIN_ROOT}/scripts/impact.mjs" *)
user-invocable: true
---

# OMO Research

Use this skill when the next action depends on understanding existing code or reference material.

## Inside A Sub-Agent

When neither the Agent nor the Task tool is available, you are running inside a sub-agent. Do not dispatch. Do the steps that fit your brief's scope yourself, and return the steps that need another agent (the `omo-oracle` consult, review lanes, parallel workers, QA by another role) to the caller as named next actions. Where this skill says to split independent questions across agents, answer the questions in your brief yourself and return the remaining independent questions to the caller.

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
