#!/usr/bin/env node
// Stop hook: require evidence for active goals written by this session's main thread.
// Check format only; allow current-turn background waits, repeated stops, and unreadable input.
// OMO_GOAL_GATE=off|0|false disables it; the per-file block cap defaults to five.
import { openSync, readSync, closeSync, fstatSync, constants, realpathSync, lstatSync } from "node:fs";
import { resolve, dirname, basename, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  readTranscript,
  codexRunInFlight,
  GOAL_MARKER,
  backgroundPending,
  isGateFeedback,
} from "./review-gate.ts";
import type { StopInput, TranscriptEntry } from "./review-gate.ts";

export interface ParsedGoal {
  status: string | undefined;
  open: string[];
}

export interface GoalGateDeps {
  env?: NodeJS.ProcessEnv;
  loadTranscript?: (path: string) => TranscriptEntry[];
  readGoal?: (path: string) => string | null;
  codexInFlight?: (cwd: string | undefined) => boolean;
}

const MARKER = GOAL_MARKER;
const LIMIT = 64 * 1024;

export function readGoalFile(path: string): string | null {
  let fd: number | undefined;
  try {
    // Nonblocking open lets fstat reject a FIFO without waiting for a writer.
    fd = openSync(path, constants.O_RDONLY | constants.O_NONBLOCK | constants.O_NOFOLLOW);
    if (!fstatSync(fd).isFile()) return null;
    const buffer = Buffer.alloc(LIMIT);
    const size = readSync(fd, buffer, 0, LIMIT, 0);
    return buffer.toString("utf8", 0, size);
  } catch {
    return null;
  } finally {
    if (fd !== undefined) closeSync(fd);
  }
}

function hasEvidence(line: string): boolean {
  // Ignore labels inside code, but preserve code-formatted values after an outside label.
  const labelsOutsideCode = line.replace(/(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)/g,
    (span: string) => span.replace(/evidence:/gi, "         "));
  return /(?<![\w-])evidence:\s*\S/i.test(labelsOutsideCode);
}

