import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import * as fs from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { EXCLUDE_BLOCK, LEGACY_GITIGNORE_CONTENTS, run } from "./omo-dir-ignore.mjs";

let hasGit = true;
try { execFileSync("git", ["--version"], { stdio: "ignore" }); } catch { hasGit = false; }
const post = (tool_name = "Bash", extra = {}) => ({ tool_name, ...extra });
const git = (cwd, ...args) => execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
const exclude = (root) => resolve(root, git(root, "rev-parse", "--git-path", "info/exclude").trim());
const omo = (root) => join(root, ".claude/omo");
const read = (path) => fs.readFileSync(path, "utf8");
function fixture(fn, init = true) {
  const root = fs.realpathSync(fs.mkdtempSync(join(tmpdir(), "omo-ignore-")));
  try {
    if (init) git(root, "init", "-q");
    fn(root);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
}
function records(root) {
  for (const sub of ["handoffs", "drafts"]) {
    fs.mkdirSync(join(omo(root), sub), { recursive: true });
    fs.writeFileSync(join(omo(root), sub, "t.md"), "record");
  }
}
const check = (name, fn) => test(name, { skip: !hasGit }, () => fixture(fn));

test("exports exactly the managed block and both known legacy versions", () => {
  assert.equal(EXCLUDE_BLOCK, "# >>> omo-orchestrator managed >>>\n**/.claude/omo/handoffs/\n**/.claude/omo/plans/\n**/.claude/omo/drafts/\n**/.claude/omo/reviews/\n**/.claude/omo/briefs/\n**/.claude/omo/codex/\n# <<< omo-orchestrator managed <<<\n");
  const old = "# Created by the omo-orchestrator plugin: omo working records stay out of Git.\n/.gitignore\n/handoffs/\n/plans/\n/reviews/\n/briefs/\n";
  assert.deepEqual(LEGACY_GITIGNORE_CONTENTS, [old + "/codex/\n", old]);
});
check("writes atomically with the prescribed git runner options and avoids idempotent writes", root => {
  records(root);
  let writes = 0, renames = 0;
  const options = {
    git(command, args, opts) {
      assert.equal(command, "git");
      assert.deepEqual(args, ["rev-parse", "--git-path", "info/exclude"]);
      const expectedEnv = { ...process.env };
      for (const key of ["GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"]) delete expectedEnv[key];
      assert.deepEqual(opts, { cwd: omo(root), encoding: "utf8", timeout: 3000, stdio: ["ignore", "pipe", "ignore"], env: expectedEnv });
      return execFileSync(command, args, opts);
    },
    fs: { ...fs,
      writeFileSync(path, ...args) {
        writes++;
        assert.equal(dirname(path), dirname(exclude(root)));
        assert.notEqual(path, exclude(root));
        return fs.writeFileSync(path, ...args);
      },
      renameSync(source, target) {
        renames++;
        assert.equal(target, exclude(root));
        return fs.renameSync(source, target);
      },
    },
  };
  run(post("Bash", { cwd: root }), options);
  run(post("Bash", { cwd: root }), options);
  assert.equal(writes, 1);
  assert.equal(renames, 1);
});
check("happy path and idempotence: records hidden with exactly one block and no .gitignore", root => {
  records(root);
  assert.equal(run(post("Bash", { cwd: root })), "");
  assert.equal(git(root, "status", "--porcelain", "-uall"), "");
  assert.equal(fs.existsSync(join(omo(root), ".gitignore")), false);
  const first = read(exclude(root));
  assert.equal(first.split(EXCLUDE_BLOCK).length, 2);
  run(post("Bash", { cwd: root }));
  assert.equal(read(exclude(root)), first);
});
check("preserves user bytes and local-mode init-deep block", root => {
  records(root);
  const before = "*.log\n# >>> omo-init-deep managed >>>\n/.claude/omo/init-deep.json\n# <<< omo-init-deep managed <<<\n";
  fs.writeFileSync(exclude(root), before);
  fs.writeFileSync(join(omo(root), "init-deep.json"), "{}");
  run(post("Bash", { cwd: root }));
  assert.equal(read(exclude(root)), before + EXCLUDE_BLOCK);
  assert.equal(git(root, "status", "--porcelain", "-uall"), "");
});
check("committed mode leaves init-deep.json visible", root => {
  records(root);
  fs.writeFileSync(join(omo(root), "init-deep.json"), "{}");
  run(post("Bash", { cwd: root }));
  assert.equal(git(root, "status", "--porcelain", "-uall"), "?? .claude/omo/init-deep.json\n");
});
check("preserves non-UTF-8 bytes outside the managed block", root => {
  records(root);
  const prefix = Buffer.from([0x23, 0xff, 0x0a]);
  const suffix = Buffer.from([0x23, 0xfe]);
  fs.writeFileSync(exclude(root), Buffer.concat([prefix, Buffer.from("# >>> omo-orchestrator managed >>>\nold\n# <<< omo-orchestrator managed <<<\n"), suffix]));
  run(post("Bash", { cwd: root }));
  assert.deepEqual(fs.readFileSync(exclude(root)), Buffer.concat([prefix, Buffer.from(EXCLUDE_BLOCK), suffix]));
});
check("stale block replaced while outside bytes remain identical", root => {
  records(root);
  fs.writeFileSync(exclude(root), "prefix\r\n# >>> omo-orchestrator managed >>>\nold\n# <<< omo-orchestrator managed <<<\nsuffix");
  run(post("Bash", { cwd: root }));
  assert.equal(read(exclude(root)), "prefix\r\n" + EXCLUDE_BLOCK + "suffix");
});
check("malformed marker sets leave exclude and legacy file untouched", root => {
  records(root);
  const start = "# >>> omo-orchestrator managed >>>\n", end = "# <<< omo-orchestrator managed <<<\n";
  for (const content of [start, end, end + start, start + start + end, start + end + end]) {
    fs.writeFileSync(exclude(root), content);
    fs.writeFileSync(join(omo(root), ".gitignore"), LEGACY_GITIGNORE_CONTENTS[0]);
    run(post("Bash", { cwd: root }));
    assert.equal(read(exclude(root)), content);
    assert.ok(fs.existsSync(join(omo(root), ".gitignore")));
  }
});
check("linked worktree uses the common exclude", root => {
  git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "fixture");
  const worktree = join(root, "linked");
  git(root, "worktree", "add", "-qb", "linked-test", worktree);
  records(worktree);
  run(post("Bash", { cwd: worktree }));
  assert.equal(exclude(worktree), exclude(root));
  assert.ok(read(exclude(root)).includes(EXCLUDE_BLOCK));
  assert.equal(git(worktree, "status", "--porcelain", "-uall"), "");
});
check("deletes both exact legacy versions and preserves edited .gitignore", root => {
  records(root);
  for (const content of [...LEGACY_GITIGNORE_CONTENTS, LEGACY_GITIGNORE_CONTENTS[0] + "custom\n"]) {
    const path = join(omo(root), ".gitignore");
    fs.writeFileSync(path, content);
    run(post("Write", { tool_input: { file_path: join(omo(root), "plans/t.md") } }));
    assert.equal(fs.existsSync(path), content.endsWith("custom\n"));
    if (fs.existsSync(path)) assert.equal(read(path), content);
  }
});
check("no-op for absent omo, disabled env, unrelated tools, git errors and write failures", root => {
  const before = read(exclude(root));
  run(post("Bash", { cwd: root }));
  assert.equal(fs.existsSync(omo(root)), false);
  records(root);
  for (const value of ["off", "0", "false", "OFF"]) run(post("Bash", { cwd: root }), { env: { OMO_DIR_IGNORE: value } });
  run(post("Read", { cwd: root }));
  run(post("Bash", { cwd: root }), { git: () => { throw Error("timeout"); } });
  run(post("Bash", { cwd: root }), { fs: { ...fs, writeFileSync() { throw Error("EACCES"); } } });
  assert.equal(read(exclude(root)), before);
});
test("no git repository or malformed input is silent", () => fixture(root => {
  records(root);
  for (const input of [null, undefined, {}, post("Write", { tool_input: { file_path: join(omo(root), "x.md") } })]) assert.equal(run(input), "");
  assert.equal(fs.existsSync(join(omo(root), ".gitignore")), false);
}, false));
check("missing info directory recreated; unterminated user line gets a newline", root => {
  records(root);
  fs.rmSync(dirname(exclude(root)), { recursive: true });
  run(post("Bash", { cwd: root }));
  assert.equal(read(exclude(root)), EXCLUDE_BLOCK);
  fs.writeFileSync(exclude(root), "*.log");
  run(post("Bash", { cwd: root }));
  assert.equal(read(exclude(root)), "*.log\n" + EXCLUDE_BLOCK);
});

