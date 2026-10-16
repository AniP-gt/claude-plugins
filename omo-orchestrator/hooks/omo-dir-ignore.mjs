#!/usr/bin/env node
// PostToolUse hook: keep `.claude/omo/` (handoff ledgers, plans, review reports) out of Git without asking the
// user to edit a project .gitignore or the global git config. After a write-like tool call, a `.gitignore`
// is created inside an existing `.claude/omo/` directory. It lists each working-record subdirectory (and itself)
// instead of using `*`, and has no negation: `init-deep.json` is left to `omo-init-deep`, whose local mode hides it
// through `info/exclude` and whose `--committed` mode tracks it. A negation here would override that exclude entry.
// A new omo subdirectory must be added to IGNORE_CONTENT.
// OMO_DIR_IGNORE=off|0|false disables the hook.
// The directory is never created here, an existing `.gitignore` is never touched, and every failure is silent.
// Candidates: the `.claude/omo` that a tool's `file_path` points into, and `<git root>/.claude/omo` found by
// walking up from `cwd`, which also covers files created through Bash.
import * as nodeFs from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const IGNORE_CONTENT = [
  "# Created by the omo-orchestrator plugin: omo working records stay out of Git.",
  "/.gitignore",
  "/handoffs/",
  "/plans/",
  "/reviews/",
  "/briefs/",
  "",
].join("\n");

const TOOLS = new Set(["Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"]);
const OMO_SEGMENT = "/.claude/omo/";

function gitRoot(cwd, fs) {
  let dir = cwd;
  for (;;) {
    if (fs.existsSync(join(dir, ".git"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function candidates(input, fs) {
  const found = [];
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

function protect(dir, fs) {
  try {
    if (!fs.statSync(dir).isDirectory()) return;
    // The `wx` flag fails when a .gitignore already exists, so a user's own file is never overwritten.
    fs.writeFileSync(join(dir, ".gitignore"), IGNORE_CONTENT, { flag: "wx" });
  } catch {
    // Absent directory, existing .gitignore, or no permission: leave everything as it is.
  }
}

export function run(input, { fs = nodeFs, env = process.env } = {}) {
  try {
    if (/^(off|0|false)$/i.test(env.OMO_DIR_IGNORE ?? "")) return "";
    if (typeof input !== "object" || input === null || !TOOLS.has(input.tool_name)) return "";
    for (const dir of candidates(input, fs)) protect(dir, fs);
  } catch {
    // A hook must never disturb the tool call.
  }
  return "";
}

async function readStdin() {
  let data = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let parsed;
  try {
    parsed = JSON.parse(await readStdin());
  } catch {
    parsed = undefined;
  }
  run(parsed);
}
