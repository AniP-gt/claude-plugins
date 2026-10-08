#!/usr/bin/env node
// UserPromptSubmit hook: detects ulw / ultrawork keywords and points Claude at the matching skill.
// Ported from oh-my-openagent packages/omo-codex/plugin/components/ultrawork (codex-hook.ts, skill-pointer.ts)
// and the keyword rules in docs/guide/keywords.md.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const MARKER = "<ultrawork-mode>";

// ASCII word boundaries so that `ulwで` (Japanese right after the keyword) still triggers, while `ulwx` does not.
const B = "(?<![A-Za-z0-9_])";
const E = "(?![A-Za-z0-9_])";
const SEP = "[\\s-]?";

const MASS_PATTERN = new RegExp(`${B}(?:mass${SEP}ulw|ulw${SEP}mass|mulw)${E}`, "i");
const MODE_PATTERNS = [
  ["plan", new RegExp(`${B}ulw${SEP}plan${E}`, "i")],
  ["research", new RegExp(`${B}ulw${SEP}research${E}`, "i")],
  ["loop", new RegExp(`${B}ulw${SEP}loop${E}`, "i")],
  ["execute", new RegExp(`${B}ulw${SEP}execute${E}`, "i")],
];
const ULTRAWORK_PATTERN = new RegExp(`${B}(?:ulw|ultrawork)${E}`, "i");

const MODES = {
  ultrawork: { skill: "omo-ultrawork", label: "ULTRAWORK" },
  plan: { skill: "omo-plan", label: "ULW PLAN" },
  research: { skill: "omo-ultraresearch", label: "ULW RESEARCH" },
  loop: { skill: "omo-ralph-loop", label: "ULW LOOP" },
  execute: { skill: "omo-ulw-execute", label: "ULW EXECUTE" },
  mass: { skill: "omo-mass-ulw", label: "MASS ULW" },
};

export function stripCode(prompt) {
  return prompt.replace(/```[\s\S]*?(?:```|$)/g, " ").replace(/`[^`\n]*`/g, " ");
}

// Background task results and system reminders reach UserPromptSubmit as prompt text, but they are
// not the user's words: a sub-agent report that quotes "ultrawork" must not start the mode.
export function stripInjected(prompt) {
  return prompt
    .replace(/<task-notification>[\s\S]*?(?:<\/task-notification>|$)/g, " ")
    .replace(/<system-reminder>[\s\S]*?(?:<\/system-reminder>|$)/g, " ")
    .replace(/\[SYSTEM NOTIFICATION - NOT USER INPUT\][^\n]*/g, " ");
}

// Text the user pasted from elsewhere arrives wrapped in <pasted_content> tags. It is quoted material,
// not the user's request: a pasted report that says "review" or "ulw" must not route the prompt.
// It still counts as user input for turn tracking, so stripInjected leaves it alone.
// A paste ends only at the closing tag with the same id, so a paste that quotes another closing tag
// stays whole. An opener without its closing tag hides the rest only when it carries the id Claude Code
// adds; a bare "<pasted_content>" the user typed is kept as their text. Typing an id-bearing opener by
// hand, even inside backticks, still hides the rest of the prompt from routing. The scan is linear: each
// closing tag is searched for at most once after it is known to be missing.
const PASTE_OPEN = /<pasted_content( id="[^"\n]{1,64}")?>/g;

export function stripPasted(prompt) {
  let out = "";
  let pos = 0;
  const missing = new Set();
  for (;;) {
    PASTE_OPEN.lastIndex = pos;
    const open = PASTE_OPEN.exec(prompt);
    if (open === null) return out + prompt.slice(pos);
    const id = open[1] ?? "";
    const close = `</pasted_content${id}>`;
    const end = missing.has(close) ? -1 : prompt.indexOf(close, PASTE_OPEN.lastIndex);
    if (end !== -1) {
      out += `${prompt.slice(pos, open.index)} `;
      pos = end + close.length;
      continue;
    }
    missing.add(close);
    if (id !== "") return `${out}${prompt.slice(pos, open.index)} `;
    out += prompt.slice(pos, PASTE_OPEN.lastIndex);
    pos = PASTE_OPEN.lastIndex;
  }
}

// The user's own words: a paste is stripped first because it is the outer container, so an unclosed
// <system-reminder> quoted inside it cannot swallow the paste's closing tag and the request after it.
export function userText(prompt) {
  return stripCode(stripInjected(stripPasted(prompt)));
}

export function detectKeyword(prompt) {
  const text = userText(prompt);
  const mass = MASS_PATTERN.test(text);
  for (const [mode, pattern] of MODE_PATTERNS) {
    if (pattern.test(text)) return { mode, mass };
  }
  if (mass) return { mode: "mass", mass: false };
  if (ULTRAWORK_PATTERN.test(text)) return { mode: "ultrawork", mass: false };
  return null;
}

function skillPath(skill) {
  return join(PLUGIN_ROOT, "skills", skill, "SKILL.md");
}

export function buildContext({ mode, mass }) {
  const { skill, label } = MODES[mode];
  const path = skillPath(skill);
  const lines = [
    MARKER,
    `${label} MODE IS ACTIVE FOR THIS TASK (keyword detected in the user's message).`,
    "",
    "If the user is only talking about the keyword rather than asking for this mode, ignore this block and carry on normally.",
    "",
    "MANDATORY BOOTSTRAP: do these steps, in order, before anything else.",
    "",
    "1. First user-visible line this turn MUST be exactly:",
    "`ULTRAWORK MODE ENABLED!`",
    "",
    "2. Open your reply with a binding `# Goal` block: the user's request as an outcome, the success",
    "criteria as binary observables, the scope bounds, and one line \"I'll stop right away when <observable state>\".",
    "",
    `3. Load the \`omo-orchestrator:${skill}\` skill NOW with the Skill tool, before any other tool call, plan, or edit.`,
  ];
  if (existsSync(path)) {
    lines.push(
      "If the Skill tool is unavailable, Read the whole file instead (keep reading if the result is truncated):",
      "",
      path,
    );
  } else {
    lines.push("If the skill cannot be loaded, tell the user the omo-orchestrator skill is missing and continue with steps 1 and 2 plus evidence-bound execution.");
  }
  lines.push(
    "",
    "Every rule in that skill is binding for this entire task: no summarizing from memory, no skipping.",
  );
  if (mass) {
    const massPath = skillPath(MODES.mass.skill);
    lines.push(
      "",
      `MASS ULW: also load \`omo-orchestrator:${MODES.mass.skill}\` and run this mode as dependency-ordered parallel waves`,
      `of sub-agent tasks as that skill describes${existsSync(massPath) ? ` (file: ${massPath})` : ""}.`,
    );
  }
  lines.push("", "Do not start the requested work until the bootstrap is complete.", "</ultrawork-mode>");
  return lines.join("\n");
}

export function run(input) {
  if (typeof input !== "object" || input === null || typeof input.prompt !== "string") return "";
  if (input.hook_event_name !== undefined && input.hook_event_name !== "UserPromptSubmit") return "";
  const detected = detectKeyword(input.prompt);
  if (detected === null) return "";
  const output = {
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: buildContext(detected),
    },
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
  const raw = await readStdin();
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    parsed = undefined;
  }
  const output = run(parsed);
  if (output.length > 0) process.stdout.write(output);
}
