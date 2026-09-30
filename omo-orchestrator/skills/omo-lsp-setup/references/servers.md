# Language Server Reference

Per-language server, install options, verify command, and common pitfalls. Derived from oh-my-openagent `lsp-setup/references/*`. "Official plugin" means a plugin in the `claude-plugins-official` marketplace.

Always ask before running an install command. Never start a server through `npx`.

## TypeScript / JavaScript

- Server: `typescript-language-server --stdio` (needs the `typescript` package for `tsserver`).
- Official plugin: `typescript-lsp`.
- Install: `npm install -g typescript-language-server typescript`.
- Verify: `typescript-language-server --version`.
- Alternatives: `deno lsp` (Deno projects), `biome lsp-proxy` (Biome), `vscode-eslint-language-server --stdio` (from `npm install -g vscode-langservers-extracted`), `oxlint --lsp`, `vue-language-server --stdio`, `svelteserver --stdio`, `astro-ls --stdio`. Choose from `package.json` / `deno.json` evidence.
- Pitfalls:
  - "Could not find tsserver": `typescript` is missing globally and in `node_modules`.
  - Binary not on PATH after global install: check `npm prefix -g`, add its `bin`, reopen the shell.

## Python

- Server: `basedpyright-langserver --stdio` (upstream default). Official plugin `pyright-lsp` runs `pyright-langserver --stdio`.
- Install: `uv tool install basedpyright` (uv projects) or `pip install basedpyright`. For the official plugin: `pip install pyright` or `uv tool install pyright`.
- Verify: `basedpyright --version` or `pyright --version`; sanity check `basedpyright path/to/file.py`.
- Alternatives: `ty server` (Astral, experimental), `ruff server` (lint and format only, runs alongside a type server, never instead of one).
- Pitfalls:
  - Missing imports: the server does not see the project venv. Set `venvPath` / `venv` in `pyrightconfig.json` or `[tool.basedpyright]` / `[tool.pyright]` in `pyproject.toml`.
  - `uv tool install` writes to `~/.local/bin`; make sure it is on PATH.

## Go

- Server: `gopls`. Official plugin: `gopls-lsp`.
- Install: `go install golang.org/x/tools/gopls@latest`, or `brew install gopls` on macOS.
- Verify: `gopls version`; sanity check `gopls check path/to/file.go`.
- Pitfalls:
  - `$(go env GOPATH)/bin` (default `~/go/bin`) not on PATH.
  - No diagnostics or "no required module": the workspace root must contain `go.mod`. Run `go mod tidy` if deps are unresolved.
  - After a Go upgrade, reinstall gopls.

## Rust

- Server: `rust-analyzer`. Official plugin: `rust-analyzer-lsp`.
- Install: `rustup component add rust-analyzer rust-src` (preferred, pinned to toolchain), or `brew install rust-analyzer`.
- Verify: `rust-analyzer --version`; sanity check `cargo check`.
- Pitfalls:
  - Crash while indexing std: reinstall `rust-src` (`rustup component remove rust-src && rustup component add rust-src`).
  - Proc macros or build scripts fail: fix `cargo check` first.
  - rustup shims live in `~/.cargo/bin`.

## C / C++

- Server: `clangd` (upstream passes `--background-index --clang-tidy`). Official plugin: `clangd-lsp`.
- Install: macOS `brew install llvm` (keg-only, add `$(brew --prefix llvm)/bin` to PATH); Debian/Ubuntu `apt install clangd`; Windows `winget install LLVM.LLVM`. Other platforms: https://clangd.llvm.org/installation.
- Verify: `clangd --version`; sanity check `clangd --check=path/to/file.cpp`.
- Pitfalls:
  - Spurious "file not found" or unknown flags: missing or stale `compile_commands.json`. Generate with `cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON` (link it to the root) or `bear -- make`.
  - Headers analyzed wrong: add a `.clangd` `CompileFlags` block.
- Alternative: `ccls` (third party, needs a custom plugin).

## Java

