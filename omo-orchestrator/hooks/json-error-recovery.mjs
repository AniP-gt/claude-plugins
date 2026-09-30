#!/usr/bin/env node
// PostToolUse hook: when a tool call failed because its JSON arguments were malformed, tell Claude to fix
// the syntax and retry instead of repeating the same call. Ported from the OMO json-error-recovery idea.
import { fileURLToPath } from "node:url";

const MARKER = "[JSON PARSE ERROR - IMMEDIATE ACTION REQUIRED]";
const SKIP_TOOLS = new Set(["bash", "read", "glob", "grep", "webfetch", "websearch", "web_search"]);
const ERROR_PATTERN =
  /json parse error|failed to parse json|invalid json|malformed json|unexpected end of json input|SyntaxError:.*(?:unexpected token|in JSON)|InputValidationError/i;
const MAX_SCAN_CHARS = 20_000;

const GUIDANCE = `${MARKER}

The tool call failed because its arguments were not valid JSON or did not match the tool schema.

1. Read the error above: what was expected versus what you sent.
2. Fix the arguments (missing braces, unescaped quotes, trailing commas, wrong types, missing required fields).
3. Retry once with corrected arguments.

Do not repeat the exact same call.`;

function responseText(toolResponse) {
  if (typeof toolResponse === "string") return toolResponse;
  if (toolResponse === null || toolResponse === undefined) return "";
  try {
    return JSON.stringify(toolResponse);
  } catch {
    return "";
  }
}

export function run(input) {
  if (typeof input !== "object" || input === null) return "";
  const event = input.hook_event_name ?? "PostToolUse";
  if (event !== "PostToolUse" && event !== "PostToolUseFailure") return "";
  const toolName = typeof input.tool_name === "string" ? input.tool_name.toLowerCase() : "";
  if (SKIP_TOOLS.has(toolName)) return "";
  const text = `${responseText(input.tool_response)}\n${responseText(input.error)}`.slice(0, MAX_SCAN_CHARS).trim();
  if (text.length === 0 || text.includes(MARKER) || !ERROR_PATTERN.test(text)) return "";
  const output = {
    hookSpecificOutput: { hookEventName: event, additionalContext: GUIDANCE },
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
