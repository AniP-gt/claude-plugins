---
name: omo-research
description: Read-only OMO-style research for codebase structure, existing patterns, library references, and bug hypotheses. Use when a question needs codebase or library investigation before anything is decided or changed. Modes: ultraresearch (exhaustive or saturation research, `ulw research`), tech-debt-audit (tech debt, debt audit, code health), security-research (security review, vulnerability research, exploitability, threat model), coding-agent-sessions (past sessions, transcripts, subagent runs), get-unpublished-changes (changes since last release, unpublished changes, changelog).
argument-hint: [question]
allowed-tools: Read, Grep, Glob, Bash(node "${CLAUDE_PLUGIN_ROOT}/scripts/impact.mjs" *), TodoWrite, Task
user-invocable: true
---

# OMO Research

Use this skill when the next action depends on understanding existing code or reference material.

## Modes

Modes are alternative procedures kept in `modes/<mode>/MODE.md` under this skill. The flow below is the default when no mode applies.

- Selection: (a) if the first word of the arguments is a mode name, use that mode and treat the rest as the goal; (b) otherwise, if the brief has a `MODES:` line, use the modes it names; (c) otherwise judge by the "Use when" triggers in the table, and fall back to the default flow below when none fits. An unknown first word is part of the goal, so use the default flow.
- Workers: a `MODES: omo-research/<mode>` line in the brief, or a trigger in the table that matches the task even without that line, means Read that MODE.md and follow it. This also applies when this skill was preloaded through `LOAD_SKILLS`.
- Path: a mode file is `${CLAUDE_SKILL_DIR}/modes/<mode>/MODE.md`. If the variable is not expanded, append `modes/<mode>/` to this skill's Base directory. When the skill was preloaded and no Base directory is visible, call the Skill tool on `omo-research` to get it. A bare `references/...` path inside a MODE.md is relative to that mode's own `modes/<mode>/` directory. A path qualified with another skill's name (`` `omo-x` `references/y.md` `` or "the `omo-x` skill's `references/y.md`") is relative to that skill's directory. A path of the form `skills/<name>/…` is relative to the plugin root.
- Precedence: "replaces" means follow the MODE.md as the procedure, and apply the default flow below only where the MODE.md names it. "Adds to" means this file's policy stays in force and the MODE.md adds its procedure. "Main-only" means that inside a sub-agent you do not run the mode; return the steps it would need to the caller.
- Permissions: `ultraresearch` and `tech-debt-audit` need Bash and Write beyond this skill's `allowed-tools`. In the main context those commands ask for permission.

| Mode | Alias | Precedence | Use when |
|---|---|---|---|
| `ultraresearch` | - | replaces, main-only | exhaustive or saturation research on a decision-critical question; hook keyword `ulw research` |
| `tech-debt-audit` | - | replaces, main-only | tech debt, debt audit, or code health, written to a `TECH_DEBT_AUDIT.md` report |
| `security-research` | - | adds to | security review, vulnerability research, exploitability, threat model |
| `coding-agent-sessions` | - | adds to | finding past sessions, transcripts, or subagent runs |
| `get-unpublished-changes` | - | adds to | changes since the last release, unpublished changes, changelog |

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
