---
name: query
description: Answer questions based on the LLM Wiki. Use when asked about past design decisions, specs, incident responses, or terms, or when unsure about a spec or its history during work. When the wiki has no answer, searches context-mode records and other sources, and writes good answers and corrections back to the wiki without asking. Use when asked to look something up in the wiki or how something was decided before.
---

# LLM Wiki: Query

## 1. Find the wiki

Get `<wiki>` with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py resolve`. If it fails, point the user to `/llm-wiki:setup`.

## 2. Answer from the wiki

1. Read `<wiki>/index.md` and pick pages that look relevant. If none are found, Grep inside `<wiki>` (including `raw/`).
2. Read the chosen pages and their links, then answer. If a page you use for the answer has `repo://` evidence, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py check-claims --page <path relative to the wiki>`. Confirm `stale` or `missing` facts against the code before answering. If something needs fixing, write it back in step 4.
3. Cite the source pages in the answer as paths relative to `<wiki>`. Mark speculative parts as speculation.

## 3. When the wiki has no answer

Search in this order. Stop once you find the answer.

1. For anything the code can confirm, investigate the repository.
2. For the history of past sessions (what was tried, why it was rejected), search with context-mode `ctx_search`. The tool is deferred, so first load it with `ToolSearch` using `select:mcp__plugin_context-mode_context-mode__ctx_search`. Pass several paraphrases together in `queries`, and use `sort: "timeline"` to include past sessions. To also see records from repositories other than the current one, add `project: "global"`.
3. Only when an MCP server for another memory tool such as MemPalace is available, search it too.

context-mode records are automatically captured fragments and are unverified. When you use them in an answer, confirm them against code or sources, and mark anything you cannot confirm as speculation.
- State explicitly that an answer found outside the wiki was "not in the wiki". If it looks reusable, write it back in step 4.

## 4. Write back

Update the wiki without asking the user in these cases.

- The answer you found looks reusable (reasons for design decisions, gotchas, procedures, and so on)
- A wiki statement disagrees with the code or sources and you judge it needs fixing (the code wins)

Update raw/, pages, index.md, and log.md following the "Language" section and steps 1 and 3-4 of the ingest skill. Write what you write back in English (answer the user in the user's language). Use `Query` in the log.
Mention the updated pages in one line at the end of the answer.
