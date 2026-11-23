// Run: node --test omo-orchestrator/hooks/merge-close-gate.test.ts
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { findGhTargets, run, uncheckedItems } from "./merge-close-gate.ts";

type Replies = Record<string, string | Error>;
const dirs: string[] = [];
after(() => {
  for (const dir of dirs) rmSync(dir, { recursive: true, force: true });
});

type CallOptions = { cwd?: string; timeoutMs?: number };

// A fake gh: replies are keyed by the joined args; an unknown call throws, like a gh that exits non-zero.
// `options` records the cwd and timeout each call was given; `onCall` lets a test move a fake clock.
function fakeGh(replies: Replies, onCall: () => void = () => {}) {
  const calls: string[] = [];
  const options: CallOptions[] = [];
  const gh = (args: string[], callOptions: CallOptions = {}): string => {
    const key = args.join(" ");
    calls.push(key);
    options.push(callOptions);
    onCall();
    const reply = replies[key];
    if (reply === undefined) throw new Error(`gh exited with status 1: no reply for ${key}`);
    if (reply instanceof Error) throw reply;
    return reply;
  };
  return { gh, calls, options };
}

const bash = (command: string) => ({ hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command } });
const body = (text: string) => JSON.stringify({ body: text });
const decision = (output: string) => JSON.parse(output).hookSpecificOutput;

const CHECKED = "## Acceptance Criteria\n- [x] done one\n- [x] done two\n";
const UNCHECKED = "## Acceptance Criteria\n- [x] done one\n- [ ] still open\n";

test("a command with no gh issue close or gh pr merge passes without calling gh", () => {
  const { gh, calls } = fakeGh({});
  assert.equal(run(bash("git status && gh pr view 3 && echo gh issue close"), { env: {}, gh }), "");
  assert.equal(run(bash("ls"), { env: {}, gh }), "");
  assert.deepEqual(calls, []);
});

test("gh issue close with every AC box checked passes", () => {
  const { gh, calls } = fakeGh({ "issue view --json body -- 12": body(CHECKED) });
  assert.equal(run(bash("gh issue close 12"), { env: {}, gh }), "");
  assert.deepEqual(calls, ["issue view --json body -- 12"]);
});

test("gh issue close with an unchecked AC item is denied and names the item and its issue", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": body(UNCHECKED) });
  const output = run(bash("gh issue close 12"), { env: {}, gh });
  assert.ok(output.endsWith("\n"));
  const hook = decision(output);
  assert.equal(hook.hookEventName, "PreToolUse");
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /still open/);
  assert.match(hook.permissionDecisionReason, /issue 12/);
  assert.match(hook.permissionDecisionReason, /file:line/);
  assert.match(hook.permissionDecisionReason, /OMO_MERGE_GATE=off/);
});

test("an unchecked box outside an AC / DoR / DoD section passes", () => {
  const { gh } = fakeGh({
    "issue view --json body -- 5": body("## Notes\n- [ ] remember to tell Bob\n\n## Acceptance Criteria\n- [x] shipped\n\n## Follow-ups\n- [ ] later\n"),
  });
  assert.equal(run(bash("gh issue close 5"), { env: {}, gh }), "");
});

test("a body with no AC section has nothing to check and passes", () => {
  const { gh } = fakeGh({ "issue view --json body -- 5": body("just prose\n- [ ] a loose task\n") });
  assert.equal(run(bash("gh issue close 5"), { env: {}, gh }), "");
});

test("closing as not planned or duplicate is not a completion and passes without calling gh", () => {
  const { gh, calls } = fakeGh({});
  for (const command of [
    'gh issue close 12 --reason "not planned"',
    "gh issue close 12 -r 'not planned'",
    "gh issue close 12 --reason=not_planned",
    "gh issue close 12 -r duplicate",
    "gh issue close 12 --duplicate-of 3",
  ]) {
    assert.equal(run(bash(command), { env: {}, gh }), "", command);
  }
  assert.deepEqual(calls, []);
});

test("closing as completed is still gated", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": body(UNCHECKED) });
  assert.equal(decision(run(bash("gh issue close 12 --reason completed"), { env: {}, gh })).permissionDecision, "deny");
});

