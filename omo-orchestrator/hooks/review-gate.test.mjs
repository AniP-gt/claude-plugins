// Run: node --test omo-orchestrator/hooks/review-gate.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import { run } from "./review-gate.mjs";

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

function gate(entries) {
  const feedback = run(
    { hook_event_name: "Stop", transcript_path: "t.jsonl", cwd },
    { env: {}, loadTranscript: () => entries, changedFiles: () => null },
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
