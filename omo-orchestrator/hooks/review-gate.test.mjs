// Run: node --test omo-orchestrator/hooks/review-gate.test.mjs
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, realpathSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { codexRunInFlight, minFiles, run } from "./review-gate.mjs";

const cwd = "/repo";
const prompt = { type: "user", message: { content: "直して" } };
const edit = (file) => ({
  type: "assistant",
  message: { content: [{ type: "tool_use", name: "Edit", input: { file_path: `${cwd}/${file}` } }] },
});
const review = {
  type: "assistant",
  message: { content: [{ type: "tool_use", name: "Agent", input: { subagent_type: "omo-orchestrator:omo-reviewer" } }] },
};
// Real task notifications carry no isMeta flag; they stop counting as prompts once stripInjected removes them.
const notification = { type: "user", origin: { kind: "task-notification" }, message: { content: "<task-notification>\n<status>completed</status>\n</task-notification>" } };
const reply = { type: "assistant", message: { content: [{ type: "text", text: "ok" }] } };

function gate(entries, changed = null, stopHookActive = false, reports = {}) {
  const feedback = run(
    { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd, stop_hook_active: stopHookActive },
    { env: {}, loadTranscript: () => entries, changedFiles: () => changed, readReport: (path) => reports[path] ?? "" },
  );
  return feedback.length === 0 ? null : { type: "user", isMeta: true, message: { content: `Stop hook feedback:\n${JSON.parse(feedback).reason}` } };
}

test("blocks once when several files changed without a review", () => {
  assert.notEqual(gate([prompt, edit("a.js"), edit("b.js")]), null);
});

test("passes when a review ran after the last edit", () => {
  assert.equal(gate([prompt, edit("a.js"), edit("b.js"), review]), null);
});

test("a background notification after the gate's feedback does not block the same edits again", () => {
  const entries = [prompt, edit("a.js"), edit("b.js")];
  const feedback = gate(entries);
  assert.notEqual(feedback, null);
  assert.equal(gate([...entries, feedback, reply, notification, reply]), null);
});

test("an edit after the gate's feedback re-arms the gate", () => {
  const entries = [prompt, edit("a.js"), edit("b.js")];
  const feedback = gate(entries);
  assert.notEqual(gate([...entries, feedback, reply, edit("c.js")]), null);
});

test("feedback from an earlier turn does not cover a new turn", () => {
  const earlier = [prompt, edit("a.js"), edit("b.js")];
  const feedback = gate(earlier);
  assert.notEqual(gate([...earlier, feedback, reply, prompt, edit("c.js"), edit("d.js")]), null);
});

test("a `!` shell command after the gate's feedback does not start a new turn", () => {
  const entries = [prompt, edit("a.js"), edit("b.js")];
  // The files come from the git snapshot, which a `!` command does not refresh.
  const fromGit = [`${cwd}/a.js`, `${cwd}/b.js`];
  const feedback = gate(entries, fromGit);
  assert.notEqual(feedback, null);
  const bashInput = { type: "user", message: { content: "<bash-input>git push</bash-input>" } };
  const bashOutput = { type: "user", message: { content: "<bash-stdout>main -> main</bash-stdout><bash-stderr></bash-stderr>" } };
  assert.equal(gate([...entries, feedback, reply, bashInput, bashOutput, reply], fromGit), null);
});

test("a prompt that mixes the user's words with a shell block still starts a new turn", () => {
  const entries = [prompt, edit("a.js"), edit("b.js")];
  const feedback = gate(entries);
  const mixed = { type: "user", message: { content: "これも直して <bash-input>ls</bash-input>" } };
  assert.notEqual(gate([...entries, feedback, reply, mixed, edit("c.js"), edit("d.js")]), null);
});

const tool = (name, input, id = `${name}-1`) => ({ type: "assistant", message: { content: [{ type: "tool_use", id, name, input }] } });
const result = (id, text) => ({ type: "user", message: { content: [{ type: "tool_result", tool_use_id: id, content: [{ type: "text", text }] }] } });
const omoReview = tool("Skill", { skill: "omo-orchestrator:omo-review" });
const isCodexBlock = (feedback) => feedback !== null && feedback.message.content.includes("[OMO CODEX GATE]");

