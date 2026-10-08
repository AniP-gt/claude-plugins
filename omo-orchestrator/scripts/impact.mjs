#!/usr/bin/env node
// Lists who references a symbol or a changed file, and which of those are tests, in a few compact lines.
// It replaces a chain of Grep and Read calls whose raw output would otherwise stay in the conversation.
// Read-only: it runs `git grep`, `git diff`, and `git ls-files` without a shell and never writes files.
//
// Usage:
//   node impact.mjs --symbol <name> [--symbol <name>...]   callers of each symbol
//   node impact.mjs --file <path> [--file <path>...]       files that mention each file's module name
//   node impact.mjs [--base <ref>]                         same as --file for every changed file (default base HEAD)
//   --limit <n>                                            entries shown per list (default 15)
import { execFileSync } from "node:child_process";
import { existsSync, realpathSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TEST_PATTERN =
  /(^|\/)(tests?|__tests__|spec)\/|[._-](test|spec)s?\.[^/]+$|(^|\/)(test_[^/]+|conftest\.py)$|Tests?\.[^/]+$/;
// Module names that say nothing about the module; the parent directory name is searched instead.
const GENERIC_STEMS = new Set(["index", "main", "mod", "__init__", "init", "lib", "app"]);
const MIN_TERM_LENGTH = 3;
// Changed files of these kinds are skipped when no --file is given; their names are rarely imported.
const NON_CODE_PATTERN = /\.(md|mdx|txt|rst|json|ya?ml|toml|lock|csv|svg|png|jpe?g|gif|ico)$|(^|\/)\.[^/]+$/i;

export function isTestPath(file) {
  return TEST_PATTERN.test(file);
}

export function moduleTerm(file) {
  const base = path.basename(file);
  // A test file such as foo.test.ts or foo_spec.rb is searched as its subject, foo.
  const stem = base.replace(/\.[^.]+$/, "").replace(/[._-](test|spec)s?$/, "") || base;
  if (!GENERIC_STEMS.has(stem)) return stem;
  const parent = path.basename(path.dirname(file));
  return parent === "." || parent === "" ? stem : parent;
}

function git(args, cwd) {
  try {
    // Without core.quotePath=false, git prints non-ASCII paths as quoted octal escapes.
    return execFileSync("git", ["-c", "core.quotePath=false", ...args], { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024, stdio: ["ignore", "pipe", "ignore"] });
  } catch (error) {
    // git grep exits 1 when nothing matches.
    if (error.status === 1) return "";
    if (error.status === 128) throw new Error(`git ${args[0]} failed: not a git repository or unknown ref`);
    throw new Error(`git ${args[0]} failed${error.status === undefined ? "" : ` (exit ${error.status})`}`);
  }
}

// Resolves symlinks in the longest existing ancestor, so a deleted file still maps to a repository path.
function realResolve(file) {
  let dir = path.resolve(file);
  const rest = [];
  while (!existsSync(dir) && path.dirname(dir) !== dir) {
    rest.unshift(path.basename(dir));
    dir = path.dirname(dir);
  }
  return path.join(realpathSync(dir), ...rest);
}

function lines(text) {
  return text.split("\n").filter((line) => line.length > 0);
}

export function changedFiles(base, cwd) {
  const tracked = lines(git(["diff", "--name-only", base, "--"], cwd));
  const untracked = lines(git(["ls-files", "--others", "--exclude-standard"], cwd));
  return [...new Set([...tracked, ...untracked])];
}

// Returns Map<file, lineNumbers[]> for word matches of a fixed string in tracked files.
export function references(term, cwd) {
  const hits = new Map();
  for (const line of lines(git(["grep", "--untracked", "-n", "-w", "-I", "-F", "-e", term], cwd))) {
    const match = /^(.*?):(\d+):/.exec(line);
    if (match === null) continue;
    const [, file, lineNumber] = match;
    if (!hits.has(file)) hits.set(file, []);
    hits.get(file).push(Number(lineNumber));
  }
  return hits;
}

function formatList(entries, limit) {
  const shown = entries.slice(0, limit);
  const more = entries.length - shown.length;
  return more > 0 ? [...shown, `+${more} more`] : shown;
}

function formatFile(file, lineNumbers) {
  const preview = lineNumbers.slice(0, 3).map((n) => `L${n}`).join(",");
  return `${file} (${lineNumbers.length}: ${preview}${lineNumbers.length > 3 ? ",..." : ""})`;
}

export function describe(label, term, hits, { exclude = null, limit = 15 } = {}) {
  if (term.length < MIN_TERM_LENGTH) return [`${label}: skipped, search term "${term}" is too short`];
  const files = [...hits.keys()].filter((file) => file !== exclude).sort();
  const tests = files.filter(isTestPath);
  const callers = files.filter((file) => !isTestPath(file));
  const refCount = files.reduce((sum, file) => sum + hits.get(file).length, 0);
  const out = [`${label}: ${refCount} refs in ${files.length} files (${tests.length} tests)`];
  if (callers.length > 0) out.push(`  callers: ${formatList(callers.map((f) => formatFile(f, hits.get(f))), limit).join(", ")}`);
  if (tests.length > 0) out.push(`  tests: ${formatList(tests, limit).join(", ")}`);
  return out;
}

export function parseArgs(argv) {
  const options = { symbols: [], files: [], base: "HEAD", limit: 15 };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    const value = argv[i + 1];
    if (flag === "--help" || flag === "-h") return { ...options, help: true };
    if (value === undefined || value.startsWith("--")) throw new Error(`${flag} needs a value`);
    if (flag === "--symbol") options.symbols.push(value);
    else if (flag === "--file") options.files.push(value);
    else if (flag === "--base") {
      if (value.startsWith("-")) throw new Error("--base must be a ref, not an option");
      options.base = value;
    }
    else if (flag === "--limit") {
      options.limit = Number.parseInt(value, 10);
      if (!(options.limit > 0)) throw new Error("--limit needs a positive integer");
    } else throw new Error(`unknown option ${flag}`);
    i += 1;
  }
  return options;
}