test("gh pr merge is denied when the PR body has an unchecked DoD item", () => {
  const { gh } = fakeGh({
    "pr view --json body,closingIssuesReferences -- 7": JSON.stringify({
      body: "### Definition of Done\n- [ ] docs updated\n",
      closingIssuesReferences: [],
    }),
  });
  const hook = decision(run(bash("gh pr merge 7 --squash"), { env: {}, gh }));
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /docs updated/);
  assert.match(hook.permissionDecisionReason, /PR 7/);
});

test("gh pr merge is denied when a closing issue has an unchecked item, and the issue body is read by its url", () => {
  const url = "https://github.com/o/r/issues/9";
  const { gh, calls } = fakeGh({
    "pr view --json body,closingIssuesReferences -- 7": JSON.stringify({
      body: "## AC\n- [x] ok\n",
      closingIssuesReferences: [{ number: 9, url }],
    }),
    [`issue view --json body -- ${url}`]: body("**受け入れ基準**\n- [ ] 画面に表示される\n"),
  });
  const hook = decision(run(bash("gh pr merge 7"), { env: {}, gh }));
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /画面に表示される/);
  assert.match(hook.permissionDecisionReason, /#9/);
  assert.equal(calls.length, 2);
});

test("gh pr merge with everything checked passes; with no argument the current branch PR is read", () => {
  const { gh, calls } = fakeGh({
    "pr view --json body,closingIssuesReferences": JSON.stringify({ body: CHECKED, closingIssuesReferences: [] }),
  });
  assert.equal(run(bash("gh pr merge --auto --squash --delete-branch"), { env: {}, gh }), "");
  assert.deepEqual(calls, ["pr view --json body,closingIssuesReferences"]);
});

test("a gh failure is denied: the gate fails closed", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": new Error("gh: command not found") });
  const hook = decision(run(bash("gh issue close 12"), { env: {}, gh }));
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /could not judge/);
  assert.match(hook.permissionDecisionReason, /gh: command not found/);
  assert.match(hook.permissionDecisionReason, /OMO_MERGE_GATE=off/);
});

test("unparseable gh output is denied", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": "not json" });
  const hook = decision(run(bash("gh issue close 12"), { env: {}, gh }));
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /could not judge/);
});

test("a gh reply whose body is not a string is denied", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": JSON.stringify({ body: 3 }) });
  assert.equal(decision(run(bash("gh issue close 12"), { env: {}, gh })).permissionDecision, "deny");
});

test("an error in one target does not hide an unchecked item in another", () => {
  const { gh } = fakeGh({
    "issue view --json body -- 1": body(UNCHECKED),
    "issue view --json body -- 2": new Error("timed out"),
  });
  const reason = decision(run(bash("gh issue close 1 && gh issue close 2"), { env: {}, gh })).permissionDecisionReason;
  assert.match(reason, /still open/);
  assert.match(reason, /timed out/);
});

test("OMO_MERGE_GATE=off|0|false disables the whole gate", () => {
  const { gh, calls } = fakeGh({});
  for (const value of ["off", "0", "false", "OFF"]) {
    assert.equal(run(bash("gh issue close 12"), { env: { OMO_MERGE_GATE: value }, gh }), "", value);
  }
  assert.deepEqual(calls, []);
});

test("a chained, piped, or multi-line command is scanned", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": body(UNCHECKED) });
  for (const command of [
    "git push && gh issue close 12",
    "make test; gh issue close 12 --comment 'done'",
    "echo ok | gh issue close 12",
    "git status\ngh issue close 12\n",
    "cd x || gh issue close 12",
    "GH_TOKEN=abc gh issue close 12",
    'bash -c "gh issue close 12"',
    "echo $(gh issue close 12)",
  ]) {
    assert.equal(decision(run(bash(command), { env: {}, gh })).permissionDecision, "deny", command);
  }
});

test("a gh call that follows a shell control keyword (if, then, do, !, {) is still scanned", () => {
  const { gh } = fakeGh({ "issue view --json body -- 12": body(UNCHECKED) });
  for (const command of [
    "if gh issue close 12; then echo ok; fi",
    "make test && if gh issue close 12; then echo ok; fi",
    "while true; do gh issue close 12; done",
    "for n in 1; do gh issue close 12; done",
    "! gh issue close 12",
    "{ gh issue close 12; }",
    "test -f x && then_flag=1 || gh issue close 12",
    "if true; then gh issue close 12; else echo no; fi",
  ]) {
    assert.equal(decision(run(bash(command), { env: {}, gh })).permissionDecision, "deny", command);
  }
});

