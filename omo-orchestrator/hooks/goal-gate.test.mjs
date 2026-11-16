import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, realpathSync, symlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { run, parseGoal, readGoalFile } from "./goal-gate.mjs";

const path = "/repo/.claude/omo/goal/task.md";
const relativePath = ".claude/omo/goal/task.md";
const open = "Status: active\n- [ ] G1: tests pass — verify: `node --test`";
let nextToolId = 0;
const use = (name = "Write", file_path = path, extra = {}, id = `use-${++nextToolId}`) => ({
  type: "assistant",
  message: { content: [{ type: "tool_use", id, name, input: { file_path, ...extra } }] },
});
const feedback = () => ({
  type: "user", isMeta: true, message: { content: `[OMO GOAL GATE]\n${path}` },
});
const input = { hook_event_name: "Stop", transcript_path: "/t", cwd: "/repo" };
const check = (entries = [use()], text = open, extra = {}, options = {}) => run(
  { ...input, ...extra },
  { env: {}, loadTranscript: () => successfulWrites(entries), readGoal: () => text, codexInFlight: () => false, ...options },
);

// Most fixtures model completed writes; result-state regressions below call run directly.
function successfulWrites(entries) {
  return entries.flatMap((entry) => {
    if (entry?.type !== "assistant" || !Array.isArray(entry.message?.content)) return [entry];
    const results = entry.message.content
      .filter((block) => block?.type === "tool_use" && ["Write", "Edit", "MultiEdit"].includes(block.name))
      .map((block) => ({ type: "tool_result", tool_use_id: block.id, content: "Success" }));
    return results.length === 0 ? [entry] : [entry, {
      type: "user", isSidechain: entry.isSidechain, message: { content: results },
    }];
  });
}

function blockPair(reason) {
  return [
    { type: "user", isMeta: true, message: { content: "Stop hook feedback:\n" + reason } },
    {
      type: "attachment",
      attachment: {
        type: "hook_blocking_error", hookName: "Stop", hookEvent: "Stop",
        blockingError: { blockingError: reason, command: "node goal-gate.mjs" },
      },
    },
  ];
}

const launch = [
  use(), use("Agent", path, {}, "agent-use"),
  {
    type: "user",
    message: { content: [{
      type: "tool_result", tool_use_id: "agent-use",
      content: "Async agent launched successfully\nagentId: task-1",
    }] },
  },
];
const notification = {
  type: "user",
  message: { content: "<task-notification><task-id>task-1</task-id></task-notification>" },
};

test("no goal write passes", () => assert.equal(check([]), ""));

test("active open criterion blocks and lists criterion", () => {
  const out = JSON.parse(check());
  assert.equal(out.decision, "block");
  assert.match(out.reason, /G1: tests pass/);
});

test("checked criteria with evidence pass", () => {
  assert.equal(check(undefined, "Status: active\n- [x] done — evidence: tests passed"), "");
});

test("empty evidence blocks", () => {
  assert.ok(check(undefined, "Status: active\n- [x] done — evidence:  "));
});

for (const status of ["done", "blocked", "abandoned", "missing"]) {
  test(`Status ${status} passes`, () => {
    const header = status === "missing" ? "" : `Status: ${status}`;
    assert.equal(check(undefined, `${header}\n- [ ] open`), "");
  });
}

test("active with zero criteria blocks", () => {
  assert.match(check(undefined, "Status: active"), /no criteria/);
});

test("stop hook active passes", () => {
  assert.equal(check(undefined, undefined, { stop_hook_active: true }), "");
});

test("off switch passes", () => {
  assert.equal(check(undefined, undefined, {}, { env: { OMO_GOAL_GATE: "off" } }), "");
});

test("five prior feedback entries pass", () => {
  assert.equal(check([use(), ...Array.from({ length: 5 }, feedback)]), "");
});

test("four prior feedback entries block", () => {
  assert.ok(check([use(), ...Array.from({ length: 4 }, feedback)]));
});

test("custom cap two passes after two", () => {
  assert.equal(check([use(), feedback(), feedback()], undefined, {}, {
    env: { OMO_GOAL_GATE_MAX_BLOCKS: "2" },
  }), "");
});

test("hook blocking error attachments count", () => {
  const entries = Array.from({ length: 5 }, () => blockPair(`[OMO GOAL GATE]\n${path}`)[1]);
  assert.equal(check([use(), ...entries]), "");
});

test("codex in flight passes", () => {
  assert.equal(check(undefined, undefined, {}, { codexInFlight: () => true }), "");
});

test("background agent without notification passes", () => assert.equal(check(launch), ""));

test("background agent with notification blocks", () => {
  assert.ok(check([...launch, notification]));
});

