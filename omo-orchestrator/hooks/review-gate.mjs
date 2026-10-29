#!/usr/bin/env node
// Stop hook: when this turn changed files (one or more by default) and nothing reviewed them after the last edit, block the
// stop once and ask Claude for a review of hidden impact (risk map, undefined cases, validation).
// Changed files come from the git snapshot preflight.mjs took at the prompt, so Bash and sub-agent edits
// count; the transcript's Edit/Write calls are the fallback outside git.
// The second stop arrives with stop_hook_active=true and always passes, so the hook cannot loop.
// A background task notification continues the same turn and triggers a fresh stop without that flag, so
// the gate also passes when its own feedback already follows the last edit: it asks once per edit.
// A second check blocks once when this turn ran omo-review but shows no sign of its Codex lane afterwards.
import { readFileSync, realpathSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { filesChangedSince, loadSnapshot } from "./turn-snapshot.mjs";
import { stripInjected } from "./ulw-keyword.mjs";

const MARKER = "[OMO REVIEW GATE]";
const EDIT_TOOLS = new Set(["Edit", "Write", "MultiEdit", "NotebookEdit"]);
const DELEGATE_TOOLS = new Set(["Agent", "Task"]);
// Sub-agents whose edits never appear in this transcript; one call counts as a change to unknown files.
const EDITING_AGENT_PATTERN = /implementer|builder/i;
const REVIEW_SKILL_PATTERN = /review/i;
const REVIEW_AGENT_PATTERN = /review|oracle|security-check/i;
// The handoff ledger and notepads are bookkeeping, not product changes. Review skills write their reports
// under docs/reviews/ after they run; counting those would ask for a review of the review.
const IGNORED_PATH_PATTERN = /(^|\/)(?:\.claude\/omo|docs\/reviews)\//;

export function minFiles(env = process.env) {
  const value = Number.parseInt(env.OMO_REVIEW_GATE_MIN_FILES ?? "", 10);
  return Number.isInteger(value) && value > 0 ? value : 1;
}

// A `!` shell command the user runs lands as <bash-input>/<bash-stdout> user messages. It fires no
// UserPromptSubmit, so the snapshot stays at the last prompt; treating it as a new turn would forget the
// gate's earlier feedback and block again on the same files.
const BASH_MODE_PATTERN = /<(bash-input|bash-stdout|bash-stderr)>[\s\S]*?<\/\1>/g;

// Task notifications, system reminders, and `!` shell commands arrive as user messages but continue the
// same turn.
function isRealUserPrompt(entry) {
  if (entry?.type !== "user" || entry.isMeta === true || entry.isSidechain === true) return false;
  const content = entry.message?.content;
  let text;
  if (typeof content === "string") text = content;
  else if (Array.isArray(content) && !content.some((block) => block?.type === "tool_result")) {
    text = content.map((block) => (block?.type === "text" ? block.text : "")).join("\n");
  } else return false;
  return stripInjected(text).replace(BASH_MODE_PATTERN, " ").trim().length > 0;
}

// Marks where this gate's own feedback landed in the turn; summarizeTurn treats it like a review.
export const GATE_FEEDBACK = "omo-review-gate-feedback";

// Stop feedback may be stored as a meta user message or as a hook_blocking_error attachment.
function isGateFeedback(entry, marker = MARKER) {
  if (entry?.isSidechain === true) return false;
  if (entry?.type === "attachment" && entry.attachment?.type === "hook_blocking_error") {
    return JSON.stringify(entry.attachment.blockingError ?? "").includes(marker);
  }
  if (entry?.type !== "user" || entry.isMeta !== true) return false;
  const content = entry.message?.content;
  return typeof content === "string" && content.includes(marker);
}

// Index of the first entry after the last real user prompt.
function turnStart(entries) {
  for (let i = entries.length - 1; i >= 0; i -= 1) if (isRealUserPrompt(entries[i])) return i + 1;
  return 0;
}

// Returns the tool_use blocks the main thread issued since the last real user prompt, with a
// { name: GATE_FEEDBACK } entry wherever the gate already blocked a stop.
export function currentTurnToolUses(entries) {
  const start = turnStart(entries);
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
  if (shown === null) return false;
  // A session started in docs/ shows reports as reviews/self/x.md, so the last two cwd segments are
  // prefixed. Ancestors above them are left out: a repository under /work/docs/reviews/ is not all reports.
  const context = cwd ? `${basename(dirname(cwd))}/${basename(cwd)}/${shown}` : shown;
  return !IGNORED_PATH_PATTERN.test(context);
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

const MAX_LISTED_FILES = 5;

export function buildReason({ files, delegatedEdit }) {
  const what = files.length > 0 ? `${files.length} ファイルを変更し` : "サブエージェントがファイルを変更し";
  const lines = [`${MARKER} ${what}、最後の編集のあとにレビューしていません。`];
  for (const file of files.slice(0, MAX_LISTED_FILES)) lines.push(`- ${file}`);
  if (files.length > MAX_LISTED_FILES) lines.push(`- ほか ${files.length - MAX_LISTED_FILES} 件`);
  if (delegatedEdit && files.length === 0) lines.push("先にサブエージェントの差分（git diff）を読んでください。");
  lines.push(
    "",
    "終える前に、次のどれか1つを選んでください。",
    "- 誤字か設定値だけの変更なら、そう1行で書いて終える。ドキュメントやコメントの説明は挙動の主張なので軽いレビューの対象。",
    "- 3ファイル以上、公開 API や CLI の挙動、永続化、セキュリティに関わるなら `omo-orchestrator:omo-review` を実行する。",
    "- それ以外は軽いレビュー: 変更した関数などの呼び出し元と隠れた影響範囲、それを守るテストなど。",
    "  空入力・境界値・重複や並行実行・途中失敗・既存データの扱い。実際に実行した確認。",
    "  範囲内の問題は直し、守りのないリスクは最終回答に書き、必要なら利用者に1つだけ質問する。",
  );
  return lines.join("\n");
}

const CODEX_MARKER = "[OMO CODEX GATE]";
const OMO_REVIEW_SKILL_PATTERN = /(^|:)omo-review$/;
// A user-typed `/omo-review` lands as the prompt itself, not as a Skill call.
const OMO_REVIEW_COMMAND_PATTERN = /<command-name>\/?(omo-orchestrator:)?omo-review<\/command-name>/;
const CODEX_COMMAND_PATTERN = /(^|[\s;&|(])(codex\s+exec\b|command\s+-v\s+codex\b)/;
// Status lines a review sub-agent returns: `codex: …` from codex-lane.md and self-review's `Codex 実行: …`.
// `codex: run by caller` is left out: it hands the lane to the caller, which still has to run it.
const CODEX_STATUS_PATTERN = /codex:\s*(OK|NOT_EXECUTED)|Codex 実行\**\s*[:：]\s*\**\s*(OK|NOT_EXECUTED)/i;

// Comment lines mention commands without running them.
function withoutComments(command) {
  return String(command ?? "")
    .split("\n")
    .filter((line) => !line.trimStart().startsWith("#"))
    .join("\n");
}

function textOf(content) {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content.map((block) => (typeof block?.text === "string" ? block.text : "")).join("\n");
}

// True when this turn invoked omo-review and nothing after the last invocation shows its Codex lane: a Bash
// call that ran or probed `codex`, or a Codex status line in a sub-agent's result. Only Agent/Task results
// count, because a Read of codex-lane.md or the skill text carries the same status line as an example.
export function codexLaneMissing(entries) {
  const start = turnStart(entries);
  let pending = start > 0 && OMO_REVIEW_COMMAND_PATTERN.test(textOf(entries[start - 1]?.message?.content));
  const delegateIds = new Set();
  for (const entry of entries.slice(start)) {
    if (isGateFeedback(entry, CODEX_MARKER)) {
      pending = false;
      continue;
    }
    if (entry?.isSidechain === true) continue;
    const content = entry?.message?.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (entry.type === "assistant" && block?.type === "tool_use") {
        const input = block.input ?? {};
        if (block.name === "Skill" && OMO_REVIEW_SKILL_PATTERN.test(String(input.skill ?? ""))) pending = true;
        else if (block.name === "Bash" && CODEX_COMMAND_PATTERN.test(withoutComments(input.command))) pending = false;
        else if (DELEGATE_TOOLS.has(block.name)) delegateIds.add(block.id);
      } else if (entry.type === "user" && block?.type === "tool_result" && delegateIds.has(block.tool_use_id)) {
        if (CODEX_STATUS_PATTERN.test(textOf(block.content))) pending = false;
      }
    }
  }
  return pending;
}

export function buildCodexReason() {
  return [
    `${CODEX_MARKER} このターンで omo-review を実行しましたが、Codex レーンの実行が見当たりません。`,
    "",
    "終える前に、次のどれか1つを選んでください。",
    "- `omo-review` の `references/codex-lane.md` に従って Codex を実行し、`codex:` の状態行を最終報告に書く。",
    "- self-review が Codex を実行済みなら、そのレポートの `Codex 実行` 行を確認して `codex: OK (self-review, <path>)` を書く。",
    "- レビュー自体を実行しなかった（コントローラー内で二重レビューを避けた等）なら、そう1行で書いて終える。",
  ].join("\n");
}

function block(reason) {
  return `${JSON.stringify({ decision: "block", reason })}\n`;
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
  if (typeof input.transcript_path !== "string") return "";
  const entries = loadTranscript(input.transcript_path);
  if (!/^(off|0|false)$/i.test(env.OMO_REVIEW_GATE ?? "")) {
    const reason = reviewReason(entries, input, env, changedFiles);
    if (reason !== null) return block(reason);
  }
  if (!/^(off|0|false)$/i.test(env.OMO_CODEX_GATE ?? "") && codexLaneMissing(entries)) return block(buildCodexReason());
  return "";
}

function reviewReason(entries, input, env, changedFiles) {
  const cwd = typeof input.cwd === "string" ? input.cwd : undefined;
  const turn = summarizeTurn(currentTurnToolUses(entries), cwd);
  if (turn.reviewed) return null;
  const fromGit = changedFiles(input.session_id, env, cwd);
  const files = new Set(turn.files);
  for (const file of fromGit ?? []) if (isReviewable(file, cwd)) files.add(file);
  // With a git snapshot, sub-agent edits are already in the file list; without one, guess from the call.
  const delegatedEdit = fromGit === null && turn.delegatedEdit;
  if (files.size < minFiles(env) && !delegatedEdit) return null;
  const shown = [...files].map((file) => display(file, cwd)).sort();
  return buildReason({ files: shown, delegatedEdit });
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
