#!/usr/bin/env node
// PreToolUse hook (matcher Write|Edit|MultiEdit): production code is not edited on a branch where no test file has
// changed yet. "Write the failing test first" is a prose rule in omo-implement that an agent skips under load and
// then adds tests after the fact, or never. The gate makes the order a precondition of the edit itself.
// Gated: a source file (by extension) that is not a test path. Never gated: test paths (directory names match case
// insensitively), non-code files (docs, data), config files (`*.config.*`, `*.conf.*`, dotfiles such as `.eslintrc.js`),
// and paths git ignores (`git check-ignore`, so node_modules/ and dist/ edits pass).
// Allowed once any test path appears in the branch's change set: `git diff --name-only <base>` (committed and working
// tree changes) plus untracked files, where <base> is the merge-base of HEAD with the default branch
// (origin/HEAD, then origin/main, origin/master, main, master). A change that needs no test (wording, docs, renames,
// config values, wiring with no branch) is declared in `<repo>/.claude/omo/tdd-exempt/<branch>.txt`, one
// `<repo-relative path or glob>: <reason>` per line; a line without a reason does not count. A branch name is used as a
// relative path (`pbi/33` -> `tdd-exempt/pbi/33.txt`); a detached HEAD uses `HEAD.txt`, which no branch can be named.
// The hook fails open: malformed input, a non-git directory, no resolvable base, or any git error or timeout allows the edit.
// OMO_TDD_GATE=off|0|false disables it.
// The gate is an ordering check that makes the agent decide, not a security boundary.
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const GATED_TOOLS = new Set(["Write", "Edit", "MultiEdit"]);
const SOURCE_EXTENSIONS = new Set([
  ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".php", ".cs",
  ".c", ".cc", ".cpp", ".h", ".hpp", ".scala", ".ex", ".exs", ".vue", ".svelte", ".dart",
]);
// Compared lower-cased: `Tests/` (Swift, C#), `Test/`, `Spec/`, `androidTest/`, `testFixtures/` are all test directories.
const TEST_DIRECTORIES = new Set([
  "test", "tests", "spec", "__tests__", "e2e", "__mocks__", "__fixtures__", "testdata", "fixtures", "androidtest", "testfixtures", "cypress", "playwright",
]);
// A C# test project directory: `MyApp.Tests/`, `MyApp.Test/`.
const TEST_PROJECT_DIRECTORY = /\.tests?$/i;
const TEST_FILE_PATTERNS = [
  /\.test\./, /\.spec\./, /\.cy\./, /_test\.go$/, /^test_.*\.py$/, /_test\.py$/, /_spec\./, /^(?:tests|conftest)\.py$/,
  /(?:Test|Tests)\.(?:swift|kt|java|cs|php|scala)$/, /Spec\.(?:kt|scala|groovy)$/,
];
const CONFIG_FILE_PATTERN = /\.(?:config|conf)\./i;
const DEFAULT_BRANCH_FALLBACKS = ["origin/main", "origin/master", "main", "master"];
const GIT_TIMEOUT_MS = 1500;
const EXEMPT_DIRECTORY = join(".claude", "omo", "tdd-exempt");
const EXEMPT_LINE_PATTERN = /^([^:]+?)\s*:\s*(\S.*)$/;

// Runs git in `cwd` and returns its stdout, or undefined when git fails, times out, or is missing.
export type GitRunner = (cwd: string, args: string[]) => string | undefined;
type RunOptions = { env?: NodeJS.ProcessEnv; git?: GitRunner };
// PreToolUse hook input as read from stdin; every field is checked at runtime before use.
type HookInput = { hook_event_name?: unknown; tool_name?: unknown; tool_input?: unknown; cwd?: unknown };
type ToolInput = { file_path?: unknown };