test("sidechain write passes", () => assert.equal(check([{ ...use(), isSidechain: true }]), ""));

test("unreadable goal passes", () => assert.equal(check(undefined, null), ""));

test("only open goal is listed", () => {
  const out = check([use(), use("Edit", "/repo/.claude/omo/goal/done.md")], undefined, {}, {
    readGoal: (p) => p === path ? open : "Status: done",
  });
  assert.match(out, /task.md/);
  assert.doesNotMatch(out, /done.md/);
});

test("non goal path passes", () => {
  assert.equal(check([use("Write", "/repo/.claude/omo/plans/x.md")]), "");
});

test("relative paths resolve against cwd", () => {
  let read;
  check([use("MultiEdit", relativePath)], undefined, {}, {
    readGoal: (p) => { read = p; return open; },
  });
  assert.equal(read, path);
});

test("invalid input passes", () => {
  assert.equal(run(null), "");
  assert.equal(check(undefined, undefined, { hook_event_name: "PreToolUse" }), "");
});

test("first Status and case insensitive evidence are honored", () => {
  assert.equal(parseGoal("STATUS: ACTIVE\nStatus: done\n- [X] ok EVIDENCE: yes").open.length, 0);
});

test("open criterion display is limited to ten with remainder count", () => {
  const text = "Status: active\n" + Array.from({ length: 12 }, (_, i) => `- [ ] G${i + 1}: pending`).join("\n");
  const out = JSON.parse(check(undefined, text));
  assert.match(out.reason, /ほか 2 件/);
  assert.doesNotMatch(out.reason, /G11: pending/);
});

