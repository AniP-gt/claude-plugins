// Run: node --test omo-orchestrator/scripts/impact.test.mjs
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { isTestPath, moduleTerm, parseArgs, run } from "./impact.mjs";

test("isTestPath recognizes common test layouts and leaves docs alone", () => {
  for (const file of ["a/b.test.ts", "tests/x.py", "test_foo.py", "foo_test.go", "FooTest.java", "spec/a_spec.rb", "app/conftest.py"]) {
    assert.equal(isTestPath(file), true, file);
  }
  for (const file of ["src/foo.ts", "src/contest.ts", "docs/specs/design.md", "src/latest.ts"]) {
    assert.equal(isTestPath(file), false, file);
  }
});

test("moduleTerm uses the subject of test files and the directory for generic names", () => {
  assert.equal(moduleTerm("src/auth/login.ts"), "login");
  assert.equal(moduleTerm("src/auth/index.ts"), "auth");
  assert.equal(moduleTerm("src/foo.test.ts"), "foo");
  assert.equal(moduleTerm("spec/foo_spec.rb"), "foo");
  assert.equal(moduleTerm(".gitignore"), ".gitignore");
});

test("parseArgs rejects missing values, unknown flags, and option-like refs", () => {
  assert.deepEqual(parseArgs(["--symbol", "a", "--symbol", "b", "--limit", "3"]).symbols, ["a", "b"]);
  assert.throws(() => parseArgs(["--symbol"]), /needs a value/);
  assert.throws(() => parseArgs(["--bogus", "x"]), /unknown option/);
  assert.throws(() => parseArgs(["--base", "-O/etc/passwd"]), /must be a ref/);
  assert.throws(() => parseArgs(["--limit", "0"]), /positive integer/);
});

let repo;
const git = (...args) => execFileSync("git", args, { cwd: repo, stdio: "ignore" });

before(() => {
  repo = mkdtempSync(path.join(os.tmpdir(), "impact-test-"));
  mkdirSync(path.join(repo, "日本"));
  mkdirSync(path.join(repo, "tests"));
  writeFileSync(path.join(repo, "日本", "core.js"), "export function loadCart() {}\n");
  writeFileSync(path.join(repo, "app.js"), 'import { loadCart } from "./日本/core.js";\nloadCart();\n');
  git("init", "-q");
  git("-c", "user.name=t", "-c", "user.email=t@example.com", "add", ".");
  git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init");
  // Untracked caller and test, as they exist mid-task before `git add`.
  writeFileSync(path.join(repo, "tests", "cart.test.js"), "loadCart();\n");
  writeFileSync(path.join(repo, "日本", "core.js"), "export function loadCart() { return 1; }\n");
});

after(() => rmSync(repo, { recursive: true, force: true }));

test("symbol search counts untracked callers and tests", () => {
  const out = run(["--symbol", "loadCart"], repo);
  assert.match(out, /symbol loadCart: 4 refs in 3 files \(1 tests\)/);
  assert.match(out, /tests: tests\/cart\.test\.js/);
});

test("changed non-ASCII paths are searched unescaped and excluded from their own callers", () => {
  const out = run([], repo);
  assert.match(out, /file 日本\/core\.js \(as "core"\): 1 refs in 1 files/);
  assert.match(out, /callers: app\.js/);
  assert.doesNotMatch(out, /\\\d{3}/);
});

test("--file resolves against the caller's directory", () => {
  const out = run(["--file", "core.js"], path.join(repo, "日本"));
  assert.match(out, /file 日本\/core\.js/);
});

test("--file accepts absolute paths under a symlinked directory and deleted files", () => {
  assert.match(run(["--file", path.join(repo, "日本", "core.js")], repo), /file 日本\/core\.js \(as "core"\): 1 refs/);
  assert.match(run(["--file", "gone/removed.js"], repo), /file gone\/removed\.js/);
});

test("the CLI runs when started through a symlink", () => {
  const link = path.join(repo, "impact-link.mjs");
  symlinkSync(fileURLToPath(new URL("./impact.mjs", import.meta.url)), link);
  try {
    const out = execFileSync(process.execPath, [link, "--symbol", "loadCart"], { cwd: repo, encoding: "utf8" });
    assert.match(out, /symbol loadCart:/);
  } finally {
    rmSync(link);
  }
});

test("--base with --symbol is reported as ignored", () => {
  assert.match(run(["--symbol", "loadCart", "--base", "main"], repo), /--base applies only when/);
});