test("text that only mentions the command (quotes, comments) is not a command", () => {
  const { gh, calls } = fakeGh({});
  for (const command of [
    'echo "gh issue close 12"',
    "git commit -m 'docs: explain gh pr merge gate'",
    "ls # gh pr merge 3",
  ]) {
    assert.equal(run(bash(command), { env: {}, gh }), "", command);
  }
  assert.deepEqual(calls, []);
});

test("-R / --repo is passed through to gh", () => {
  const { gh, calls } = fakeGh({
    "issue view -R o/r --json body -- 12": body(CHECKED),
    "issue view -R o/r --json body -- 13": body(CHECKED),
    "pr view -R o/r --json body,closingIssuesReferences -- 7": JSON.stringify({
      body: CHECKED,
      closingIssuesReferences: [{ number: 9 }],
    }),
    "issue view -R o/r --json body -- 9": body(CHECKED),
  });
  assert.equal(run(bash("gh issue close 12 -R o/r"), { env: {}, gh }), "");
  assert.equal(run(bash("gh issue close --repo o/r 13 --comment hi"), { env: {}, gh }), "");
  assert.equal(run(bash("gh pr merge 7 --squash -R o/r"), { env: {}, gh }), "");
  assert.deepEqual(calls, [
    "issue view -R o/r --json body -- 12",
    "issue view -R o/r --json body -- 13",
    "pr view -R o/r --json body,closingIssuesReferences -- 7",
    "issue view -R o/r --json body -- 9",
  ]);
});

test("-R / --repo placed before the subcommand or between group and action is read and passed through", () => {
  const { gh, calls } = fakeGh({
    "issue view -R o/r --json body -- 12": body(UNCHECKED),
    "pr view -R o/r --json body,closingIssuesReferences -- 7": JSON.stringify({ body: UNCHECKED, closingIssuesReferences: [] }),
  });
  for (const command of ["gh -R o/r issue close 12", "gh --repo o/r issue close 12", "gh --repo=o/r issue close 12", "gh issue -R o/r close 12", "gh -Ro/r issue close 12"]) {
    assert.equal(decision(run(bash(command), { env: {}, gh })).permissionDecision, "deny", command);
  }
  for (const command of ["gh -R o/r pr merge 7", "gh pr --repo o/r merge 7 --squash"]) {
    assert.equal(decision(run(bash(command), { env: {}, gh })).permissionDecision, "deny", command);
  }
  assert.equal(calls.length, 7);
  assert.deepEqual(findGhTargets("gh --repo o/r issue close 12 --reason 'not planned'"), []);
});

test("a value of --comment or --body is not taken for the target", () => {
  const targets = findGhTargets('gh issue close --comment "fixed in 5" 12; gh pr merge --body "see 4" 7');
  assert.deepEqual(targets, [
    { kind: "issue", arg: "12", repo: undefined },
    { kind: "pr", arg: "7", repo: undefined },
  ]);
});

test("more than 10 unchecked items are listed up to 10 with a count of the rest", () => {
  const items = Array.from({ length: 13 }, (_, i) => `- [ ] item-${i + 1}`).join("\n");
  const { gh } = fakeGh({ "issue view --json body -- 12": body(`## DoD\n${items}\n`) });
  const reason = decision(run(bash("gh issue close 12"), { env: {}, gh })).permissionDecisionReason;
  assert.match(reason, /item-10\b/);
  assert.doesNotMatch(reason, /item-11\b/);
  assert.match(reason, /3 more/);
});

test("input that is not a Bash PreToolUse call passes", () => {
  const { gh } = fakeGh({});
  assert.equal(run(undefined, { env: {}, gh }), "");
  assert.equal(run("x", { env: {}, gh }), "");
  assert.equal(run({ tool_name: "Read", tool_input: { command: "gh issue close 1" } }, { env: {}, gh }), "");
  assert.equal(run({ tool_name: "Bash", tool_input: {} }, { env: {}, gh }), "");
  assert.equal(run({ tool_name: "Bash", tool_input: { command: 3 } }, { env: {}, gh }), "");
  assert.equal(run({ hook_event_name: "PostToolUse", tool_name: "Bash", tool_input: { command: "gh issue close 1" } }, { env: {}, gh }), "");
});