- Server: `jdtls`. Official plugin: `jdtls-lsp` (sets a long `startupTimeout`).
- Install: macOS `brew install jdtls`; elsewhere download a release from https://github.com/eclipse-jdtls/eclipse.jdt.ls and put the `jdtls` launcher on PATH.
- Prerequisite: JDK 17+ to run the server (the project may target older Java).
- Verify: `command -v jdtls` and `java -version` (17+); then a diagnostics run on one `.java` file.
- Pitfalls:
  - Exits immediately: no JDK 17+. Set `JAVA_HOME`.
  - First index is slow on large Maven/Gradle projects; wait.
  - Wrong results after big dependency changes: delete the jdtls workspace data dir to re-index.
  - Broken `pom.xml` / `build.gradle` breaks symbol resolution.

## Kotlin

- Server: `kotlin-lsp` (JetBrains, pre-release). Official plugin: `kotlin-lsp` (runs `kotlin-lsp --stdio`).
- Install: download a release from https://github.com/Kotlin/kotlin-lsp and symlink the launcher onto PATH as `kotlin-lsp`.
- Prerequisite: a JDK.
- Verify: `command -v kotlin-lsp`, then a diagnostics run on one `.kt` file.
- Pitfalls:
  - Pre-release churn: pin a known-good release.
  - Slow first Gradle import; `.kts` files resolve slower than `.kt`.
- Alternative: `fwcd/kotlin-language-server` (older, community).

## C#

- Server: `csharp-ls`. Official plugin: `csharp-lsp`.
- Install: `dotnet tool install -g csharp-ls` (needs the .NET SDK, not only the runtime).
- Razor / Blazor (`.razor .cshtml`): `roslyn-language-server --stdio`, install `dotnet tool install -g roslyn-language-server --prerelease` (v5.8.0+). No official plugin.
- Verify: `command -v csharp-ls` and `dotnet tool list -g`.
- Pitfalls:
  - `~/.dotnet/tools` (Windows `%USERPROFILE%\.dotnet\tools`) not on PATH.
  - Empty results: run `dotnet restore` on the `.sln` / `.csproj`.
- Alternative: OmniSharp (legacy).

## Swift

- Server: `sourcekit-lsp` (ships with Xcode or the swift.org toolchain). Official plugin: `swift-lsp`.
- Install: macOS `xcode-select --install` or full Xcode; Linux/Windows install the swift.org toolchain and add its `usr/bin` to PATH.
- Verify: `xcrun sourcekit-lsp --help` on macOS, or `command -v sourcekit-lsp`; `swift --version`.
- Pitfalls:
  - Wrong toolchain on macOS: fix with `xcode-select -s`.
  - Poor resolution without `Package.swift` or a `compile_commands.json`.
  - Objective-C files need a compilation database.

## Ruby

- Upstream default runs `rubocop --lsp` (diagnostics, formatting, code actions). Official plugin `ruby-lsp` runs the Shopify `ruby-lsp` binary.
- Install: `gem install ruby-lsp` for the official plugin; `gem install rubocop` for the RuboCop server. In Bundler projects prefer adding gems to the `Gemfile`.
- Verify: `ruby-lsp --version` or `rubocop --version`.
- Pitfalls:
  - The binary that runs must be on PATH, not only the other gem.
  - Version mismatch with the `Gemfile` pin: run inside the bundle.
  - No diagnostics: invalid or overly permissive `.rubocop.yml`.
- Alternative: `solargraph stdio`.

## PHP

- Server: `intelephense --stdio` (Node package). Official plugin: `php-lsp`.
- Install: `npm install -g intelephense` (Node required).
- Verify: `intelephense --version` or `command -v intelephense`.
- Pitfalls:
  - Premium features (rename, implementations) need a licence key; free mode works without one.
  - Wrong PHP version inferred: set `intelephense.environment.phpVersion`.
- Alternative: `phpactor language-server` (pure PHP, no Node).

## Dart

