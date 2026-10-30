// Run: node --test omo-orchestrator/hooks/review-gate.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import { minFiles, run } from "./review-gate.mjs";

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

function gate(entries, changed = null, stopHookActive = false) {
  const feedback = run(
    { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd, stop_hook_active: stopHookActive },
    { env: {}, loadTranscript: () => entries, changedFiles: () => changed },
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

test("passes when a Bash call ran codex exec after omo-review", () => {
  const codex = tool("Bash", { command: 'codex exec --sandbox read-only -o "/tmp/x.md" "review" < /tmp/x.diff' });
  assert.equal(gate([prompt, omoReview, codex, reply]), null);
});

test("passes when the codex probe found no CLI, since the lane then records NOT_EXECUTED", () => {
  assert.equal(gate([prompt, omoReview, tool("Bash", { command: "command -v codex >/dev/null 2>&1 && codex --version" }), reply]), null);
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