const runGit: GitRunner = (cwd, args) => {
  try {
    return execFileSync("git", args, {
      cwd,
      encoding: "utf8",
      timeout: GIT_TIMEOUT_MS,
      stdio: ["ignore", "pipe", "ignore"],
      maxBuffer: 64 * 1024 * 1024,
      env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
    });
  } catch {
    return undefined;
  }
};

// `repoRelative` uses forward slashes; directories are checked on every segment above the file name.
function isTestPath(repoRelative: string): boolean {
  const segments = repoRelative.split("/");
  const name = segments[segments.length - 1] ?? "";
  const inTestDirectory = segments.slice(0, -1).some((segment) => TEST_DIRECTORIES.has(segment.toLowerCase()) || TEST_PROJECT_DIRECTORY.test(segment));
  return inTestDirectory || TEST_FILE_PATTERNS.some((pattern) => pattern.test(name));
}

const isConfigFile = (repoRelative: string): boolean => {
  const name = basename(repoRelative);
  return name.startsWith(".") || CONFIG_FILE_PATTERN.test(name);
};

const hasSourceExtension = (path: string): boolean => {
  const name = basename(path);
  const dot = name.lastIndexOf(".");
  return dot > 0 && SOURCE_EXTENSIONS.has(name.slice(dot).toLowerCase());
};

export function isProductionCode(repoRelative: string): boolean {
  return hasSourceExtension(repoRelative) && !isTestPath(repoRelative) && !isConfigFile(repoRelative);
}

// The file may not exist yet, so resolve the deepest existing ancestor (symlinks such as the macOS tmp dir included)
// and re-append the missing tail.
function resolveFromExistingAncestor(absolute: string): { directory: string; tail: string[] } {
  const tail: string[] = [];
  let current = dirname(absolute);
  tail.unshift(basename(absolute));
  while (!existsSync(current)) {
    const parent = dirname(current);
    if (parent === current) break;
    tail.unshift(basename(current));
    current = parent;
  }
  return { directory: realpathSync(current), tail };
}

function defaultBranchBase(git: GitRunner, repo: string): string | undefined {
  const originHead = git(repo, ["symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD"])?.trim();
  const candidates = [...(originHead ? [originHead] : []), ...DEFAULT_BRANCH_FALLBACKS];
  for (const ref of candidates) {
    const base = git(repo, ["merge-base", "HEAD", ref])?.trim();
    if (base) return base;
  }
  return undefined;
}

const splitNul = (text: string): string[] => text.split("\0").filter((entry) => entry.length > 0);

// Paths changed on this branch: committed and working-tree changes against the base, plus untracked files.
function changedPaths(git: GitRunner, repo: string, base: string): string[] | undefined {
  const tracked = git(repo, ["-c", "core.quotepath=off", "diff", "--name-only", "-z", base]);
  const untracked = git(repo, ["-c", "core.quotepath=off", "ls-files", "--others", "--exclude-standard", "-z"]);
  if (tracked === undefined || untracked === undefined) return undefined;
  return [...splitNul(tracked), ...splitNul(untracked)];
}

// `**` crosses directories (`**/` also matches none), `*` and `?` stay inside one path segment.
function globToRegExp(glob: string): RegExp {
  let source = "";
  for (let index = 0; index < glob.length; index++) {
    const char = glob[index];
    if (char === "*" && glob[index + 1] === "*") {
      if (glob[index + 2] === "/") {
        source += "(?:.*/)?";
        index += 2;
      } else {
        source += ".*";
        index += 1;
      }
    } else if (char === "*") source += "[^/]*";
    else if (char === "?") source += "[^/]";
    else source += char.replace(/[.+^${}()|[\]\\]/g, "\\$&");
  }
  return new RegExp(`^${source}$`);
}

function isExempt(exemptFile: string, repoRelative: string): boolean {
  let text: string;
  try {
    text = readFileSync(exemptFile, "utf8");
  } catch {
    return false;
  }
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) continue;
    const match = EXEMPT_LINE_PATTERN.exec(line);
    if (match === null) continue;
    const pattern = match[1].trim().replace(/^\.\//, "");
    if (pattern === repoRelative || globToRegExp(pattern).test(repoRelative)) return true;
  }
  return false;
}

