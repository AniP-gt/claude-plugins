#!/usr/bin/env node
// PostToolUse hook: hide omo working records through a managed Git info/exclude block.
// Resolve the exclude file with git rev-parse, preserving user lines and omo-init-deep's block.
// Never create .claude/omo or ignore init-deep.json. Replace via a same-directory temp file.
// Remove only exact known legacy hook .gitignore contents after the block is current.
// OMO_DIR_IGNORE=off|0|false disables this hook; every failure is silent and stdout stays empty.
// Candidates come from file_path and walking cwd upward to a Git root (including worktrees).
import * as nodeFs from "node:fs";
import { execFileSync, type ExecFileSyncOptionsWithStringEncoding } from "node:child_process";
import { randomUUID } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const EXCLUDE_BLOCK = [
  "# >>> omo-orchestrator managed >>>",
  ...["handoffs", "plans", "drafts", "reviews", "briefs", "codex", "goal"].map(name => `**/.claude/omo/${name}/`),
  "# <<< omo-orchestrator managed <<<",
  "",
].join("\n");

const legacy = [
  "# Created by the omo-orchestrator plugin: omo working records stay out of Git.",
  "/.gitignore", "/handoffs/", "/plans/", "/reviews/", "/briefs/",
];
export const LEGACY_GITIGNORE_CONTENTS = [
  [...legacy, "/codex/", ""].join("\n"),
  [...legacy, ""].join("\n"),
];

type Fs = typeof nodeFs;
// The one execFileSync call shape this hook uses, so a test double only has to match it.
type Git = (command: string, args: string[], options: ExecFileSyncOptionsWithStringEncoding) => string;
// PostToolUse hook input as read from stdin; every field is checked at runtime before use.
type HookInput = { tool_name?: unknown; tool_input?: { file_path?: unknown } | null; cwd?: unknown };
type RunOptions = { fs?: Fs; env?: NodeJS.ProcessEnv; git?: Git };

const TOOLS = new Set(["Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"]);
const OMO_SEGMENT = "/.claude/omo/";

function gitRoot(cwd: string, fs: Fs): string | null {
  let dir = cwd;
  for (;;) {
    if (fs.existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function candidates(input: HookInput, fs: Fs): string[] {
  const found: string[] = [];
  const filePath = input.tool_input?.file_path;
  if (typeof filePath === "string") {
    const at = filePath.indexOf(OMO_SEGMENT);
    if (at >= 0) found.push(filePath.slice(0, at + OMO_SEGMENT.length - 1));
  }
  if (typeof input.cwd === "string" && input.cwd.length > 0) {
    const root = gitRoot(input.cwd, fs);
    if (root !== null) found.push(join(root, ".claude", "omo"));
  }
  return [...new Set(found)];
}

function protect(dir: string, fs: Fs, git: Git, env: NodeJS.ProcessEnv): void {
  let temporary: string | undefined;
  try {
    if (!fs.statSync(dir).isDirectory()) return;
    const gitEnv = { ...env };
    for (const key of ["GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"]) delete gitEnv[key];
    const gitOptions: ExecFileSyncOptionsWithStringEncoding = { cwd: dir, encoding: "utf8", timeout: 3000, stdio: ["ignore", "pipe", "ignore"], env: gitEnv };
    const output = git("git", ["rev-parse", "--git-path", "info/exclude"], gitOptions).trim();
    if (!output) return;
    const resolved = resolve(dir, output);
    let exists = false;
    try {
      fs.lstatSync(resolved);
      exists = true;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    // A dangling link exists: let realpath fail silently rather than replace the link.
    const path = exists ? fs.realpathSync(resolved) : resolved;
    const mode = exists ? fs.statSync(path).mode & 0o7777 : undefined;
    const existing = exists ? fs.readFileSync(path, "latin1") : "";
    const starts = [...existing.matchAll(/^# >>> omo-orchestrator managed >>>(?=\r?$)/gm)];
    const ends = [...existing.matchAll(/^# <<< omo-orchestrator managed <<<(?=\r?$)/gm)];
    let next;
    if (starts.length === 0 && ends.length === 0) {
      next = existing + (existing && !existing.endsWith("\n") ? "\n" : "") + EXCLUDE_BLOCK;
    } else if (starts.length === 1 && ends.length === 1 && starts[0].index < ends[0].index) {
      let after = ends[0].index + ends[0][0].length;
      if (existing.startsWith("\r\n", after)) after += 2;
      else if (existing[after] === "\n" || existing[after] === "\r") after++;
      next = existing.slice(0, starts[0].index) + EXCLUDE_BLOCK + existing.slice(after);
    } else return;
    if (next !== existing) {
      fs.mkdirSync(dirname(path), { recursive: true });
      temporary = join(dirname(path), `.omo-exclude-${process.pid}-${randomUUID()}.tmp`);
      // latin1 round-trips every existing byte, including non-UTF-8 user comments.
      fs.writeFileSync(temporary, next, { flag: "wx", encoding: "latin1" });
      if (mode !== undefined) fs.chmodSync(temporary, mode);
      fs.renameSync(temporary, path);
      temporary = undefined;
    }
    const legacy = join(dir, ".gitignore");
    if (fs.existsSync(legacy) && fs.lstatSync(legacy).isFile() &&
        LEGACY_GITIGNORE_CONTENTS.includes(fs.readFileSync(legacy, "utf8"))) {
      try {
        git("git", ["ls-files", "--error-unmatch", "--", ".gitignore"], gitOptions);
      } catch (error) {
        // Only Git's normal unmatched-path result authorizes deletion, never a timeout/spawn error.
        if ((error as { status?: unknown }).status === 1) fs.unlinkSync(legacy);
      }
    }
  } catch {
    // Git unavailable, missing directory, malformed state or permission failure: stay silent.
  } finally {
    if (temporary) {
      try { fs.unlinkSync(temporary); } catch { /* Best-effort cleanup. */ }
    }
  }
}

export function run(input: unknown, { fs = nodeFs, env = process.env, git = execFileSync }: RunOptions = {}): string {
  try {
    if (/^(off|0|false)$/i.test(env.OMO_DIR_IGNORE ?? "")) return "";
    if (typeof input !== "object" || input === null) return "";
    const hookInput = input as HookInput;
    if (typeof hookInput.tool_name !== "string" || !TOOLS.has(hookInput.tool_name)) return "";
    for (const dir of candidates(hookInput, fs)) protect(dir, fs, git, env);
  } catch {
    // A hook must never disturb the tool call.
  }
  return "";
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
  run(parsed);
}
