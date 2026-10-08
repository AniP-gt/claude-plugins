#!/usr/bin/env node
// Stop hook: when this turn changed several files and nothing reviewed them after the last edit, block the
// stop once and ask Claude for a review of hidden impact (risk map, undefined cases, validation).
// Changed files come from the git snapshot preflight.mjs took at the prompt, so Bash and sub-agent edits
// count; the transcript's Edit/Write calls are the fallback outside git.
// The second stop arrives with stop_hook_active=true and always passes, so the hook cannot loop.
// A background task notification continues the same turn and triggers a fresh stop without that flag, so
// the gate also passes when its own feedback already follows the last edit: it asks once per edit.
import { readFileSync, realpathSync } from "node:fs";
import { isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { filesChangedSince, loadSnapshot } from "./turn-snapshot.mjs";
import { stripInjected } from "./ulw-keyword.mjs";

const MARKER = "[OMO REVIEW GATE]";
const EDIT_TOOLS = new Set(["Edit", "Write", "MultiEdit", "NotebookEdit"]);
const DELEGATE_TOOLS = new Set(["Agent", "Task"]);
// Sub-agents whose edits never appear in this transcript; one call counts as a multi-file change.
const EDITING_AGENT_PATTERN = /implementer|builder/i;
const REVIEW_SKILL_PATTERN = /review/i;
const REVIEW_AGENT_PATTERN = /review|oracle|security-check/i;
// The handoff ledger and notepads are bookkeeping, not product changes.
const IGNORED_PATH_PATTERN = /(^|\/)\.claude\/omo\//;

export function minFiles(env = process.env) {
  const value = Number.parseInt(env.OMO_REVIEW_GATE_MIN_FILES ?? "", 10);
  return Number.isInteger(value) && value > 0 ? value : 2;
}

// Task notifications and system reminders arrive as user messages but continue the same turn.
function isRealUserPrompt(entry) {
  if (entry?.type !== "user" || entry.isMeta === true || entry.isSidechain === true) return false;
  const content = entry.message?.content;
  let text;
  if (typeof content === "string") text = content;
  else if (Array.isArray(content) && !content.some((block) => block?.type === "tool_result")) {
    text = content.map((block) => (block?.type === "text" ? block.text : "")).join("\n");
  } else return false;
  return stripInjected(text).trim().length > 0;
}

// Marks where this gate's own feedback landed in the turn; summarizeTurn treats it like a review.
export const GATE_FEEDBACK = "omo-review-gate-feedback";

function isGateFeedback(entry) {
  if (entry?.type !== "user" || entry.isMeta !== true || entry.isSidechain === true) return false;
  const content = entry.message?.content;
  return typeof content === "string" && content.includes(MARKER);
}

// Returns the tool_use blocks the main thread issued since the last real user prompt, with a
// { name: GATE_FEEDBACK } entry wherever the gate already blocked a stop.
export function currentTurnToolUses(entries) {
  let start = 0;
  for (let i = entries.length - 1; i >= 0; i -= 1) {
    if (isRealUserPrompt(entries[i])) {
      start = i + 1;
      break;
    }
  }
  const uses = [];
  for (const entry of entries.slice(start)) {
    if (isGateFeedback(entry)) {
      uses.push({ name: GATE_FEEDBACK });
      continue;
    }
    if (entry?.type !== "assistant" || entry.isSidechain === true) continue;
    const content = entry.message?.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) if (block?.type === "tool_use") uses.push(block);
  }
  return uses;
}

// Edits seen in the transcript, whether a sub-agent may have edited, and whether a review ran after the
// last edit. A review that an edit follows no longer covers the final state.
export function summarizeTurn(uses, cwd) {
  const files = new Set();
  let delegatedEdit = false;
  let reviewed = false;
  for (const use of uses) {
    const input = use.input ?? {};
    if (EDIT_TOOLS.has(use.name)) {
      const target = input.file_path ?? input.notebook_path;
      if (typeof target !== "string") continue;
      const absolute = cwd && !isAbsolute(target) ? resolve(cwd, target) : target;
      if (!isReviewable(absolute, cwd)) continue;
      files.add(absolute);
      reviewed = false;
    } else if (DELEGATE_TOOLS.has(use.name)) {
      const type = typeof input.subagent_type === "string" ? input.subagent_type : "";
      if (REVIEW_AGENT_PATTERN.test(type)) reviewed = true;
      else if (EDITING_AGENT_PATTERN.test(type)) {
        delegatedEdit = true;
        reviewed = false;
      }
    } else if (use.name === GATE_FEEDBACK) {
      reviewed = true;
    } else if (use.name === "Skill") {
      if (REVIEW_SKILL_PATTERN.test(String(input.skill ?? ""))) reviewed = true;
    }
  }
  return { files: [...files], delegatedEdit, reviewed };
}