check("H1: follows symlinked exclude without replacing the link", root => fixture(outside => {
  records(root);
  const target = join(outside, "exclude");
  fs.writeFileSync(target, "*.private\n");
  fs.unlinkSync(exclude(root));
  fs.symlinkSync(target, exclude(root));
  run(post("Bash", { cwd: root }));
  assert.ok(fs.lstatSync(exclude(root)).isSymbolicLink());
  assert.equal(read(target), "*.private\n" + EXCLUDE_BLOCK);
}, false));
check("H2: preserves exclude mode 0600", root => {
  records(root);
  fs.chmodSync(exclude(root), 0o600);
  run(post("Bash", { cwd: root }));
  assert.equal(fs.statSync(exclude(root)).mode & 0o7777, 0o600);
});
check("H3: ignores inherited Git location overrides", root => fixture(other => {
  records(root);
  const before = read(exclude(other));
  const env = { ...process.env, GIT_DIR: join(other, ".git"), GIT_WORK_TREE: other, GIT_COMMON_DIR: join(other, ".git"), GIT_INDEX_FILE: join(other, ".git/index") };
  run(post("Bash", { cwd: root }), {
    env,
    git(command, args, opts) {
      return execFileSync(command, args, { ...opts, env: opts.env ?? env });
    },
  });
  assert.ok(read(exclude(root)).includes(EXCLUDE_BLOCK));
  assert.equal(read(exclude(other)), before);
  assert.equal(env.GIT_DIR, join(other, ".git"));
}));
check("H4: preserves user lines after a CR-only stale block", root => {
  records(root);
  fs.writeFileSync(exclude(root), "a\r# >>> omo-orchestrator managed >>>\rold\r# <<< omo-orchestrator managed <<<\rkeep.secret\r");
  run(post("Bash", { cwd: root }));
  assert.equal(read(exclude(root)), "a\r" + EXCLUDE_BLOCK + "keep.secret\r");
});
check("H5: keeps a tracked exact legacy .gitignore", root => {
  records(root);
  const legacy = join(omo(root), ".gitignore");
  fs.writeFileSync(legacy, LEGACY_GITIGNORE_CONTENTS[0]);
  git(root, "add", "-f", "--", ".claude/omo/.gitignore");
  run(post("Bash", { cwd: root }));
  assert.equal(read(legacy), LEGACY_GITIGNORE_CONTENTS[0]);
});
check("H5: keeps a symlink to exact legacy contents", root => {
  records(root);
  const target = join(root, "legacy-ignore");
  fs.writeFileSync(target, LEGACY_GITIGNORE_CONTENTS[0]);
  const legacy = join(omo(root), ".gitignore");
  fs.symlinkSync(target, legacy);
  run(post("Bash", { cwd: root }));
  assert.ok(fs.lstatSync(legacy).isSymbolicLink());
  assert.equal(read(target), LEGACY_GITIGNORE_CONTENTS[0]);
});

