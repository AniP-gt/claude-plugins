// Run: node --test omo-orchestrator/hooks/omo-dir-ignore.test.mjs
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { IGNORE_CONTENT, run } from "./omo-dir-ignore.mjs";

const EXPECTED = [
  "# Created by the omo-orchestrator plugin: omo working records stay out of Git.",
  "/.gitignore",
  "/handoffs/",
  "/plans/",
  "/reviews/",
  "/briefs/",
  "",
].join("\n");

function withRepo(fn) {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "omo-dir-ignore-")));
  try {
    mkdirSync(join(root, ".git"));
    fn(root);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

const post = (tool_name, extra) => ({ hook_event_name: "PostToolUse", tool_name, tool_input: {}, ...extra });

test("the ignore file content is exactly the documented text", () => {
  assert.equal(IGNORE_CONTENT, EXPECTED);
});

test("a write under .claude/omo creates .gitignore there, and the hook prints nothing", () => {
  withRepo((root) => {
    mkdirSync(join(root, ".claude/omo/handoffs"), { recursive: true });
    const file = join(root, ".claude/omo/handoffs/task.md");
    const output = run(post("Write", { tool_input: { file_path: file }, cwd: tmpdir() }));
    assert.equal(output, "");
    assert.equal(readFileSync(join(root, ".claude/omo/.gitignore"), "utf8"), EXPECTED);
  });
});

test("a Bash call from a subdirectory finds the git root by walking up from cwd", () => {
  withRepo((root) => {
    mkdirSync(join(root, ".claude/omo"), { recursive: true });
    mkdirSync(join(root, "src/deep"), { recursive: true });
    run(post("Bash", { tool_input: { command: "true" }, cwd: join(root, "src/deep") }));
    assert.equal(readFileSync(join(root, ".claude/omo/.gitignore"), "utf8"), EXPECTED);
  });
});

test("a .git file (worktree) marks the git root too", () => {
  withRepo((root) => {
    rmSync(join(root, ".git"), { recursive: true });
    writeFileSync(join(root, ".git"), "gitdir: /elsewhere\n");
    mkdirSync(join(root, ".claude/omo"), { recursive: true });
    run(post("Bash", { cwd: root }));
    assert.equal(existsSync(join(root, ".claude/omo/.gitignore")), true);
  });
});

test("an existing .gitignore is never overwritten", () => {
  withRepo((root) => {
    mkdirSync(join(root, ".claude/omo"), { recursive: true });
    writeFileSync(join(root, ".claude/omo/.gitignore"), "custom\n");
    run(post("Edit", { tool_input: { file_path: join(root, ".claude/omo/a.md") }, cwd: root }));
    assert.equal(readFileSync(join(root, ".claude/omo/.gitignore"), "utf8"), "custom\n");
  });
});

test("an absent .claude/omo is not created", () => {
  withRepo((root) => {
    run(post("Bash", { cwd: root }));
    run(post("Write", { tool_input: { file_path: join(root, ".claude/omo/x.md") }, cwd: root }));
    assert.equal(existsSync(join(root, ".claude")), false);
  });
});

test("tools outside the list are ignored", () => {
  withRepo((root) => {
    mkdirSync(join(root, ".claude/omo"), { recursive: true });
    for (const tool of ["Read", "Grep", "Agent", "mcp__x__y"]) run(post(tool, { cwd: root }));
    assert.equal(existsSync(join(root, ".claude/omo/.gitignore")), false);
  });
});

test("malformed input produces no output and no error", () => {
  for (const input of [undefined, null, "text", 42, {}, { tool_name: 7 }, post("Bash", { cwd: 7 }), post("Write", { tool_input: "x" })]) {
    assert.equal(run(input), "");
  }
});

test("a filesystem error is swallowed", () => {
  const failing = {
    statSync: () => ({ isDirectory: () => true }),
    existsSync: () => true,
    writeFileSync: () => {
      throw new Error("EACCES");
    },
  };
  assert.equal(run(post("Bash", { cwd: "/anywhere" }), { fs: failing }), "");
  assert.equal(run(post("Write", { tool_input: { file_path: "/a/.claude/omo/x.md" } }), { fs: failing }), "");
});

test("OMO_DIR_IGNORE off, 0, or false (any case) does nothing; other values do not", () => {
  for (const value of ["off", "0", "false", "OFF", "False"]) {
    withRepo((root) => {
      mkdirSync(join(root, ".claude/omo"), { recursive: true });
      run(post("Bash", { cwd: root }), { env: { OMO_DIR_IGNORE: value } });
      assert.equal(existsSync(join(root, ".claude/omo/.gitignore")), false, value);
    });
  }
  withRepo((root) => {
    mkdirSync(join(root, ".claude/omo"), { recursive: true });
    run(post("Bash", { cwd: root }), { env: { OMO_DIR_IGNORE: "on" } });
    assert.equal(existsSync(join(root, ".claude/omo/.gitignore")), true);
  });
});

let hasGit = true;
try {
  execFileSync("git", ["--version"], { stdio: "ignore" });
} catch {
  hasGit = false;
}

test("committed mode: git no longer lists omo records, while init-deep.json stays trackable", { skip: !hasGit }, () => {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "omo-dir-ignore-git-")));
  try {
    const git = (...args) => execFileSync("git", args, { cwd: root, encoding: "utf8" });
    git("init", "-q");
    mkdirSync(join(root, ".claude/omo/handoffs"), { recursive: true });
    writeFileSync(join(root, ".claude/omo/handoffs/task.md"), "ledger\n");
    writeFileSync(join(root, ".claude/omo/init-deep.json"), "{}\n");
    assert.match(git("status", "--porcelain", "-uall"), /handoffs\/task\.md/);
    run(post("Bash", { cwd: root }));
    const status = git("status", "--porcelain", "-uall");
    assert.doesNotMatch(status, /handoffs|\.gitignore/);
    assert.match(status, /\.claude\/omo\/init-deep\.json/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("local mode: the omo-init-deep info/exclude block keeps hiding init-deep.json next to the hook's .gitignore", { skip: !hasGit }, () => {
  const root = realpathSync(mkdtempSync(join(tmpdir(), "omo-dir-ignore-local-")));
  try {
    const git = (...args) => execFileSync("git", args, { cwd: root, encoding: "utf8" });
    git("init", "-q");
    const exclude = resolve(root, git("rev-parse", "--git-path", "info/exclude").trim());
    mkdirSync(dirname(exclude), { recursive: true });
    appendFileSync(
      exclude,
      [
        "# >>> omo-init-deep managed >>>",
        "/.claude/rules/omo-init-deep/",
        "/.claude/omo/init-deep.json",
        "# <<< omo-init-deep managed <<<",
        "",
      ].join("\n"),
    );
    mkdirSync(join(root, ".claude/omo/handoffs"), { recursive: true });
    writeFileSync(join(root, ".claude/omo/init-deep.json"), "{}\n");
    writeFileSync(join(root, ".claude/omo/handoffs/t.md"), "ledger\n");
    run(post("Bash", { cwd: root }));
    assert.equal(git("status", "--porcelain", "-uall"), "");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