function deny(reason: string): string {
  const output = {
    hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: reason },
  };
  return `${JSON.stringify(output)}\n`;
}

function denyReason(repoRelative: string, base: string, exemptFile: string): string {
  return [
    `No test file has changed on this branch since ${base.slice(0, 12)} (the merge-base with the default branch), and ${repoRelative} is production code.`,
    "Write or modify a failing test first (a new or changed test path anywhere in the repo counts, an untracked file included), run it and watch it fail for the expected reason, then retry this edit.",
    "If this change needs no test (wording, docs, renames, config values, wiring that adds no branch), declare it instead: append one line to the exemption file with the exact path and the reason, then retry.",
    `Exemption file (absolute path): ${exemptFile}`,
    `Line to add: ${repoRelative}: <why no test is needed>`,
    "Languages with inline tests (Rust `#[cfg(test)]` modules, Python doctests) keep the test in the same file, which this gate cannot see: declare that file in the exemption file with the reason instead.",
    "A line without a reason does not count. Set OMO_TDD_GATE=off to disable this gate.",
  ].join("\n");
}

export function run(input: unknown, { env = process.env, git = runGit }: RunOptions = {}): string {
  if (typeof input !== "object" || input === null) return "";
  const hookInput = input as HookInput;
  if (hookInput.hook_event_name !== undefined && hookInput.hook_event_name !== "PreToolUse") return "";
  if (typeof hookInput.tool_name !== "string" || !GATED_TOOLS.has(hookInput.tool_name)) return "";
  if (/^(off|0|false)$/i.test(env.OMO_TDD_GATE ?? "")) return "";
  const rawToolInput = hookInput.tool_input;
  if (typeof rawToolInput !== "object" || rawToolInput === null) return "";
  const filePath = (rawToolInput as ToolInput).file_path;
  if (typeof filePath !== "string" || filePath.trim() === "") return "";
  if (!hasSourceExtension(filePath)) return "";

  const base = typeof hookInput.cwd === "string" && isAbsolute(hookInput.cwd) ? hookInput.cwd : process.cwd();
  let located: { directory: string; tail: string[] };
  try {
    located = resolveFromExistingAncestor(resolve(base, filePath));
  } catch {
    return "";
  }
  const repo = git(located.directory, ["rev-parse", "--show-toplevel"])?.trim();
  if (!repo) return "";
  const repoRelative = relative(repo, join(located.directory, ...located.tail)).split(sep).join("/");
  if (repoRelative === "" || repoRelative.startsWith("../") || isAbsolute(repoRelative)) return "";
  if (!isProductionCode(repoRelative)) return "";
  // `check-ignore -q` exits 0 only for an ignored path (a tracked file is never reported); the runner maps any non-zero exit to undefined.
  if (git(repo, ["check-ignore", "-q", "--", repoRelative]) !== undefined) return "";

  const mergeBase = defaultBranchBase(git, repo);
  if (mergeBase === undefined) return "";
  const changed = changedPaths(git, repo, mergeBase);
  if (changed === undefined || changed.some(isTestPath)) return "";

  const branch = git(repo, ["symbolic-ref", "--short", "-q", "HEAD"])?.trim() || "HEAD";
  const exemptFile = join(repo, EXEMPT_DIRECTORY, `${branch}.txt`);
  if (isExempt(exemptFile, repoRelative)) return "";
  return deny(denyReason(repoRelative, mergeBase, exemptFile));
}

async function readStdin(): Promise<string> {
  let data = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let parsed: unknown;
  try {
    parsed = JSON.parse(await readStdin());
  } catch {
    parsed = undefined;
  }
  const output = run(parsed);
  if (output.length > 0) process.stdout.write(output);
}
