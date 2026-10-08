// Git working-tree snapshot shared by preflight.mjs (taken when the user sends a prompt) and
// review-gate.mjs (compared when Claude stops). Comparing the two finds every file the turn changed,
// including edits made through Bash or by sub-agents, which never show up as Edit/Write calls.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const GIT_TIMEOUT_MS = 2000;
const DELETED = "deleted";
const SHA_PATTERN = /^[0-9a-f]{40,64}$/;

function git(cwd, args, input) {
  return execFileSync("git", args, {
    cwd,
    input,
    encoding: "utf8",
    timeout: GIT_TIMEOUT_MS,
    maxBuffer: 32 * 1024 * 1024,
    stdio: ["pipe", "pipe", "ignore"],
  });
}

function splitZ(output) {
  return output.split("\0").filter((entry) => entry.length > 0);
}

// Blob hash of each path's current content in one git call; a path that no longer exists maps to DELETED.
function hashPaths(cwd, paths) {
  const hashes = {};
  const present = [];
  for (const path of paths) {
    let isFile = false;
    try {
      isFile = statSync(join(cwd, path)).isFile();
    } catch {
      isFile = false;
    }
    // hash-object --stdin-paths is newline-delimited; such a name would shift every later hash.
    if (isFile && !path.includes("\n")) present.push(path);
    else if (isFile) hashes[path] = `unhashable:${path}`;
    else hashes[path] = DELETED;
  }
  if (present.length > 0) {
    const output = git(cwd, ["hash-object", "--stdin-paths"], `${present.join("\n")}\n`).trim().split("\n");
    present.forEach((path, index) => {
      hashes[path] = output[index] ?? DELETED;
    });
  }
  return hashes;
}

// Paths that differ from `base` (tracked changes, committed or not) plus untracked files.
function changedSince(cwd, base) {
  const tracked = splitZ(git(cwd, ["diff", "--name-only", "-z", base, "--"]));
  const untracked = splitZ(git(cwd, ["ls-files", "--others", "--exclude-standard", "-z"]));
  return [...new Set([...tracked, ...untracked])];
}

export function snapshotDir(env = process.env) {
  return join(env.OMO_SNAPSHOT_DIR ?? join(tmpdir(), "omo-orchestrator"), "turns");
}

function snapshotFile(sessionId, env) {
  return join(snapshotDir(env), `${String(sessionId).replace(/[^A-Za-z0-9_-]/g, "_")}.json`);
}

export function gitRoot(cwd) {
  try {
    return git(cwd, ["rev-parse", "--show-toplevel"]).trim();
  } catch {
    return null;
  }
}

// Returns null outside a git work tree or when git fails; callers then fall back to the transcript.
export function takeSnapshot(cwd) {
  try {
    const root = gitRoot(cwd);
    if (root === null) return null;
    const head = git(root, ["rev-parse", "--verify", "HEAD"]).trim();
    const dirty = changedSince(root, head);
    return { root, head, hashes: hashPaths(root, dirty) };
  } catch {
    return null;
  }
}

export function saveSnapshot(sessionId, snapshot, env = process.env) {
  if (!sessionId || snapshot === null) return;
  try {
    mkdirSync(snapshotDir(env), { recursive: true, mode: 0o700 });
    if (!ownedPrivateDir(snapshotDir(env))) return;
    writeFileSync(snapshotFile(sessionId, env), JSON.stringify(snapshot), { mode: 0o600 });
  } catch {
    // A missing snapshot only weakens the gate to transcript-based detection.
  }
}

// On Linux tmpdir() is the shared /tmp, so another user could pre-create the directory and plant a
// snapshot whose root or head steers git. Only a directory we own and nobody else can write is trusted.
function ownedPrivateDir(dir) {
  try {
    const stat = statSync(dir);
    const uid = typeof process.getuid === "function" ? process.getuid() : stat.uid;
    return stat.isDirectory() && stat.uid === uid && (stat.mode & 0o022) === 0;
  } catch {
    return false;
  }
}

// The snapshot is used only for the repository the hook is running in now, at a commit-shaped HEAD.
export function loadSnapshot(sessionId, env = process.env, cwd = undefined) {
  if (!sessionId || !ownedPrivateDir(snapshotDir(env))) return null;
  try {
    const parsed = JSON.parse(readFileSync(snapshotFile(sessionId, env), "utf8"));
    if (typeof parsed?.root !== "string" || typeof parsed?.head !== "string") return null;
    if (!SHA_PATTERN.test(parsed.head)) return null;
    if (cwd !== undefined && gitRoot(cwd) !== parsed.root) return null;
    return parsed;
  } catch {
    return null;
  }
}

// Files whose content differs from what they had when the snapshot was taken, relative to the repo root.
export function filesChangedSince(snapshot) {
  try {
    const before = snapshot.hashes ?? {};
    const candidates = new Set([...changedSince(snapshot.root, snapshot.head), ...Object.keys(before)]);
    const now = hashPaths(snapshot.root, [...candidates]);
    // A path clean at snapshot time matched HEAD, so appearing in the diff now means this turn changed it.
    return [...candidates].filter((path) => !(path in before) || now[path] !== before[path]);
  } catch {
    return null;
  }
}
