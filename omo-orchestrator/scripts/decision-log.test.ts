// Run: node --test omo-orchestrator/scripts/decision-log.test.ts
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";
import { HEADER, appendRow, cleanCell } from "./decision-log.ts";

const dir = mkdtempSync(path.join(os.tmpdir(), "decision-log-"));
after(() => rmSync(dir, { recursive: true, force: true }));

test("cleanCell flattens tabs and newlines and neutralizes formula prefixes", () => {
  assert.equal(cleanCell("a\tb\nc\rd"), "a b c d");
  for (const v of ["=SUM(A1)", "+1", "-x", "@cmd"]) assert.equal(cleanCell(v), `'${v}`);
  assert.equal(cleanCell("commit 3a9f1c2"), "commit 3a9f1c2");
});

test("cleanCell quotes a leading double quote so a CSV-aware reader cannot unwrap a formula or swallow columns", () => {
  assert.equal(cleanCell('"=1+1"'), `'"=1+1"`);
  assert.equal(cleanCell('"unclosed'), `'"unclosed`);
  assert.equal(cleanCell('say "hi"'), 'say "hi"');
});

test("cleanCell replaces escape, vertical tab, line separator, bidi, and zero-width characters", () => {
  assert.equal(cleanCell("a\u001b[31mb\u000bc\u2028d\u202ee\u200bf\u2066g"), "a [31mb c d e f g");
  assert.equal(cleanCell("a⁠b⁤c؜d᠎e"), "a b c d e");
  assert.equal(cleanCell("日本語 ok"), "日本語 ok");
});

test("appendRow writes the header once into a new nested file and appends rows", () => {
  const file = path.join(dir, "nested", "task.tsv");
  appendRow(file, ["frame", "counted the work", "size first", "commit abc", "open"], new Date("2026-11-23T01:02:03.456Z"));
  appendRow(file, ["fix", "a\tb", "=bad", "x", "tests green"], new Date("2026-11-23T01:05:00Z"));
  assert.equal(
    readFileSync(file, "utf8"),
    HEADER +
      "2026-11-23T01:02:03Z\tframe\tcounted the work\tsize first\tcommit abc\topen\n" +
      "2026-11-23T01:05:00Z\tfix\ta b\t'=bad\tx\ttests green\n",
  );
});

test("appendRow never rewrites existing rows and adds the header to an empty file", () => {
  const kept = path.join(dir, "kept.tsv");
  writeFileSync(kept, HEADER + "old\trow\n");
  appendRow(kept, ["p", "d", "w", "e", "r"]);
  assert.match(readFileSync(kept, "utf8"), /^ts\tphase.*\nold\trow\n\S+\tp\td\tw\te\tr\n$/s);
  const empty = path.join(dir, "empty.tsv");
  writeFileSync(empty, "");
  appendRow(empty, ["p", "d", "w", "e", "r"]);
  assert.ok(readFileSync(empty, "utf8").startsWith(HEADER));
});

test("appendRow rejects a wrong cell count", () => {
  assert.throws(() => appendRow(path.join(dir, "x.tsv"), ["only", "four", "cells", "here"]), /expected 5 cells/);
});

test("the CLI appends a row and rejects wrong arity with exit 1", () => {
  const script = fileURLToPath(new URL("./decision-log.ts", import.meta.url));
  const file = path.join(dir, "cli.tsv");
  execFileSync(process.execPath, [script, file, "p", "d", "w", "e", "r"]);
  assert.match(readFileSync(file, "utf8"), /\tp\td\tw\te\tr\n$/);
  assert.throws(() => execFileSync(process.execPath, [script, file, "p"], { stdio: "pipe" }), /usage/);
});

test("the CLI still writes when started through a symlinked directory", () => {
  const link = path.join(dir, "linked-scripts");
  symlinkSync(path.dirname(fileURLToPath(new URL("./decision-log.ts", import.meta.url))), link);
  const file = path.join(dir, "via-link.tsv");
  execFileSync(process.execPath, [path.join(link, "decision-log.ts"), file, "p", "d", "w", "e", "r"]);
  assert.match(readFileSync(file, "utf8"), /\tp\td\tw\te\tr\n$/);
});