test("blocks when omo-review ran with no Codex lane afterwards", () => {
  assert.ok(isCodexBlock(gate([prompt, omoReview, reply])));
});

const asyncLaunch = (id, agentId) =>
  result(id, `Async agent launched successfully.\nagentId: ${agentId} (internal ID)\nThe agent is working in the background.`);
const taskDone = (taskId, text) => ({
  type: "user",
  message: { content: `<task-notification>\n<task-id>${taskId}</task-id>\n<status>completed</status>\n<result>${text}</result>\n</task-notification>` },
});
const bgReviewer = tool("Agent", { subagent_type: "omo-orchestrator:omo-reviewer", run_in_background: true }, "agent-bg");

test("waits while a background sub-agent launched after omo-review is still running", () => {
  assert.equal(gate([prompt, omoReview, bgReviewer, asyncLaunch("agent-bg", "a1"), reply]), null);
});

test("blocks once the background sub-agent finished without a Codex status line", () => {
  const entries = [prompt, omoReview, bgReviewer, asyncLaunch("agent-bg", "a1"), reply, taskDone("a1", "ISSUES_FOUND: NO"), reply];
  assert.ok(isCodexBlock(gate(entries)));
});

test("a Codex status line in the background sub-agent's notification is evidence", () => {
  const entries = [prompt, omoReview, bgReviewer, asyncLaunch("agent-bg", "a1"), reply, taskDone("a1", "Codex 実行: OK"), reply];
  assert.equal(gate(entries), null);
});

test("a notification for another task does not end the wait", () => {
  const entries = [prompt, omoReview, bgReviewer, asyncLaunch("agent-bg", "a1"), reply, taskDone("zz", "done"), reply];
  assert.equal(gate(entries), null);
});

test("waits while a background Bash command launched after omo-review is still running", () => {
  const bg = tool("Bash", { command: "orca terminal wait", run_in_background: true }, "bash-bg");
  const launched = result("bash-bg", "Command running in background with ID: b1. Output is being written to: /tmp/b1.output");
  assert.equal(gate([prompt, omoReview, bg, launched, reply]), null);
  assert.ok(isCodexBlock(gate([prompt, omoReview, bg, launched, reply, taskDone("b1", "exit 0"), reply])));
});

test("a sub-agent report quoting a launch message does not hold the check", () => {
  const quoted = result("agent-bg", "ISSUES_FOUND: NO\nログ: Command running in background with ID: b1.");
  assert.ok(isCodexBlock(gate([prompt, omoReview, bgReviewer, quoted, reply])));
});

test("a background task launched before omo-review does not hold the check", () => {
  assert.ok(isCodexBlock(gate([prompt, bgReviewer, asyncLaunch("agent-bg", "a1"), omoReview, reply])));
});

test("passes when a Bash call ran codex exec after omo-review", () => {
  const codex = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/x.md" "review" < /tmp/x.diff' });
  assert.equal(gate([prompt, omoReview, codex, reply]), null);
});

test("passes when the lane ran codex with --dangerously-bypass-hook-trust before exec", () => {
  const codex = tool("Bash", { command: 'codex --dangerously-bypass-hook-trust exec --sandbox read-only -o "/tmp/x.md" "review" < /tmp/x.diff' });
  assert.equal(gate([prompt, omoReview, codex, reply]), null);
});

test("a consult with --dangerously-bypass-hook-trust is still not the review lane", () => {
  const consult = tool("Bash", { command: 'codex --dangerously-bypass-hook-trust exec --sandbox read-only -o "/tmp/omo-consult/codex/1.out.md" "debug" < "/tmp/omo-consult/codex/1.brief.md"' });
  assert.ok(isCodexBlock(gate([prompt, omoReview, consult, reply])));
});

test("passes when the codex probe found no CLI, since the lane then records NOT_EXECUTED", () => {
  assert.equal(gate([prompt, omoReview, tool("Bash", { command: "command -v codex >/dev/null 2>&1 && codex --version" }), reply]), null);
});

