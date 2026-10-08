#!/usr/bin/env node
// UserPromptSubmit hook: when a prompt asks for a code change, inject a short pre-flight checklist so that
// affected users, undefined cases, and existing callers are looked at before the first edit, even when the
// user did not ask for it. When it asks for a review, route it to omo-review, the single review entry, which
// a model does not pick on its own for a plain "review this" request.
// ulw prompts are left to ulw-keyword.mjs, which loads a fuller workflow.
// Every prompt also records a git snapshot that review-gate.mjs compares against when Claude stops.
import { fileURLToPath } from "node:url";
import { saveSnapshot, takeSnapshot } from "./turn-snapshot.mjs";
import { detectKeyword, stripCode, stripInjected } from "./ulw-keyword.mjs";

const MARKER = "<omo-preflight>";
const B = "(?<![A-Za-z0-9_])";
const E = "(?![A-Za-z0-9_])";
const CHANGE_PATTERNS = [
  /実装|追加して|修正|直して|直す|変更して|変えて|書き換え|リファクタ|作って|作成して|対応して|移行|削除して|置き換え|改修|組み込/,
  new RegExp(
    `${B}(?:implement|add|fix|refactor|change|update|modify|rewrite|migrate|remove|delete|build|create|rename|support)${E}`,
    "i",
  ),
];

const REVIEW_PATTERNS = [/レビュー|監査|指摘だけ|指摘して/, new RegExp(`${B}(?:review|audit)${E}`, "i")];
// The user picked a specific reviewer or command; leave that choice alone.
const NAMED_REVIEWER_PATTERN = /review-pr|code-review|self-review|omo-review|security-review/i;

export function wantsReview(prompt) {
  const text = stripCode(stripInjected(prompt));
  if (text.trimStart().startsWith("/") || NAMED_REVIEWER_PATTERN.test(text)) return false;
  return REVIEW_PATTERNS.some((pattern) => pattern.test(text));
}

export function wantsChange(prompt) {
  const text = stripCode(stripInjected(prompt));
  return CHANGE_PATTERNS.some((pattern) => pattern.test(text));
}

export function buildContext() {
  return [
    MARKER,
    "This prompt may ask for a code change. If it does not, ignore this block.",
    "Before the first edit, check these briefly and keep the result to a few lines:",
    "1. Who is affected besides the requester: callers of the code, API or CLI users, operators, jobs, other agents.",
    "2. Up to three cases the request leaves undefined or contradicts (empty, boundary, repeat, concurrent,",
    "   partial failure, existing data). Ask the user only when the answer changes a reachable result;",
    "   otherwise pick the reading that matches existing code and say which one you used.",
    "3. Search the callers of every existing function, config key, or command you will modify.",
    "If the change touches 3+ files, public or CLI behavior, persistence, or security, load",
    "`omo-orchestrator:omo-implement`, which sizes the task and escalates to ultrawork when needed.",
    "</omo-preflight>",
  ].join("\n");
}

export function buildReviewContext() {
  return [
    MARKER,
    "This prompt asks for a review. If it does not, ignore this block.",
    "Load `omo-orchestrator:omo-review` with the Skill tool before reading the change. It is the single review",
    "entry: it runs an omo reviewer and the `self-review` skill in parallel and merges their verdicts.",
    "Whatever runs, follow each changed value past the diff: who reads a status, flag, or field the change",
    "now writes (queries, schedulers, jobs, other services), what the old code did on the failure path that",
    "the new code changes, and whether a retried or repeated call is safe.",
    "</omo-preflight>",
  ].join("\n");
}

export function recordTurnStart(input, env = process.env) {
  if (typeof input.session_id !== "string" || typeof input.cwd !== "string") return;
  // A task notification continues the current turn; resnapshotting would hide the turn's earlier edits.
  if (stripInjected(input.prompt).trim().length === 0) return;
  if (/^(off|0|false)$/i.test(env.OMO_REVIEW_GATE ?? "")) return;
  saveSnapshot(input.session_id, takeSnapshot(input.cwd), env);
}

export function run(input, { env = process.env, record = recordTurnStart } = {}) {
  if (typeof input !== "object" || input === null || typeof input.prompt !== "string") return "";
  if (input.hook_event_name !== undefined && input.hook_event_name !== "UserPromptSubmit") return "";
  record(input, env);
  if (/^(off|0|false)$/i.test(env.OMO_PREFLIGHT ?? "")) return "";
  if (detectKeyword(input.prompt) !== null) return "";
  // A review request often says "do not fix" (修正はせず), so it is checked before the change verbs.
  let context;
  if (wantsReview(input.prompt)) context = buildReviewContext();
  else if (wantsChange(input.prompt)) context = buildContext();
  else return "";
  const output = {
    hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: context },
  };
  return `${JSON.stringify(output)}\n`;
}

async function readStdin() {
  let data = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let parsed;
  try {
    parsed = JSON.parse(await readStdin());
  } catch {
    parsed = undefined;
  }
  const output = run(parsed);
  if (output.length > 0) process.stdout.write(output);
}