// Scratch files outside the working tree and the omo ledger are not part of the change under review.
function isReviewable(absolute, cwd) {
  const shown = inside(absolute, cwd);
  return shown !== null && !IGNORED_PATH_PATTERN.test(shown);
}

// Path relative to cwd, or null when it lies outside. Git reports symlink-resolved paths (/private/tmp
// for /tmp on macOS), so the resolved cwd is tried as well.
function inside(absolute, cwd) {
  if (!cwd) return absolute;
  for (const base of [cwd, resolvedCwd(cwd)]) {
    const shown = relative(base, absolute);
    if (!shown.startsWith("..") && !isAbsolute(shown)) return shown;
  }
  return null;
}

function resolvedCwd(cwd) {
  try {
    return realpathSync(cwd);
  } catch {
    return cwd;
  }
}

function display(absolute, cwd) {
  return (inside(absolute, cwd) ?? absolute).replace(/[\r\n]+/g, " ");
}

export function buildReason({ files, delegatedEdit }) {
  const changed = files.length > 0 ? files.map((file) => `- ${file}`).join("\n") : "- (edited by a sub-agent)";
  const lines = [
    MARKER,
    `This turn changed ${files.length > 0 ? `${files.length} files` : "files through a sub-agent"} and no review ran after the last edit.`,
    changed,
    "",
    "Before you finish, do a light review of what the user did not ask about but will be hit by:",
    "1. Risk map: for each modified existing function, class, config key, or command, search its callers",
    "   (name the search) and note hidden reach: references by string or reflection, queued or scheduled",
    "   work, data the old code already wrote, consumers outside this repository, flags or env vars.",
    "   Mark each found, none, or could not verify, and name the guardrail (test, type, lint, none).",
    "2. Undefined cases: empty input, boundaries, repeated or concurrent runs, partial failure, data that",
    "   already exists. Note which the change handles and which it leaves open.",
    "3. Validation: name the checks you actually ran this session for these files, and what remains unrun.",
    "",
    "Fix anything confirmed and in scope. Rows with impact and no guardrail go in your final answer as",
    "residual risks; product decisions go to the user as one precise question.",
    "When the change touches 3+ files, public or CLI behavior, persistence, or security, run",
    "`omo-orchestrator:omo-review` instead of the light review: it is the single review entry and runs the",
    "`self-review` skill in parallel with its own reviewer.",
    "If the change is only wording, docs, or config values with no new branch, say so in one line and stop.",
  ];
  if (delegatedEdit && files.length === 0) {
    lines.push("", "The edits came from a sub-agent: read its diff (git diff) before reviewing.");
  }
  return lines.join("\n");
}

export function readTranscript(path) {
  try {
    return readFileSync(path, "utf8")
      .split("\n")
      .filter((line) => line.trim().length > 0)
      .map((line) => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter((entry) => entry !== null);
  } catch {
    return [];
  }
}

export function run(input, { env = process.env, loadTranscript = readTranscript, changedFiles = gitChangedFiles } = {}) {
  if (typeof input !== "object" || input === null) return "";
  if (input.hook_event_name !== undefined && input.hook_event_name !== "Stop") return "";
  if (input.stop_hook_active === true) return "";
  if (/^(off|0|false)$/i.test(env.OMO_REVIEW_GATE ?? "")) return "";
  if (typeof input.transcript_path !== "string") return "";
  const cwd = typeof input.cwd === "string" ? input.cwd : undefined;
  const turn = summarizeTurn(currentTurnToolUses(loadTranscript(input.transcript_path)), cwd);
  if (turn.reviewed) return "";
  const fromGit = changedFiles(input.session_id, env, cwd);
  const files = new Set(turn.files);
  for (const file of fromGit ?? []) if (isReviewable(file, cwd)) files.add(file);
  // With a git snapshot, sub-agent edits are already in the file list; without one, guess from the call.
  const delegatedEdit = fromGit === null && turn.delegatedEdit;
  if (files.size < minFiles(env) && !delegatedEdit) return "";
  const shown = [...files].map((file) => display(file, cwd)).sort();
  return `${JSON.stringify({ decision: "block", reason: buildReason({ files: shown, delegatedEdit }) })}\n`;
}

// Absolute paths the turn changed according to the git snapshot, or null when there is no snapshot.
export function gitChangedFiles(sessionId, env = process.env, cwd = undefined) {
  const snapshot = loadSnapshot(sessionId, env, cwd);
  if (snapshot === null) return null;
  const changed = filesChangedSince(snapshot);
  return changed === null ? null : changed.map((path) => join(snapshot.root, path));
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