check("M1: leaves dangling exclude symlink and missing target untouched", root => {
  records(root);
  const path = exclude(root);
  const target = join(root, "missing-exclude");
  fs.unlinkSync(path);
  fs.symlinkSync(target, path);
  const entries = fs.readdirSync(dirname(path));
  let writes = 0;
  assert.equal(run(post("Bash", { cwd: root }), {
    fs: { ...fs, writeFileSync(...args) { writes++; return fs.writeFileSync(...args); } },
  }), "");
  assert.ok(fs.lstatSync(path).isSymbolicLink());
  assert.equal(fs.existsSync(target), false);
  assert.equal(writes, 0);
  assert.deepEqual(fs.readdirSync(dirname(path)), entries);
});
check("M2: keeps exact legacy .gitignore when ls-files times out", root => {
  records(root);
  const legacy = join(omo(root), ".gitignore");
  fs.writeFileSync(legacy, LEGACY_GITIGNORE_CONTENTS[0]);
  let checks = 0;
  assert.equal(run(post("Bash", { cwd: root }), {
    git(command, args, options) {
      if (args[0] === "rev-parse") return execFileSync(command, args, options);
      assert.deepEqual(args, ["ls-files", "--error-unmatch", "--", ".gitignore"]);
      checks++;
      throw Object.assign(new Error("timeout"), { code: "ETIMEDOUT" });
    },
  }), "");
  assert.equal(checks, 1);
  assert.equal(read(legacy), LEGACY_GITIGNORE_CONTENTS[0]);
  assert.ok(read(exclude(root)).includes(EXCLUDE_BLOCK));
});