export function parseGoal(text: string): ParsedGoal {
  const status = /^Status:\s*(\S+)/im.exec(text)?.[1].replace(/[*_`]/g, "").toLowerCase();
  const criteria = [...text.matchAll(/^\s*-\s*\[( |x|X)\]\s+(.*)$/gm)];
  const open = criteria
    .filter((match) => match[1] === " " || !hasEvidence(match[2]))
    .map((match) => match[0].trim());
  if (criteria.length === 0) open.push("no criteria");
  return { status, open };
}

export function normalizeGoalPath(resolvedPath: string): string {
  // Preserve the leaf so O_NOFOLLOW still rejects a symlink swapped in after lstat.
  try { return join(realpathSync(dirname(resolvedPath)), basename(resolvedPath)); }
  catch { return resolvedPath; }
}

function goalPathsWritten(entries: TranscriptEntry[], cwd: string): string[] {
  const succeeded = new Set<string>();
  for (const entry of entries) {
    if (entry?.type !== "user" || entry.isSidechain === true || !Array.isArray(entry.message?.content)) continue;
    for (const block of entry.message.content) {
      if (block?.type === "tool_result" && typeof block.tool_use_id === "string" && block.is_error !== true) {
        succeeded.add(block.tool_use_id);
      }
    }
  }
  const paths = new Set<string>();
  for (const entry of entries) {
    if (entry?.type !== "assistant" || entry.isSidechain === true || !Array.isArray(entry.message?.content)) continue;
    for (const block of entry.message.content) {
      if (block?.type !== "tool_use" || typeof block.name !== "string" || !["Write", "Edit", "MultiEdit"].includes(block.name)) continue;
      const filePath = block.input?.file_path;
      if (block.id === undefined || !succeeded.has(block.id) || typeof filePath !== "string") continue;
      let path = resolve(cwd, filePath);
      if (/[\r\n]/.test(path) || !/(^|\/)\.claude\/omo\/goal\/[^/]+\.md$/.test(path)) continue;
      try { if (lstatSync(path).isSymbolicLink()) continue; } catch { /* Missing paths keep the current behavior. */ }
      path = normalizeGoalPath(path);
      if (!/[\r\n]/.test(path)) paths.add(path);
    }
  }
  return [...paths];
}

function escapeMarkers(text: string): string {
  return text.replaceAll("[OMO ", "［OMO ");
}

function feedbackCount(entries: TranscriptEntry[], path: string): number {
  let attachments = 0;
  let metas = 0;
  for (const entry of entries) {
    if (!isGateFeedback(entry, MARKER)) continue;
    const error = entry.attachment?.blockingError;
    const text = entry.type === "attachment"
      ? (typeof error === "string" ? error : error?.blockingError)
      : entry.message?.content;
    if (typeof text !== "string" || !text.split(/\r?\n/).includes(escapeMarkers(path))) continue;
    if (entry.type === "attachment") attachments += 1;
    else metas += 1;
  }
  // One Stop block can be recorded in both shapes; count the larger stream.
  return Math.max(attachments, metas);
}

function buildReason(goals: { path: string; open: string[] }[]): string {
  const files = goals.map(({ path, open }) => [
    escapeMarkers(path),
    ...open.slice(0, 10).map((line) => escapeMarkers(line.replace(/[\r\n]/g, "").trim())),
    ...(open.length > 10 ? [`ほか ${open.length - 10} 件`] : []),
  ].join("\n"));
  return [
    `${MARKER} 未達または証拠のない成功条件が残っています。`,
    files.join("\n\n"),
    "",
    "- 未達の条件があるなら作業を続ける。",
    "- 条件を満たしたら、その行を `- [x] … — evidence: <実行したコマンドと結果、またはファイルパス>` に書き換える。",
    "- ユーザーの回答待ちや外部要因で進めないなら `Status: blocked`、中止なら `Status: abandoned`、最終ゲートが APPROVE なら `Status: done` に書き換え、理由を1行書いて終える。",
  ].join("\n");
}

export function run(
  input: unknown,
  {
    env = process.env,
    loadTranscript = readTranscript,
    readGoal = readGoalFile,
    codexInFlight = codexRunInFlight,
  }: GoalGateDeps = {},
): string {
  try {
    if (input === null || typeof input !== "object") return "";
    const stop: StopInput = input;
    if (stop.hook_event_name !== undefined && stop.hook_event_name !== "Stop") return "";
    if (stop.stop_hook_active === true || typeof stop.transcript_path !== "string") return "";
    if (/^(off|0|false)$/i.test(env.OMO_GOAL_GATE ?? "")) return "";
    const cwd = typeof stop.cwd === "string" ? stop.cwd : process.cwd();
    const entries = loadTranscript(stop.transcript_path);
    const parsedMax = Number.parseInt(env.OMO_GOAL_GATE_MAX_BLOCKS ?? "", 10);
    const max = Number.isInteger(parsedMax) && parsedMax > 0 ? parsedMax : 5;
    const goals: { path: string; open: string[] }[] = [];
    for (const path of goalPathsWritten(entries, cwd)) {
      const text = readGoal(path);
      if (typeof text !== "string") continue;
      const goal = parseGoal(text);
      if (goal.status !== "active" || goal.open.length === 0) continue;
      if (feedbackCount(entries, path) < max) goals.push({ path, open: goal.open });
    }
    if (goals.length === 0 || backgroundPending(entries) || codexInFlight(cwd)) return "";
    return `${JSON.stringify({ decision: "block", reason: buildReason(goals) })}\n`;
  } catch {
    return "";
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  try {
    let data = "";
    process.stdin.setEncoding("utf8");
    for await (const chunk of process.stdin) data += chunk;
    const output = run(JSON.parse(data));
    if (output) process.stdout.write(output);
  } catch { /* Invalid input is silent and fail-open. */ }
}