- Server: `dart language-server --lsp` (bundled with the Dart or Flutter SDK). No official plugin.
- Install: `brew install dart`, or install Flutter and use its bundled `dart`; add the SDK `bin` to PATH.
- Verify: `dart --version`; sanity check `dart analyze`.
- Pitfalls: Flutter-only installs must have Flutter's `bin` on PATH; outdated SDK misreads new language features.

## Elixir

- Server: `elixir-ls`. No official plugin.
- Install: macOS `brew install elixir-ls`; elsewhere build from https://github.com/elixir-lsp/elixir-ls (`mix deps.get && mix compile && mix elixir_ls.release2 -o release`) and add `release/` to PATH.
- Verify: `command -v elixir-ls`, `elixir --version`.
- Pitfalls: asdf users run `asdf reshim elixir`; build with the same Erlang/Elixir as the project; first start compiles deps and is slow.
- Alternatives: `lexical`, `nextls --stdio`.

## Zig

- Server: `zls`. No official plugin.
- Install: `brew install zls`, or a prebuilt release matching your Zig version, or build from source.
- Verify: `zls --version` and `zig version`; the two must match.
- Pitfalls: version mismatch causes crashes or silent failures; rebuild zls after every Zig upgrade; `zig` itself must be on PATH.

## Lua

- Server: `lua-language-server`. Official plugin: `lua-lsp`.
- Install: `brew install lua-language-server`, Arch `pacman -S lua-language-server`, or a GitHub release from https://github.com/LuaLS/lua-language-server.
- Verify: `lua-language-server --version`.
- Pitfalls: undefined `vim` global in Neovim configs (set `diagnostics.globals` and `workspace.library` in `.luarc.json`); wrong `runtime.version` (`LuaJIT`, `Lua 5.4`) flags stdlib as undefined.

## Bash

- Server: `bash-language-server start`. No official plugin.
- Install: `npm install -g bash-language-server`, plus `shellcheck` (`brew install shellcheck`, `apt install shellcheck`, `scoop install shellcheck`).
- Verify: `bash-language-server --version` and `shellcheck --version`.
- Pitfalls: no diagnostics without `shellcheck`; `.zsh` / `.ksh` are linted as bash.

## YAML

- Server: `yaml-language-server --stdio`. No official plugin.
- Install: `npm install -g yaml-language-server`.
- Verify: `command -v yaml-language-server`.
- Pitfalls: no validation until a schema matches (add a `# yaml-language-server: $schema=<url>` modeline or configure `yaml.schemas`); SchemaStore may guess the wrong schema by filename.

## Terraform

- Server: `terraform-ls serve`. No official plugin.
- Install: macOS `brew install hashicorp/tap/terraform-ls`; Linux via HashiCorp releases or apt/dnf repo; Windows `choco install terraform-ls`. `terraform` must also be on PATH.
- Verify: `terraform-ls version` and `terraform version`; sanity check `terraform validate`.
- Pitfalls: no provider completion until `terraform init` runs in each module root; `.tfvars` need the containing module opened.

## Haskell

- Server: `haskell-language-server-wrapper --lsp`. No official plugin.
- Install: `ghcup install hls` (with `ghcup install ghc` and `ghcup install cabal` first).
- Verify: `haskell-language-server-wrapper --version`; `haskell-language-server-wrapper` in the project root also reports the GHC it detected.
- Pitfalls: HLS must support the project's GHC; multi-package repos may need a `hie.yaml` (`gen-hie > hie.yaml`); first load compiles deps.

## Julia

- Server: `julia --startup-file=no --history-file=no -e "using LanguageServer; runserver()"`. The PATH binary is `julia`. No official plugin.
- Install: Julia via juliaup (`brew install juliaup`, the official installer, or `winget install julia -s msstore`), then `julia --project=@lsp -e 'using Pkg; Pkg.add("LanguageServer")'`.
- Verify: `julia --version` and `julia --project=@lsp -e 'using LanguageServer'`.
- Pitfalls: first launch precompiles for minutes with no output, do not kill it; `LanguageServer` must be in the environment the server runs in (set `JULIA_PROJECT=@lsp`).
