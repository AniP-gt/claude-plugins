---
name: lint
description: Check and fix the LLM Wiki. Mechanically detects broken links, orphan pages, pages missing from the index, missing frontmatter, and changed evidence code, then reads pages to find contradictions and outdated statements. Use when asked to check or lint the wiki.
---

# LLM Wiki: Lint

## 1. Mechanical checks

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py lint` (use `--wiki <path>` for an unregistered wiki). It returns the following JSON.

| Key | Meaning | Fix |
|---|---|---|
| `broken_links` | The linked page does not exist | Create the page if it should exist. Fix the link if it is a typo |
| `orphans` | No page links to it | Link it from a related page or index.md |
| `not_in_index` | Not listed in index.md | Add it to the matching section of index.md |
| `missing_frontmatter` | No frontmatter | Add it in the format of `<wiki>/CLAUDE.md` |
| `missing_updated` | No `updated` | Fill in the best date you can determine |

Next, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py check-claims` (same `--wiki` as lint). For each `repo://<project>/<path>#L<a>-L<b>@<sha>` reference in a page, it checks whether those lines changed between the referenced commit and HEAD. References inside code blocks (``` and ~~~) are skipped. The comparison target is the HEAD of the registered main repository. A reference backed by an unmerged commit in a worktree is judged against the main repository's HEAD until it is merged (files that exist only in the worktree may show up as `missing`). The JSON `issues` contain these statuses.

| status | Meaning | Fix |
|---|---|---|
| `stale` | The evidence lines changed (`hunks` holds the matching diff; for binary files, `message` instead of `hunks`) | Read `git -C <repo> diff <sha> HEAD -- <path>` and the current code. If the fact changed, keep the old statement with strikethrough and a date, rewrite it, replace the reference with one recreated by `claim-ref`, and set `verified` to today. If the fact did not change, only replace the reference and update `verified` |
| `missing` | The file is not in HEAD | If `renamed_to` is present, find the lines in the new location and recreate the reference. Otherwise look for the new location, and if none is found, strike the fact through with a date |
| `unknown_commit` | The referenced commit is not in the repository (rebase or not fetched) | Run `git fetch` and retry. If it is still missing, confirm the fact against the current code and recreate the reference |
| `unknown_project` | The project name is not in projects.json | Fix the name if it is a typo. Register it with `/llm-wiki:setup` if it is unregistered |
| `invalid` | The path points outside the repository, the file is not in the referenced commit, the line range exceeds the file's line count at that commit, and so on | Recreate the reference with the correct path |
| `error` | Running git failed (reason in `message`) | Read the reason and retry. If it does not resolve, report it as open |

`shifted` holds evidence whose contents did not change but whose lines moved due to earlier changes. Just replace the reference's line range with `current` and the sha with the current value from `claim-ref`. Run `claim-ref` in the registered main repository (running it in a worktree uses the worktree's HEAD, which can disagree with `current`).

## 2. Content checks

Read `<wiki>/CLAUDE.md` and `index.md`, then read pages looking for the following. When there are many pages, focus on recently updated pages and their related pages.

- Statements that contradict each other across pages
- Statements whose `updated` is old and that likely no longer match the code or recent sources (check the repository if needed)
- Pages that mix several topics and should be split
- Duplicate pages on the same topic

## 3. Report and fix

Fix everything you judge needs fixing without asking the user. Mechanical fixes (adding to the index, filling in frontmatter, fixing links) and content fixes (resolving contradictions, updating outdated statements, splitting or merging pages) are treated the same.
Write content fixes in English, following the rules in `<wiki>/CLAUDE.md` and the "Language" section of the ingest skill. Do not delete old statements; keep them with strikethrough and a date. Do not delete pages made redundant by a merge; leave a link to the merged page.
After fixing, add `## YYYY-MM-DD Lint <summary>` in English at the top of `log.md`, and briefly report the fixes by kind.
Only items where the evidence is insufficient to decide the correct content are left unfixed and included in the report as open.