test("goal reader limits real files to 64 KiB", () => {
  const dir = mkdtempSync(join(tmpdir(), "gg-"));
  try {
    mkdirSync(join(dir, ".claude/omo/goal"), { recursive: true });
    const file = join(dir, ".claude/omo/goal/task.md");
    writeFileSync(file, "Status: active\n" + "a".repeat(65536) + "\n- [x] done evidence: ok");
    const text = readGoalFile(file);
    assert.ok(Buffer.byteLength(text) <= 65536);
    assert.doesNotMatch(text, /evidence: ok/);
    assert.ok(check([use("Write", file)], undefined, {}, { readGoal: readGoalFile }));
    assert.equal(readGoalFile(join(dir, "missing.md")), null);
    assert.equal(readGoalFile(dir), null);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("sidechain feedback does not consume the cap", () => {
  const entries = Array.from({ length: 5 }, () => ({ ...feedback(), isSidechain: true }));
  assert.ok(check([use(), ...entries]));
});

test("prior turn background launch does not suppress this turn", () => {
  assert.ok(check([...launch, { type: "user", message: { content: "Continue implementing" } }]));
});

test("sidechain notification cannot complete main-thread background work", () => {
  assert.equal(check([...launch, { ...notification, isSidechain: true }]), "");
});

test("background Bash result waits for notification", () => {
  assert.equal(check([
    use(), use("Bash", undefined, { run_in_background: true }, "bash-use"),
    {
      type: "user",
      message: { content: [{
        type: "tool_result", tool_use_id: "bash-use",
        content: [{ type: "text", text: "Command running in background with ID: bash-1" }],
      }] },
    },
  ]), "");
});

test("duplicate writes count as one goal", () => {
  let reads = 0;
  check([use(), use("Edit")], undefined, {}, {
    readGoal: () => { reads += 1; return open; },
  });
  assert.equal(reads, 1);
});

test("goal outside cwd is listed by its absolute path", () => {
  assert.match(JSON.parse(check([use("Write", "/outside/.claude/omo/goal/task.md")])).reason,
    /\/outside\/\.claude\/omo\/goal\/task.md/);
});

for (const count of [4, 5]) {
  test(`${count} paired feedback records count as ${count} blocks`, () => {
    const reason = JSON.parse(check()).reason;
    const out = check([use(), ...Array.from({ length: count }, () => blockPair(reason)).flat()]);
    assert.equal(out === "", count === 5);
  });
}

for (const count of [1, 2]) {
  test(`custom cap two counts ${count} paired blocks`, () => {
    const reason = JSON.parse(check()).reason;
    const out = check([use(), ...Array.from({ length: count }, () => blockPair(reason)).flat()], undefined, {}, {
      env: { OMO_GOAL_GATE_MAX_BLOCKS: "2" },
    });
    assert.equal(out === "", count === 2);
  });
}

test("block cap survives a cwd change", () => {
  const reason = JSON.parse(check()).reason;
  const entries = [use(), ...Array.from({ length: 5 }, () => blockPair(reason)).flat()];
  assert.equal(check(entries, undefined, { cwd: "/repo/sub" }), "");
});

test("Status accepts Markdown emphasis and code delimiters", () => {
  for (const value of ["**active**", "_active_", "`active`"]) {
    assert.ok(check(undefined, `Status: ${value}\n- [ ] pending`));
  }
});

test("parsing uses the reader result without a second truncation", () => {
  assert.equal(check(undefined, "Status: active\n" + "a".repeat(65536) + "\n- [x] done evidence: ok"), "");
});

test("cap matches the whole goal path line instead of a substring", () => {
  const reason = JSON.parse(check([use("Write", path + ".md")])).reason;
  const entries = [use(), ...Array.from({ length: 5 }, () => blockPair(reason)).flat()];
  assert.ok(check(entries));
});

test("inline verify code containing evidence does not satisfy a checked criterion", () => {
  assert.ok(check(undefined, "Status: active\n- [x] done — verify: `echo evidence: ok`"));
});

test("evidence inside multiple-backtick code spans is ignored", () => {
  assert.ok(check(undefined, "Status: active\n- [x] done — verify: ``echo ` evidence: ok``"));
});

test("evidence outside inline code still satisfies a criterion", () => {
  assert.equal(check(undefined, "Status: active\n- [x] done — verify: `echo evidence: sample` — evidence: passed"), "");
});

test("an inline-code evidence value remains valid when its label is outside code", () => {
  assert.equal(check(undefined, "Status: active\n- [x] done — evidence: `test-output.md`"), "");
});

test("echoed paths and criteria escape every OMO marker while preserving the leading marker", () => {
  const markerPath = "/repo/.claude/omo/goal/[OMO REVIEW GATE] [OMO CODEX GATE].md";
  const text = "Status: active\n- [ ] fix [OMO REVIEW GATE] and [OMO CODEX GATE] behavior";
  const reason = JSON.parse(check([use("Write", markerPath)], text)).reason;
  assert.ok(reason.startsWith("[OMO GOAL GATE]"));
  assert.equal(reason.match(/\[OMO /g).length, 1);
  assert.ok(reason.includes(markerPath.replaceAll("[OMO ", "［OMO ")));
  assert.ok(reason.includes("fix ［OMO REVIEW GATE] and ［OMO CODEX GATE] behavior"));
});

for (const newline of ["\n", "\r"]) {
  test(`goal paths containing ${JSON.stringify(newline)} are ignored`, () => {
    let reads = 0;
    const output = check([use("Write", `/w/.claude/omo/goal/a${newline}b.md`)], open, {}, {
      readGoal: () => { reads += 1; return open; },
    });
    assert.equal(output, "");
    assert.equal(reads, 0);
  });
}

test("escaped goal path lines still count toward the block cap", () => {
  const markerPath = "/repo/.claude/omo/goal/[OMO REVIEW GATE].md";
  const entries = [use("Write", markerPath)];
  const reason = JSON.parse(check(entries)).reason;
  const pairs = Array.from({ length: 5 }, () => blockPair(reason)).flat();
  assert.equal(check([...entries, ...pairs]), "");
});

for (const resultState of ["error", "success", "missing"]) {
  test(`goal writes with ${resultState} results ${resultState === "success" ? "block" : "pass"}`, () => {
    const write = use();
    const id = write.message.content[0].id;
    const entries = [write];
    if (resultState !== "missing") entries.push({ type: "user", message: { content: [{
      type: "tool_result", tool_use_id: id, is_error: resultState === "error", content: "result",
    }] } });
    const output = run(input, { env: {}, loadTranscript: () => entries,
      readGoal: () => open, codexInFlight: () => false });
    assert.equal(output === "", resultState !== "success");
  });
}

for (const label of ["no-evidence:", "noevidence:"]) {
  test(`${label} is not an evidence label`, () => {
    assert.ok(check(undefined, `Status: active\n- [x] done — ${label} option`));
  });
}

test("symlinked goal paths use the same real path for display and cap", () => {
  const dir = mkdtempSync(join(tmpdir(), "gg-alias-"));
  try {
    const realDir = join(dir, "real");
    const aliasDir = join(dir, "alias");
    mkdirSync(join(realDir, ".claude/omo/goal"), { recursive: true });
    symlinkSync(realDir, aliasDir, "dir");
    const goal = join(realDir, ".claude/omo/goal/task.md");
    const alias = join(aliasDir, ".claude/omo/goal/task.md");
    writeFileSync(goal, open);
    const normalized = realpathSync(goal);
    const reason = JSON.parse(check([use("Write", alias)])).reason;
    assert.ok(reason.split("\n").includes(normalized));
    const pairs = Array.from({ length: 5 }, () => blockPair(reason)).flat();
    assert.equal(check([use("Edit", goal), ...pairs]), "");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
