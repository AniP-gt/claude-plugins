#!/usr/bin/env node
// Advisory inspired by lazycodex non-interactive-env; never changes or blocks the command.
import { fileURLToPath } from "node:url";

const GUIDANCE = "[OMO NON-INTERACTIVE COMMAND] This command may wait for an interactive editor, pager, or prompt. Choose an appropriate non-interactive form when possible; preserve the intended Git changes and message. If interaction is necessary, arrange it with the user.";

function isInteractive(command) {
  // Do not guess at shell expressions, substitutions, pipelines or redirections.
  if (/[\n;|&<>`$()]/.test(command)) return false;
  const tokens = command.match(/(?:[^\s'\"]+|'[^']*'|\"[^\"]*\")+/g);
  if (!tokens || tokens.some((token) => (token.match(/'/g) ?? []).length % 2 || (token.match(/\"/g) ?? []).length % 2)) return false;
  if (tokens.some((token) => token === "--help" || token === "-h")) return false;
  if (/^(?:vi|vim|nvim|nano|emacs|less|more|man)$/.test(tokens[0])) return true;
  if (tokens[0] !== "git") return false;
  const args = tokens.slice(1);
  if (args[0] === "--no-pager") args.shift();
  const action = args.shift();
  if (action === "add") return args.some((arg) => arg === "--patch" || /^-[^-]*p/.test(arg));
  if (action === "rebase") return args.some((arg) => arg === "--interactive" || arg === "--continue" || /^-[^-]*i/.test(arg));
  if (action !== "commit") return false;
  return !args.some((arg) => arg === "--no-edit" || arg === "--message" || arg.startsWith("--message=") || arg === "--file" || arg.startsWith("--file=") || /^-[^-]*[mF]/.test(arg));
}

export function run(input) {
  if (input === null || typeof input !== "object" || input.hook_event_name !== "PreToolUse" || input.tool_name !== "Bash") return "";
  const command = input.tool_input?.command;
  if (typeof command !== "string" || !isInteractive(command)) return "";
  return `${JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", additionalContext: GUIDANCE } })}\n`;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let raw = "";
  for await (const chunk of process.stdin) raw += chunk;
  let input;
  try { input = JSON.parse(raw); } catch { input = undefined; }
  process.stdout.write(run(input));
}