export function run(argv, startDir = process.cwd()) {
  const options = parseArgs(argv);
  if (options.help) {
    return "usage: impact.mjs [--symbol <name>]... [--file <path>]... [--base <ref>] [--limit <n>]";
  }
  // git diff prints paths from the repository root, so every search runs there.
  const cwd = git(["rev-parse", "--show-toplevel"], startDir).trim();
  const out = [];
  for (const symbol of options.symbols) {
    out.push(...describe(`symbol ${symbol}`, symbol, references(symbol, cwd), { limit: options.limit }));
  }
  if (options.symbols.length + options.files.length > 0 && options.base !== "HEAD") out.push("note: --base applies only when no --symbol or --file is given");
  // git prints the top level with symlinks resolved, so resolve each --file the same way.
  let files = options.files.map((file) => path.relative(cwd, realResolve(path.resolve(startDir, file))));
  if (options.symbols.length === 0 && files.length === 0) {
    const changed = changedFiles(options.base, cwd);
    files = changed.filter((file) => !NON_CODE_PATTERN.test(file));
    if (files.length === 0) return `no changed code files against ${options.base}; pass --symbol or --file`;
    if (files.length < changed.length) out.push(`skipped ${changed.length - files.length} changed non-code files`);
  }
  for (const file of files) {
    const term = moduleTerm(file);
    out.push(...describe(`file ${file} (as "${term}")`, term, references(term, cwd), { exclude: file, limit: options.limit }));
  }
  out.push("note: word matches, not a call graph; check dynamic access and string-built names with Grep.");
  return out.join("\n");
}

function isMain() {
  if (!process.argv[1]) return false;
  try {
    return realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]);
  } catch {
    return false;
  }
}

if (isMain()) {
  try {
    process.stdout.write(`${run(process.argv.slice(2))}\n`);
  } catch (error) {
    process.stderr.write(`impact: ${error.message}\n`);
    process.exit(2);
  }
}
