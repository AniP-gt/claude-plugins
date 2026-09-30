---
name: omo-lsp-setup
description: Detect which language servers a project needs, propose install commands, wire a Claude Code LSP plugin, and verify the server really answers. Never installs without asking.
argument-hint: [language-or-project]
allowed-tools: Read, Grep, Glob, Bash
user-invocable: true
---

# OMO LSP Setup

Claude Code adaptation of oh-my-openagent `packages/shared-skills/skills/lsp-setup`.

Use this skill when a project needs a language server for diagnostics, go-to-definition, references, or rename, or when Claude Code reports no LSP server for a file type. The workflow is detect, propose, install on approval, enable, verify.

Per-language details (server, install options, verify command, pitfalls) live in `references/servers.md`. Read the matching section before proposing anything.

## How LSP works in Claude Code

- Claude Code gets LSP support from plugins that declare language servers. The plugin declares the server; it does not ship the binary.
- The server binary must be installed separately and resolve on `PATH`.
- The official marketplace (`claude-plugins-official`) has ready plugins: `typescript-lsp`, `pyright-lsp`, `gopls-lsp`, `rust-analyzer-lsp`, `clangd-lsp`, `jdtls-lsp`, `kotlin-lsp`, `csharp-lsp`, `swift-lsp`, `ruby-lsp`, `php-lsp`, `lua-lsp`. Enable one with `/plugin install <name>@claude-plugins-official`.
- For a language with no official plugin, a plugin can declare its own server under `lspServers` in its plugin manifest. Keys seen in the official plugins: `command`, `args`, `extensionToLanguage`, `startupTimeout`. Check the current Claude Code plugin docs before using any other key.
- If unsure for a given setup: install the language server binary on `PATH`, enable a Claude Code LSP plugin for that language, then verify with the server's own `--version` and a diagnostics run.

## Phase 0: Language Gate

Map the target to a language, then read its section in `references/servers.md`.

| Signal | Language |
|---|---|
| `package.json`, `tsconfig.json`, `jsconfig.json`, `deno.json`, `.ts .tsx .js .jsx .mjs .cjs` | TypeScript / JavaScript |
| `pyproject.toml`, `requirements*.txt`, `setup.py`, `uv.lock`, `.py .pyi` | Python |
| `go.mod`, `.go` | Go |
| `Cargo.toml`, `.rs` | Rust |
| `CMakeLists.txt`, `Makefile`, `compile_commands.json`, `.c .cpp .h .hpp` | C / C++ |
| `pom.xml`, `build.gradle`, `.java` | Java |
| `build.gradle.kts`, `.kt .kts` | Kotlin |
| `*.sln`, `*.csproj`, `.cs .razor .cshtml` | C# |
| `Package.swift`, `*.xcodeproj`, `.swift` | Swift |
| `Gemfile`, `.rb .rake .gemspec .ru` | Ruby |
| `composer.json`, `.php` | PHP |
| `pubspec.yaml`, `.dart` | Dart |
| `mix.exs`, `.ex .exs` | Elixir |
| `build.zig`, `build.zig.zon`, `.zig` | Zig |
| `.luarc.json`, `.lua` | Lua |
| `.sh .bash .zsh .ksh` | Bash |
| `.yaml .yml` | YAML |
| `.tf .tfvars` | Terraform |
| `stack.yaml`, `*.cabal`, `.hs .lhs` | Haskell |
| `Project.toml`, `.jl` | Julia |

## Workflow

### 1. Detect

Inspect, do not guess.

- Use Glob for the manifests above at the project root and one or two levels down (monorepos). Skip `node_modules`, `vendor`, `target`, `.venv`, `dist`, `build`.
- Read the manifests that matter to pick between competing servers: `package.json` (Deno, Biome, Vue, Svelte, Astro), `pyproject.toml` (`[tool.basedpyright]`, `[tool.pyright]`, `[tool.ruff]`, uv), `Gemfile` (rubocop, ruby-lsp).
- For each language, check the binary: `command -v <server>` and `<server> --version` (or the verify command in `references/servers.md`).
- Check whether a Claude Code LSP plugin for the language is already enabled (`/plugin` or `claude plugin list`).

Report a table: language, evidence file, server, binary found (yes/no, version), plugin enabled (yes/no/none available).

### 2. Propose install

- Never auto-install. Print the exact install commands for the user's OS from `references/servers.md` and ask before running any of them.
- Prefer the project's own toolchain (uv for uv projects, rustup for Rust, `go install` for Go, dotnet tools for C#).
- Never propose `npx` or any run-on-demand package runner to start a server. Servers must be installed binaries on `PATH`.
- Call out prerequisites (JDK 17+, .NET SDK, Node, GHC, matching Zig) and PATH additions (`~/go/bin`, `~/.cargo/bin`, `~/.dotnet/tools`, `~/.local/bin`).

### 3. Enable in Claude Code

- If an official plugin exists, propose `/plugin install <name>@claude-plugins-official` and ask.
- If none exists, say so and describe a minimal plugin that declares the server under `lspServers` with `command`, `args`, and `extensionToLanguage`. Do not write it unless asked.
- Note mismatches between the official plugin's command and the reference default (for example, the official `pyright-lsp` runs `pyright-langserver`, not `basedpyright-langserver`; the official `ruby-lsp` runs the `ruby-lsp` gem binary).
- Server-specific settings usually belong in the project's own config (`pyrightconfig.json`, `.clangd`, `.rubocop.yml`, `hie.yaml`, `.luarc.json`), not in Claude Code.

### 4. Verify

After install and a Claude Code restart or plugin reload:

1. `command -v <server>` resolves and `<server> --version` (or the listed equivalent) succeeds.
2. Run a diagnostics check: open a real source file from the project, request its LSP diagnostics, and confirm the server answers without a startup error.
3. If the server has a CLI check (`basedpyright`, `gopls check`, `cargo check`, `terraform validate`), run it on one file as a sanity signal.

Report `OK` only with evidence from this session. On failure, report the exact error and the matching pitfall from `references/servers.md`.

## Hard Rules

- Do not install, upgrade, or uninstall anything without explicit approval.
- Do not edit Claude Code settings or plugin manifests unless the user asks.
- Do not recommend `npx` for running servers.
- Do not claim a server works without a version check and a diagnostics result from this session.
- Do not invent plugin config keys. Use only keys confirmed in current docs or official plugins.