test("passes when the sub-agent answers in prose and the report file it names carries the status line", () => {
  const agent = tool("Agent", { subagent_type: "omo-orchestrator:omo-external-reviewer" }, "agent-1");
  const answer = result("agent-1", "Codex は実行されました。REPORT: docs/reviews/self/x_self_review_1.md");
  const reports = { "docs/reviews/self/x_self_review_1.md": "## 判定: Approve\n- **Codex 実行**: OK" };
  assert.equal(gate([prompt, omoReview, agent, answer, reply], null, false, reports), null);
  assert.equal(gate([prompt, omoReview, agent, answer, reply], null, false, { "docs/reviews/self/x_self_review_1.md": "CODEX_EXECUTION: EXECUTED" }), null);
});

test("blocks when the named report file has no Codex status line or cannot be read", () => {
  const agent = tool("Agent", { subagent_type: "omo-orchestrator:omo-external-reviewer" }, "agent-1");
  const answer = result("agent-1", "レビュー完了。REPORT: docs/reviews/self/x_self_review_1.md");
  assert.ok(isCodexBlock(gate([prompt, omoReview, agent, answer, reply], null, false, { "docs/reviews/self/x_self_review_1.md": "## 判定: Approve" })));
  assert.ok(isCodexBlock(gate([prompt, omoReview, agent, answer, reply])));
});

test("passes when a review sub-agent returned a Codex status line", () => {
  const agent = tool("Agent", { subagent_type: "omo-orchestrator:omo-external-reviewer" }, "agent-1");
  assert.equal(gate([prompt, omoReview, agent, result("agent-1", "VERDICT: Approve\n- **Codex 実行**: OK"), reply]), null);
});

test("`codex: run by caller` from a sub-agent is not evidence", () => {
  const agent = tool("Agent", { subagent_type: "omo-orchestrator:omo-reviewer" }, "agent-1");
  assert.ok(isCodexBlock(gate([prompt, omoReview, agent, result("agent-1", "codex: run by caller"), reply])));
});

test("a codex command in a comment line is not evidence", () => {
  assert.ok(isCodexBlock(gate([prompt, omoReview, tool("Bash", { command: "# codex exec review\nprintf done" }), reply])));
});

test("a status line in a Read result is not evidence", () => {
  const read = tool("Read", { file_path: `${cwd}/codex-lane.md` }, "read-1");
  assert.ok(isCodexBlock(gate([prompt, omoReview, read, result("read-1", "codex: OK (direct)"), reply])));
});

test("a consult run (omo-consult scratch dir) is not the review lane", () => {
  const consult = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/omo-consult/codex/1.out.md" "debug" < "/tmp/omo-consult/codex/1.brief.md"' });
  assert.ok(isCodexBlock(gate([prompt, omoReview, consult, reply])));
});

test("an adversarial run (.adv. files) is not the review lane", () => {
  const adv = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/omo-review/codex/1.adv.out.md" "adv" < "/tmp/omo-review/codex/1.diff"' });
  assert.ok(isCodexBlock(gate([prompt, omoReview, adv, reply])));
});

test("a consult preflight (codex --version) followed by a consult run is not the review lane", () => {
  const preflight = tool("Bash", { command: "codex --version" });
  const consult = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/omo-consult/codex/1.out.md" "debug" < "/tmp/omo-consult/codex/1.brief.md"' });
  assert.ok(isCodexBlock(gate([prompt, omoReview, preflight, consult, reply])));
});

test("a consult preflight that finds no codex is not the review lane", () => {
  assert.ok(isCodexBlock(gate([prompt, omoReview, tool("Bash", { command: "codex --version" }), reply])));
});

test("an adversarial run after a lane status line keeps the gate passed", () => {
  const agent = tool("Agent", { prompt: "self-review" }, "agent-1");
  const adv = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/omo-review/codex/1.adv.out.md" "adv" < "/tmp/omo-review/codex/1.diff"' });
  assert.equal(gate([prompt, omoReview, agent, result("agent-1", "codex: OK (self-review, r.md)"), adv, reply]), null);
});

test("a lane run after a probe and a consult still passes", () => {
  const probe = tool("Bash", { command: "command -v codex >/dev/null 2>&1 && codex --version" });
  const consult = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/omo-consult/codex/1.out.md" "debug" < "/tmp/omo-consult/codex/1.brief.md"' });
  const lane = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/omo-review/codex/1.out.md" "review" < "/tmp/omo-review/codex/1.diff"' });
  assert.equal(gate([prompt, omoReview, probe, consult, lane, reply]), null);
});

