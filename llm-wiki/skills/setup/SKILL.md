---
name: setup
description: Initial setup for the LLM Wiki. Registers the mapping between the current repository and a wiki folder (for example inside an Obsidian vault) in ~/.config/llm-wiki/projects.json, and creates the wiki skeleton if needed. Use when asked to set up the wiki or run llm-wiki setup.
---

# LLM Wiki Setup

The mapping between repositories and wikis is stored in each user's local config. Do not write to the plugin or the target repository.

- Config file: `$LLM_WIKI_CONFIG`, or `~/.config/llm-wiki/projects.json` when unset
- CLI: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/llm_wiki.py <subcommand>`
- Example config: `${CLAUDE_PLUGIN_ROOT}/templates/projects.example.json`

## Steps

1. **Check the current state**: run `llm_wiki.py resolve`. If already registered, show the entry and ask whether to change it.
2. **Ask** (all in one question):
   - The wiki folder path (e.g. `~/Obsidian/MyVault/Projects/MyApp`)
   - The project name (default: the repository's directory name)
   - The target repository (default: the main root of the current repository; inside a worktree, use the main repository)
   Several repositories may share one wiki. In that case, register each repository.
3. **Register**: `llm_wiki.py add --name <name> --repo <repo> --wiki <wiki>`
4. **Skeleton**: if the wiki folder has no `index.md`, ask whether to create it, then run `llm_wiki.py init-wiki --wiki <wiki>`. Existing files are not overwritten.
5. **Automatic candidate extraction**: ask whether to use it. If yes, run `llm_wiki.py capture-config --enable` (add `--model <name>` to change the model; default sonnet).
   - Every time a session in a registered repository ends, it calls `claude -p` once in the background and saves candidates worth keeping in the wiki from the conversation to `<wiki>/raw/inbox/`. Pages are not updated at that point. At the start of the next session, the candidates are triaged automatically without asking and reflected in pages.
   - This consumes tokens. Short sessions whose conversation (excluding tool input and output) is under 3000 characters are skipped.
   - The setting is shared by all projects. Turn it off with `--disable`. The log is `~/.config/llm-wiki/capture.log`.
6. **Verify**: show the output of `llm_wiki.py resolve`, `llm_wiki.py list`, and `llm_wiki.py capture-config`.
7. **Guide**: tell the user that from the next Claude Code session, the SessionStart hook automatically provides the wiki location and table of contents. Then suggest ingesting the first source with `/llm-wiki:ingest`.

## Notes

- When the wiki is outside the repository (such as in a vault), the sandbox may deny writes. In that case, ask the user whether to allow it with `/sandbox`.
- To remove a registration, run `llm_wiki.py remove --name <name>`.