test("uncheckedItems: heading sections end at a same-or-higher heading and keep deeper ones", () => {
  const text = [
    "## Acceptance Criteria",
    "- [ ] a",
    "### Details",
    "* [ ] b",
    "## Other",
    "- [ ] not counted",
    "# DoR",
    "- [ ] c",
  ].join("\n");
  assert.deepEqual(uncheckedItems(text), ["a", "b", "c"]);
});

test("uncheckedItems: bold label lines open a section that ends at the next heading or label", () => {
  const text = [
    "**AC:**",
    "- [ ] a",
    "**Notes**",
    "- [ ] not counted",
    "__Definition of Ready__",
    "- [ ] b",
    "## Plain",
    "- [ ] not counted either",
  ].join("\n");
  assert.deepEqual(uncheckedItems(text), ["a", "b"]);
});

test("uncheckedItems: a bold sub-label inside a heading-opened section does not end it", () => {
  const text = ["## AC", "**User flow**", "- [ ] a", "__Edge cases__", "- [ ] b", "## Other", "- [ ] not counted"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["a", "b"]);
});

test("uncheckedItems: a non-gated sub-heading inside an AC section stays in scope until a heading of the same or higher level", () => {
  const text = ["## AC", "### DoD", "- [ ] dod item", "### User flow", "- [ ] flow item", "#### Deeper", "- [ ] deeper item", "## Notes", "- [ ] not counted"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["dod item", "flow item", "deeper item"]);
});

test("uncheckedItems: items under ### User flow within ## AC are counted, items after the following ## Notes are not", () => {
  const text = ["## AC", "### User flow", "- [ ] flow item", "## Notes", "- [ ] note item"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["flow item"]);
});

test("uncheckedItems: a nested gated heading does not reset the outer section depth", () => {
  const text = ["## AC", "### DoR", "- [ ] a", "### Edge cases", "- [ ] b", "# Top", "- [ ] not counted"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["a", "b"]);
});

test("uncheckedItems: a nested gated bold label inside a heading section does not reset its depth", () => {
  const text = ["## AC", "**DoD**", "- [ ] a", "**User flow**", "- [ ] b", "## Other", "- [ ] not counted"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["a", "b"]);
});

test("uncheckedItems: a gated heading nested in a non-gated section opens its own scope", () => {
  const text = ["## Notes", "- [ ] not counted", "### DoD", "- [ ] a", "### Other", "- [ ] not counted either"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["a"]);
});

test("uncheckedItems: a fence closes only on the same character with at least the opening length", () => {
  const text = ["## AC", "````md", "```", "- [ ] inside the outer fence", "````", "- [ ] after the fence", "~~~", "- [ ] tilde fence", "```", "- [ ] still inside", "~~~", "- [ ] after tilde"].join("\n");
  assert.deepEqual(uncheckedItems(text), ["after the fence", "after tilde"]);
});

test("uncheckedItems: matches the section names case-insensitively and ignores checked items, code fences, and HTML comments", () => {
  const text = [
    "## acceptance CRITERIA",
    "- [x] checked",
    "- [X] checked upper",
    "<!-- - [ ] template item -->",
    "```",
    "- [ ] in a fence",
    "```",
    "## 完了条件",
    "- [ ] 日本語",
    "## ACME plan",
    "- [ ] not an AC heading",
  ].join("\n");
  assert.deepEqual(uncheckedItems(text), ["日本語"]);
});

test("uncheckedItems: CRLF bodies are read", () => {
  assert.deepEqual(uncheckedItems("## DoD\r\n- [ ] a\r\n- [x] b\r\n"), ["a"]);
});

// Heredoc bodies are data for the command that reads them, not commands.
test("heredoc bodies are not scanned as commands, for every delimiter form", () => {
  for (const command of [
    "cat > notes.md <<'EOF'\ngh pr merge 12\nEOF",
    "cat > notes.md <<EOF\ngh pr merge 12\nEOF\n",
    'cat > notes.md <<"EOF"\ngh issue close 12\nEOF',
    "cat > notes.md <<-EOF\n\tgh issue close 12\n\tEOF\n",
    "cat > notes.md <<-'END'\n\tgh pr merge 12\n\tEND",
    "cat <<\\EOF\ngh pr merge 12\nEOF",
    "cat <<  EOF\ngh pr merge 12\nEOF",
    "cat <<EOF >out.txt\ngh pr merge 12\nEOF",
    "cat <<A <<B\ngh pr merge 1\nA\ngh pr merge 2\nB",
    "cat <<EOF\ngh pr merge 12",
  ]) {
    assert.deepEqual(findGhTargets(command), [], command);
  }
});