test("a codex run before omo-review does not cover it", () => {
  assert.ok(isCodexBlock(gate([prompt, tool("Bash", { command: "codex exec x" }), omoReview, reply])));
});

test("a user-typed /omo-review command counts as an omo-review call", () => {
  const command = { type: "user", message: { content: "<command-name>/omo-orchestrator:omo-review</command-name>" } };
  assert.ok(isCodexBlock(gate([command, reply])));
});

test("the follow-up stop with stop_hook_active always passes", () => {
  assert.equal(gate([prompt, omoReview, reply], null, true), null);
});

test("a background notification after the Codex feedback does not ask again", () => {
  const entries = [prompt, omoReview, reply];
  const feedback = gate(entries);
  assert.ok(isCodexBlock(feedback));
  assert.equal(gate([...entries, feedback, reply, notification, reply]), null);
});

test("Codex feedback stored as a hook_blocking_error attachment also counts", () => {
  const attachment = {
    type: "attachment",
    attachment: { type: "hook_blocking_error", hookEvent: "Stop", blockingError: { blockingError: "[OMO CODEX GATE] ..." } },
  };
  assert.equal(gate([prompt, omoReview, reply, attachment, reply, notification, reply]), null);
});

test("an omo-review call after the Codex feedback re-arms the check", () => {
  const entries = [prompt, omoReview, reply];
  const feedback = gate(entries);
  assert.ok(isCodexBlock(gate([...entries, feedback, reply, tool("Skill", { skill: "omo-orchestrator:omo-review" }, "Skill-2"), reply])));
});

test("OMO_CODEX_GATE=off disables the Codex check", () => {
  const output = run(
    { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd },
    { env: { OMO_CODEX_GATE: "off" }, loadTranscript: () => [prompt, omoReview, reply], changedFiles: () => null },
  );
  assert.equal(output, "");
});

test("a one-file change triggers the gate by default; the setting still raises the threshold", () => {
  assert.equal(minFiles({}), 1);
  assert.equal(minFiles({ OMO_REVIEW_GATE_MIN_FILES: "2" }), 2);
  assert.equal(minFiles({ OMO_REVIEW_GATE_MIN_FILES: "0" }), 1);
});

test("a one-file change blocks by default", () => {
  assert.notEqual(gate([prompt, edit("a.js")]), null);
});

test("a review report written after a review skill does not re-arm the gate", () => {
  const reviewSkill = { type: "assistant", message: { content: [{ type: "tool_use", name: "Skill", input: { skill: "self-review" } }] } };
  const report = { type: "assistant", message: { content: [{ type: "tool_use", name: "Write", input: { file_path: `${cwd}/docs/reviews/self/x.md` } }] } };
  assert.equal(gate([prompt, reviewSkill, report], [`${cwd}/docs/reviews/self/x.md`]), null);
});

test("the gate's reason does not offer a docs-only exit", () => {
  const feedback = gate([prompt, edit("README.md")]);
  assert.doesNotMatch(feedback.message.content, /文言・ドキュメント・設定値だけ/);
  assert.match(feedback.message.content, /ドキュメントやコメントの説明は挙動の主張/);
});

function gateAt(dir, entries, changed) {
  return run(
    { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd: dir },
    { env: {}, loadTranscript: () => entries, changedFiles: () => changed },
  );
}

test("a review report alone does not block, whatever directory the session started in", () => {
  const report = [`${cwd}/docs/reviews/self/x.md`];
  assert.equal(gateAt(cwd, [prompt], report), "");
  assert.equal(gateAt(`${cwd}/docs`, [prompt], report), "");
  assert.equal(gateAt(`${cwd}/docs/reviews`, [prompt], report), "");
});

test("a review report next to a real change still blocks, and lists only the real change", () => {
  const out = gateAt(`${cwd}/docs`, [prompt], [`${cwd}/docs/reviews/self/x.md`, `${cwd}/docs/guide.md`]);
  assert.notEqual(out, "");
  const reason = JSON.parse(out).reason;
  assert.match(reason, /1 ファイル/);
  assert.doesNotMatch(reason, /reviews\/self/);
});

