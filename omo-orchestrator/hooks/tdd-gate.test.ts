// Run: node --test omo-orchestrator/hooks/tdd-gate.test.ts
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { isProductionCode, run } from "./tdd-gate.ts";

const HOOK_PATH = fileURLToPath(new URL("./tdd-gate.ts", import.meta.url));
const roots: string[] = [];
after(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

const git = (cwd: string, ...args: string[]): string =>
  execFileSync("git", ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", ...args], {
    cwd,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
const scratch = (): string => {
  const root = mkdtempSync(join(tmpdir(), "tdd-gate-"));
  roots.push(root);
  return root;
};
const put = (repo: string, relative: string, content = "x\n"): string => {
  const path = join(repo, relative);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
  return path;
};
// A repo on `main` with one commit that holds production code, a doc, and no test.
const makeRepo = (): string => {
  const repo = scratch();
  git(repo, "init", "-q", "-b", "main");
  put(repo, "src/app.ts", "export const a = 1;\n");
  put(repo, "README.md", "# demo\n");
  git(repo, "add", "-A");
  git(repo, "commit", "-q", "-m", "init");
  return repo;
};
const edit = (filePath: unknown, tool = "Edit") => ({ hook_event_name: "PreToolUse", tool_name: tool, tool_input: { file_path: filePath } });
const gate = (input: unknown, env: NodeJS.ProcessEnv = {}) => run(input, { env });
const hook = (output: string) => JSON.parse(output).hookSpecificOutput;

test("isProductionCode: source extensions are gated, test paths and non-code files are not", () => {
  for (const path of ["src/app.ts", "a.tsx", "lib/x.py", "main.go", "x.rs", "A.java", "a.kt", "a.swift", "a.php", "a.cs", "a.c", "a.cc", "a.cpp", "a.h", "a.hpp", "a.scala", "a.ex", "a.exs", "a.rb", "a.mjs", "a.cjs", "a.js", "a.jsx"]) {
    assert.equal(isProductionCode(path), true, path);
  }
  for (const path of [
    "README.md", "package.json", "config.yaml", "style.css", "Makefile",
    "test/a.ts", "tests/a.py", "spec/a.rb", "src/__tests__/a.ts", "e2e/a.ts", "pkg/deep/tests/helper.go",
    "src/a.test.ts", "src/a.spec.tsx", "a.test.js", "pkg/a_test.go", "tests_x/test_foo.py", "test_foo.py", "foo_test.py", "foo_spec.rb",
  ]) {
    assert.equal(isProductionCode(path), false, path);
  }
});

test("isProductionCode: single-file component and Dart sources are gated, their test files are not", () => {
  for (const path of ["src/App.vue", "src/routes/+page.svelte", "lib/main.dart"]) assert.equal(isProductionCode(path), true, path);
  for (const path of ["src/App.test.vue", "test/widget_test.dart", "src/App.spec.svelte"]) assert.equal(isProductionCode(path), false, path);
});

test("isProductionCode: test directories match case-insensitively and cover common fixture, mock, and e2e-tool directories", () => {
  for (const path of [
    "Tests/FooTests.swift", "src/Test/a.ts", "Spec/a.rb", "src/SPEC/a.ts", "src/__mocks__/a.ts", "src/__fixtures__/a.ts", "pkg/testdata/a.go",
    "src/fixtures/a.ts", "app/src/androidTest/java/A.kt", "lib/testFixtures/A.kt", "cypress/support/commands.ts", "playwright/helpers.ts",
    "MyApp.Tests/Helper.cs", "MyApp.Test/Helper.cs", "src/MyApp.tests/Helper.cs",
  ]) {
    assert.equal(isProductionCode(path), false, path);
  }
  for (const path of ["src/latest/a.ts", "src/contest/a.ts", "src/Tests.Core/a.cs", "src/protests/a.ts"]) {
    assert.equal(isProductionCode(path), true, path);
  }
});

test("isProductionCode: test file naming conventions of other languages are test paths", () => {
  for (const path of [
    "Sources/FooTest.swift", "Sources/FooTests.swift", "src/FooTest.kt", "src/FooTests.kt", "src/FooTest.java", "src/FooTests.java",
    "src/FooTest.cs", "src/FooTests.cs", "src/FooTest.php", "src/FooTests.php", "src/FooTest.scala", "src/FooTests.scala",
    "src/FooSpec.kt", "src/FooSpec.scala", "src/FooSpec.groovy", "app/tests.py", "app/conftest.py", "conftest.py",
    "src/a.cy.ts", "src/a.cy.js", "spec/a_spec.rb", "src/foo_spec.js", "src/foo_spec.ts",
  ]) {
    assert.equal(isProductionCode(path), false, path);
  }
  for (const path of ["src/Latest.java", "src/Foo.java", "src/FooSpec.rb", "src/mytests.py", "src/conftest_helper.py", "src/Tester.kt"]) {
    assert.equal(isProductionCode(path), true, path);
  }
});

test("isProductionCode: *.config.*, *.conf.*, and dotfile configs are never gated", () => {
  for (const path of [
    "vite.config.ts", "jest.config.js", "webpack.config.mjs", "next.config.cjs", "tailwind.config.ts", "pkg/babel.config.js", "app/server.conf.py",
    ".eslintrc.js", ".eslintrc.cjs", ".prettierrc.js", "pkg/.babelrc.js", "Vite.Config.ts",
  ]) {
    assert.equal(isProductionCode(path), false, path);
  }
  for (const path of ["src/configure.ts", "src/config.ts", "src/configuration.ts", "src/app.ts"]) {
    assert.equal(isProductionCode(path), true, path);
  }
});

test("a config file or a Tests directory edit is allowed on a branch with no test change", () => {
  const repo = makeRepo();
  assert.equal(gate(edit(join(repo, "vite.config.ts"))), "");
  assert.equal(gate(edit(join(repo, ".eslintrc.js"))), "");
  assert.equal(gate(edit(join(repo, "Tests/FooTests.swift"))), "");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
});

test("a Tests directory file counts as the branch's test change", () => {
  const repo = makeRepo();
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  put(repo, "Tests/FooTests.swift");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
});

test("a path git ignores is allowed, a tracked file under an ignored pattern is still gated", () => {
  const repo = makeRepo();
  put(repo, ".gitignore", "node_modules/\ndist/\n");
  git(repo, "add", ".gitignore");
  git(repo, "commit", "-q", "-m", "ignore");
  assert.equal(gate(edit(join(repo, "node_modules/pkg/index.js"))), "");
  assert.equal(gate(edit(join(repo, "dist/bundle.js"))), "");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  // `git add -f` tracks a file despite the pattern; check-ignore then no longer reports it, so it is gated again.
  put(repo, "dist/tracked.js");
  git(repo, "add", "-f", "dist/tracked.js");
  git(repo, "commit", "-q", "-m", "force tracked");
  assert.equal(hook(gate(edit(join(repo, "dist/tracked.js")))).permissionDecision, "deny");
});

test("a failing git check-ignore does not allow the edit by itself", () => {
  const repo = makeRepo();
  const failing: (cwd: string, args: string[]) => string | undefined = (cwd, args) => {
    if (args.includes("check-ignore")) return undefined;
    try {
      return execFileSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    } catch {
      return undefined;
    }
  };
  assert.equal(hook(run(edit(join(repo, "src/app.ts")), { env: {}, git: failing })).permissionDecision, "deny");
});

test("the deny reason tells inline-test languages to use the exemption file", () => {
  const repo = makeRepo();
  const reason = hook(gate(edit(join(repo, "src/app.ts")))).permissionDecisionReason;
  assert.match(reason, /cfg\(test\)/);
  assert.match(reason, /inline/i);
});

test("a non-code file is allowed even when no test changed", () => {
  const repo = makeRepo();
  assert.equal(gate(edit(join(repo, "README.md"))), "");
  assert.equal(gate(edit(join(repo, "config/settings.json"))), "");
});

test("editing a test file is allowed", () => {
  const repo = makeRepo();
  assert.equal(gate(edit(join(repo, "src/app.test.ts"))), "");
  assert.equal(gate(edit(join(repo, "tests/helper.ts"))), "");
});

test("a production edit with no test change is denied, and the reason names the failing-test step and the exemption file", () => {
  const repo = makeRepo();
  const output = gate(edit(join(repo, "src/app.ts")));
  assert.ok(output.endsWith("\n"));
  const decision = hook(output);
  assert.equal(decision.hookEventName, "PreToolUse");
  assert.equal(decision.permissionDecision, "deny");
  assert.match(decision.permissionDecisionReason, /failing test/);
  assert.match(decision.permissionDecisionReason, /src\/app\.ts/);
  assert.match(decision.permissionDecisionReason, /wording|docs|renames|config values|wiring/);
  assert.match(decision.permissionDecisionReason, /OMO_TDD_GATE=off/);
  // The exemption file is printed as an absolute path under the repo (the macOS tmp dir is a symlink, so compare the tail).
  assert.match(decision.permissionDecisionReason, /\/\.claude\/omo\/tdd-exempt\/main\.txt/);
  assert.ok(decision.permissionDecisionReason.includes(join(".claude", "omo", "tdd-exempt", "main.txt")));
});

test("Write and MultiEdit are gated like Edit; other tools are not", () => {
  const repo = makeRepo();
  const file = join(repo, "src/app.ts");
  assert.equal(hook(gate(edit(file, "Write"))).permissionDecision, "deny");
  assert.equal(hook(gate(edit(file, "MultiEdit"))).permissionDecision, "deny");
  assert.equal(gate(edit(file, "Read")), "");
  assert.equal(gate(edit(file, "Bash")), "");
});

test("a production edit under a directory that does not exist yet is still gated against the enclosing repo", () => {
  const repo = makeRepo();
  assert.equal(hook(gate(edit(join(repo, "src/brand/new/dir/x.ts")))).permissionDecision, "deny");
  put(repo, "tests/x.test.ts");
  assert.equal(gate(edit(join(repo, "src/brand/new/dir/x.ts"))), "");
});

test("a production edit is allowed once an untracked test file exists", () => {
  const repo = makeRepo();
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  put(repo, "src/app.test.ts");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
});

test("a modified tracked test file in the working tree counts", () => {
  const repo = makeRepo();
  put(repo, "tests/a.py", "def test_a(): pass\n");
  git(repo, "add", "-A");
  git(repo, "commit", "-q", "-m", "add test on main");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  put(repo, "tests/a.py", "def test_a(): assert True\n");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
});

test("on a feature branch, a committed test change since the merge-base allows; a test committed on main before branching does not", () => {
  const repo = makeRepo();
  put(repo, "tests/old.test.ts");
  git(repo, "add", "-A");
  git(repo, "commit", "-q", "-m", "test already on main");
  git(repo, "checkout", "-q", "-b", "feature/x");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  put(repo, "src/app.ts", "export const a = 2;\n");
  git(repo, "commit", "-q", "-am", "prod only");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  put(repo, "tests/new.test.ts");
  git(repo, "add", "-A");
  git(repo, "commit", "-q", "-m", "add the test");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
});

test("the base is origin/HEAD when the repo has a remote", () => {
  const origin = scratch();
  git(origin, "init", "-q", "--bare", "-b", "trunk");
  const seed = scratch();
  git(seed, "init", "-q", "-b", "trunk");
  put(seed, "src/app.ts");
  git(seed, "add", "-A");
  git(seed, "commit", "-q", "-m", "init");
  git(seed, "remote", "add", "origin", origin);
  git(seed, "push", "-q", "origin", "trunk");
  const clone = join(scratch(), "clone");
  git(dirname(clone), "clone", "-q", origin, clone);
  git(clone, "checkout", "-q", "-b", "feat");
  assert.equal(hook(gate(edit(join(clone, "src/app.ts")))).permissionDecision, "deny");
  put(clone, "src/app.test.ts");
  git(clone, "add", "-A");
  git(clone, "commit", "-q", "-m", "test");
  assert.equal(gate(edit(join(clone, "src/app.ts"))), "");
});

const exempt = (repo: string, branchPath: string, body: string) => put(repo, join(".claude", "omo", "tdd-exempt", branchPath), body);

test("an exemption line with a reason allows that path and nothing else", () => {
  const repo = makeRepo();
  put(repo, "src/other.ts");
  exempt(repo, "main.txt", "# comment\n\nsrc/app.ts: rename only, no branch\n");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
  assert.equal(hook(gate(edit(join(repo, "src/other.ts")))).permissionDecision, "deny");
});

test("an exemption glob matches by path pattern", () => {
  const repo = makeRepo();
  exempt(repo, "main.txt", "src/gen/**/*.ts: generated wiring\nsrc/*.js: config values\n");
  assert.equal(gate(edit(join(repo, "src/gen/a/b/c.ts"))), "");
  assert.equal(gate(edit(join(repo, "src/gen/c.ts"))), "");
  assert.equal(gate(edit(join(repo, "src/x.js"))), "");
  assert.equal(hook(gate(edit(join(repo, "src/sub/x.js")))).permissionDecision, "deny");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
});

test("an exemption line without a reason does not count", () => {
  const repo = makeRepo();
  exempt(repo, "main.txt", "src/app.ts\nsrc/app.ts:\nsrc/app.ts:   \n");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
});

test("the exemption file is keyed by the branch name, nested for a branch with a slash", () => {
  const repo = makeRepo();
  git(repo, "checkout", "-q", "-b", "pbi/33");
  exempt(repo, "main.txt", "src/app.ts: wrong branch file\n");
  assert.equal(hook(gate(edit(join(repo, "src/app.ts")))).permissionDecision, "deny");
  exempt(repo, join("pbi", "33.txt"), "src/app.ts: docs-only constant text\n");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
  const reason = hook(gate(edit(join(repo, "src/other.ts")))).permissionDecisionReason;
  assert.ok(reason.includes(join(".claude", "omo", "tdd-exempt", "pbi", "33.txt")));
});

test("a detached HEAD uses HEAD.txt as the exemption file", () => {
  const repo = makeRepo();
  git(repo, "checkout", "-q", "--detach");
  const reason = hook(gate(edit(join(repo, "src/app.ts")))).permissionDecisionReason;
  assert.ok(reason.includes(join(".claude", "omo", "tdd-exempt", "HEAD.txt")));
  exempt(repo, "HEAD.txt", "src/app.ts: wording\n");
  assert.equal(gate(edit(join(repo, "src/app.ts"))), "");
});

test("OMO_TDD_GATE=off, 0, or false disables the gate", () => {
  const repo = makeRepo();
  const input = edit(join(repo, "src/app.ts"));
  for (const value of ["off", "0", "false", "OFF", "False"]) assert.equal(gate(input, { OMO_TDD_GATE: value }), "", value);
  assert.equal(hook(gate(input, { OMO_TDD_GATE: "on" })).permissionDecision, "deny");
});

test("a file outside any git repo is allowed", () => {
  const dir = scratch();
  assert.equal(gate(edit(join(dir, "src/app.ts"))), "");
  assert.equal(gate(edit(join(dir, "app.ts"))), "");
});

test("malformed input is allowed", () => {
  for (const input of [undefined, null, "text", 5, [], {}, { tool_name: "Edit" }, { tool_name: "Edit", tool_input: null }, edit(undefined), edit(7), edit(""), edit("   ")]) {
    assert.equal(gate(input), "", JSON.stringify(input));
  }
  assert.equal(gate({ hook_event_name: "PostToolUse", tool_name: "Edit", tool_input: { file_path: "/x/a.ts" } }), "");
});

test("a git runner that fails everywhere leaves the gate open", () => {
  const repo = makeRepo();
  assert.equal(run(edit(join(repo, "src/app.ts")), { env: {}, git: () => undefined }), "");
});

test("a git runner that cannot find a base ref leaves the gate open", () => {
  const repo = makeRepo();
  const git: (cwd: string, args: string[]) => string | undefined = (_cwd, args) => {
    if (args[0] === "rev-parse") return `${repo}\n`;
    if (args[0] === "symbolic-ref") return "main\n";
    return undefined;
  };
  assert.equal(run(edit(join(repo, "src/app.ts")), { env: {}, git }), "");
});

test("as a script: stdin JSON is gated, garbage stdin prints nothing", () => {
  const repo = makeRepo();
  const spawn = (stdin: string) => spawnSync(process.execPath, [HOOK_PATH], { input: stdin, encoding: "utf8", env: { ...process.env, OMO_TDD_GATE: "" } });
  const denied = spawn(JSON.stringify(edit(join(repo, "src/app.ts"))));
  assert.equal(denied.status, 0);
  assert.equal(hook(denied.stdout).permissionDecision, "deny");
  const garbage = spawn("not json");
  assert.equal(garbage.status, 0);
  assert.equal(garbage.stdout, "");
  put(repo, "tests/a.test.ts");
  assert.equal(spawn(JSON.stringify(edit(join(repo, "src/app.ts")))).stdout, "");
});
