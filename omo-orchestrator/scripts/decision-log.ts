#!/usr/bin/env node
// Append one row to an omo decision log (TSV), the format of the omo-guardrails mode `decision-log`.
// Usage: node decision-log.ts <logfile> <phase> <decision> <why> <evidence> <result>
// Writes the header when the file is missing or empty, stamps `ts` in UTC, keeps every cell on one line
// with no control, bidi, or zero-width characters,
// and prefixes a cell that starts with =, +, -, @, or " with a single quote so a spreadsheet never runs it
// as a formula. Ported from pstack show-me-your-work `scripts/log.sh` (MIT, Copyright (c) 2026 Lauren Tan).
import { appendFileSync, mkdirSync, realpathSync, statSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

export const HEADER = "ts\tphase\tdecision\twhy\tevidence\tresult\n";

// Control characters, line/paragraph separators, bidi controls, and zero-width characters become a space,
// so a cell stays on one line and cannot reorder or hide text when the log is shown in a terminal.
const UNSAFE = /[\u0000-\u001f\u007f-\u009f\u061c\u180e\u200b-\u200f\u2028-\u202e\u2060-\u2069\ufeff]/g;

export function cleanCell(value: string): string {
  const flat = value.replace(UNSAFE, " ");
  // A leading double quote is quoted too: a CSV-aware reader would unwrap `"=1+1"` into a formula, or let an
  // unclosed quote swallow the following columns.
  return /^[=+\-@"]/.test(flat) ? `'${flat}` : flat;
}

export function formatRow(ts: string, cells: string[]): string {
  return [ts, ...cells.map(cleanCell)].join("\t") + "\n";
}

function isEmptyOrMissing(file: string): boolean {
  try {
    return statSync(file).size === 0;
  } catch {
    return true;
  }
}

export function appendRow(file: string, cells: string[], now: Date = new Date()): string {
  if (cells.length !== 5) throw new Error("expected 5 cells: phase decision why evidence result");
  mkdirSync(dirname(file), { recursive: true });
  // Append only, never truncate: a wrong stat costs one stray header line, not the rows.
  if (isEmptyOrMissing(file)) appendFileSync(file, HEADER);
  const row = formatRow(now.toISOString().replace(/\.\d{3}Z$/, "Z"), cells);
  appendFileSync(file, row);
  return row;
}

// Compare real paths: a symlinked plugin directory or /tmp -> /private/tmp would otherwise skip the CLI silently.
function isMain(): boolean {
  if (!process.argv[1]) return false;
  try {
    return realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]);
  } catch {
    return false;
  }
}

if (isMain()) {
  const args = process.argv.slice(2);
  if (args.length !== 6) {
    process.stderr.write("usage: decision-log.ts <logfile> <phase> <decision> <why> <evidence> <result>\n");
    process.exit(1);
  }
  appendRow(args[0], args.slice(1));
}