test("a repository that lives under a docs/reviews directory still gates its own changes", () => {
  const root = "/work/docs/reviews/project";
  assert.notEqual(gateAt(root, [prompt], [`${root}/src/main.js`]), "");
  assert.equal(gateAt(root, [prompt], [`${root}/docs/reviews/self/x.md`]), "");
});

// A Claude controller writes <git root>/.claude/omo/codex/IN_FLIGHT while a Codex run is in flight in another tab.
const HOUR_MS = 60 * 60 * 1000;
const repos = [];
after(() => {
  for (const dir of repos) rmSync(dir, { recursive: true, force: true });
});

function repoWithMarker(ageHours) {
  const dir = realpathSync(mkdtempSync(join(tmpdir(), "review-gate-")));
  repos.push(dir);
  execFileSync("git", ["init", "-q"], { cwd: dir });
  if (ageHours !== null) {
    const marker = join(dir, ".claude/omo/codex/IN_FLIGHT");
    mkdirSync(join(dir, ".claude/omo/codex"), { recursive: true });
    writeFileSync(marker, "");
    const then = new Date(Date.now() - ageHours * HOUR_MS);
    utimesSync(marker, then, then);
  }
  return dir;
}

function gateInRepo(dir, entries) {
  const edited = { type: "assistant", message: { content: [{ type: "tool_use", name: "Edit", input: { file_path: `${dir}/a.js` } }] } };
  return run(
    { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd: dir },
    { env: {}, loadTranscript: () => [prompt, edited, ...entries], changedFiles: () => [`${dir}/a.js`] },
  );
}

test("a fresh in-flight Codex marker keeps the gate from asking for a review of half-done edits", () => {
  assert.equal(gateInRepo(repoWithMarker(1), [reply]), "");
});

test("the marker is found from a subdirectory of the repository", () => {
  const dir = repoWithMarker(1);
  mkdirSync(join(dir, "src"));
  const input = { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd: join(dir, "src") };
  const deps = { env: {}, loadTranscript: () => [prompt, reply], changedFiles: () => [`${dir}/src/a.js`] };
  assert.equal(run(input, deps), "");
  rmSync(join(dir, ".claude"), { recursive: true });
  assert.notEqual(run(input, deps), "");
});

test("without the marker the gate blocks as before", () => {
  assert.notEqual(gateInRepo(repoWithMarker(null), [reply]), "");
});

test("a marker older than 24 hours is ignored", () => {
  assert.notEqual(gateInRepo(repoWithMarker(25), [reply]), "");
  assert.equal(gateInRepo(repoWithMarker(23), [reply]), "");
});

test("a marker with a future mtime is ignored", () => {
  assert.notEqual(gateInRepo(repoWithMarker(-2), [reply]), "");
});

test("a directory named IN_FLIGHT is not a marker", () => {
  const dir = repoWithMarker(null);
  mkdirSync(join(dir, ".claude/omo/codex/IN_FLIGHT"), { recursive: true });
  assert.notEqual(gateInRepo(dir, [reply]), "");
});

test("the marker does not hide a missing Codex lane after omo-review", () => {
  const out = gateInRepo(repoWithMarker(1), [omoReview, reply]);
  assert.notEqual(out, "");
  assert.match(JSON.parse(out).reason, /\[OMO CODEX GATE\]/);
});

test("a marker outside a git repository is not looked for", () => {
  const dir = realpathSync(mkdtempSync(join(tmpdir(), "review-gate-nogit-")));
  repos.push(dir);
  mkdirSync(join(dir, ".claude/omo/codex"), { recursive: true });
  writeFileSync(join(dir, ".claude/omo/codex/IN_FLIGHT"), "");
  assert.equal(codexRunInFlight(dir), false);
  assert.notEqual(gateAt(dir, [prompt], [`${dir}/a.js`]), "");
});

test("an unknown cwd does not fall back to the hook process's own directory", () => {
  const dir = repoWithMarker(1);
  const original = process.cwd();
  process.chdir(dir);
  try {
    assert.equal(codexRunInFlight(dir), true);
    assert.equal(codexRunInFlight(undefined), false);
  } finally {
    process.chdir(original);
  }
});