test("a command after the heredoc terminator, or on the heredoc line itself, is still scanned", () => {
  assert.deepEqual(findGhTargets("cat <<EOF\nbody\nEOF\ngh pr merge 12"), [{ kind: "pr", arg: "12", repo: undefined }]);
  assert.deepEqual(findGhTargets("cat <<'EOF' && gh issue close 5\nbody\nEOF"), [{ kind: "issue", arg: "5", repo: undefined }]);
  assert.deepEqual(findGhTargets("cat <<-EOF\n\tbody\n\tEOF\ngh pr merge 3"), [{ kind: "pr", arg: "3", repo: undefined }]);
  // A line that only starts with the delimiter does not end the body.
  assert.deepEqual(findGhTargets("cat <<EOF\nEOF2\ngh pr merge 9\nEOF\ngh pr merge 4"), [{ kind: "pr", arg: "4", repo: undefined }]);
  // A here-string is not a heredoc.
  assert.deepEqual(findGhTargets("cat <<< word\ngh pr merge 6"), [{ kind: "pr", arg: "6", repo: undefined }]);
});

test("a command substitution inside double quotes is scanned as a command", () => {
  assert.deepEqual(findGhTargets('result="$(gh pr merge 42 --squash)"'), [{ kind: "pr", arg: "42", repo: undefined }]);
  assert.deepEqual(findGhTargets('echo "$(gh issue close 5)"'), [{ kind: "issue", arg: "5", repo: undefined }]);
  assert.deepEqual(findGhTargets('echo "done: `gh issue close 7` ok"'), [{ kind: "issue", arg: "7", repo: undefined }]);
  assert.deepEqual(findGhTargets('echo "a $(echo "$(gh pr merge 8)") b"'), [{ kind: "pr", arg: "8", repo: undefined }]);
  assert.deepEqual(findGhTargets('echo "$(echo ")" && gh pr merge 9)"'), [{ kind: "pr", arg: "9", repo: undefined }]);
  assert.deepEqual(findGhTargets('echo "$(cd x; gh pr merge 10)"'), [{ kind: "pr", arg: "10", repo: undefined }]);
  assert.deepEqual(findGhTargets("bash -c \"echo \\\"$(gh pr merge 11)\\\"\""), [{ kind: "pr", arg: "11", repo: undefined }]);
});

test("plain mentions of a merge or close in quotes, single-quoted substitutions, and escaped substitutions are not commands", () => {
  for (const command of [
    'git commit -m "gh pr merge"',
    'echo "gh issue close 5"',
    "echo '$(gh pr merge 42)'",
    "echo '`gh pr merge 42`'",
    'echo "\\$(gh pr merge 42)"',
    'echo "\\`gh pr merge 42\\`"',
    'echo "$(echo hi) and gh pr merge 3"',
  ]) {
    assert.deepEqual(findGhTargets(command), [], command);
  }
});

test("an unterminated substitution inside double quotes is scanned to the end of the command", () => {
  assert.deepEqual(findGhTargets('echo "$(gh pr merge 3'), [{ kind: "pr", arg: "3", repo: undefined }]);
});

test("a merge inside a double-quoted substitution is gated by run", () => {
  const { gh } = fakeGh({ "pr view --json body,closingIssuesReferences -- 42": JSON.stringify({ body: UNCHECKED, closingIssuesReferences: [] }) });
  const hook = decision(run(bash('result="$(gh pr merge 42 --squash)"'), { env: {}, gh }));
  assert.equal(hook.permissionDecision, "deny");
});

test("a heredoc command that mentions a merge in its body passes without calling gh", () => {
  const { gh, calls } = fakeGh({});
  assert.equal(run(bash("cat > notes.md <<'EOF'\ngh pr merge 12\nEOF"), { env: {}, gh }), "");
  assert.deepEqual(calls, []);
});

// `--` keeps a value that starts with `-` from being read as a gh flag (gh accepts `gh issue view --json body -- <n>`).
test("gh view calls put the issue or PR argument after --, so a leading dash is never a flag", () => {
  const { gh, calls } = fakeGh({
    "issue view --json body -- -5": body(CHECKED),
    "pr view --json body,closingIssuesReferences -- -x": JSON.stringify({ body: CHECKED, closingIssuesReferences: [] }),
  });
  assert.equal(run(bash("gh issue close -- -5"), { env: {}, gh }), "");
  assert.equal(run(bash("gh pr merge -- -x"), { env: {}, gh }), "");
  assert.deepEqual(calls, ["issue view --json body -- -5", "pr view --json body,closingIssuesReferences -- -x"]);
});

test("gh runs in the hook input cwd when it is an existing directory, else in the hook's own cwd", () => {
  const dir = mkdtempSync(join(tmpdir(), "merge-gate-"));
  dirs.push(dir);
  const file = join(dir, "a-file");
  writeFileSync(file, "x");
  const { gh, options } = fakeGh({ "issue view --json body -- 12": body(CHECKED) });
  const withCwd = (cwd: unknown) => run({ ...bash("gh issue close 12"), cwd }, { env: {}, gh });
  for (const cwd of [dir, undefined, 7, null, join(dir, "missing"), file, ""]) assert.equal(withCwd(cwd), "");
  assert.deepEqual(
    options.map((entry) => entry.cwd),
    [dir, undefined, undefined, undefined, undefined, undefined, undefined],
  );
});

test("a GH_REPO assignment in front of the command is passed as -R; an explicit -R / --repo wins", () => {
  assert.deepEqual(findGhTargets("GH_REPO=o/r gh pr merge 7"), [{ kind: "pr", arg: "7", repo: "o/r" }]);
  assert.deepEqual(findGhTargets("env GH_REPO=o/r gh issue close 12"), [{ kind: "issue", arg: "12", repo: "o/r" }]);
  assert.deepEqual(findGhTargets("GH_TOKEN=t GH_REPO=o/r gh issue close 12"), [{ kind: "issue", arg: "12", repo: "o/r" }]);
  assert.deepEqual(findGhTargets("GH_REPO=o/r gh pr merge 7 -R x/y"), [{ kind: "pr", arg: "7", repo: "x/y" }]);
  assert.deepEqual(findGhTargets("GH_REPO=o/r gh issue close --repo x/y 12"), [{ kind: "issue", arg: "12", repo: "x/y" }]);
  // The assignment belongs to its own command only.
  assert.deepEqual(findGhTargets("GH_REPO=o/r echo hi; gh pr merge 7"), [{ kind: "pr", arg: "7", repo: undefined }]);
  const { gh, calls } = fakeGh({ "issue view -R o/r --json body -- 12": body(CHECKED) });
  assert.equal(run(bash("GH_REPO=o/r gh issue close 12"), { env: {}, gh }), "");
  assert.deepEqual(calls, ["issue view -R o/r --json body -- 12"]);
});

// A fake clock moved by each gh call: 10s per call against the 25s overall deadline.
test("each gh call gets min(6s, remaining) and a target not read before the 25s deadline is denied (fail closed)", () => {
  let now = 0;
  const reply = body(CHECKED);
  const { gh, calls, options } = fakeGh(
    { "issue view --json body -- 1": reply, "issue view --json body -- 2": reply, "issue view --json body -- 3": reply, "issue view --json body -- 4": reply },
    () => {
      now += 10_000;
    },
  );
  const hook = decision(run(bash("gh issue close 1 2 3 4"), { env: {}, gh, now: () => now }));
  assert.deepEqual(options.map((entry) => entry.timeoutMs), [6000, 6000, 5000]);
  assert.equal(calls.length, 3);
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /could not judge/);
  assert.match(hook.permissionDecisionReason, /issue 4/);
  assert.match(hook.permissionDecisionReason, /25s/);
  assert.match(hook.permissionDecisionReason, /time budget/);
});

test("a deadline that is already exhausted denies without calling gh", () => {
  const { gh, calls } = fakeGh({});
  const hook = decision(run(bash("gh issue close 12"), { env: {}, gh, deadlineMs: 0 }));
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /time budget/);
  assert.deepEqual(calls, []);
});

test("within the deadline every call gets the 6s cap", () => {
  const { gh, options } = fakeGh({ "issue view --json body -- 12": body(CHECKED) });
  assert.equal(run(bash("gh issue close 12"), { env: {}, gh }), "");
  assert.deepEqual(options.map((entry) => entry.timeoutMs), [6000]);
});
