#!/usr/bin/env bash
# A quadratic duplicate finder; the case leaves measurement to the agent and supplies no benchmark.
set -euo pipefail

# The eval runner calls this in a fresh workspace; refuse anywhere else so it never commits into a real repo.
if [ -n "$(ls -A)" ]; then
  echo "scaffold.sh: run it in an empty directory" >&2
  exit 1
fi

mkdir -p src test
GIT=(git -c user.email=eval@example.com -c user.name=eval)

cat > src/duplicates.js <<'JS'
// Return each value appearing more than once, once, in order of its first occurrence.
function findDuplicates(items) {
  const duplicates = [];
  for (let i = 0; i < items.length; i += 1) {
    for (let j = i + 1; j < items.length; j += 1) {
      if (items[i] === items[j] && !duplicates.includes(items[i])) {
        duplicates.push(items[i]);
      }
    }
  }
  return duplicates;
}

module.exports = { findDuplicates };
JS

cat > src/report.js <<'JS'
const { findDuplicates } = require("./duplicates");

// The nightly import passes about 50,000 order ids.
function buildImportReport(orderIds) {
  const duplicateIds = findDuplicates(orderIds);
  return { total: orderIds.length, duplicateIds };
}

module.exports = { buildImportReport };
JS

cat > test/duplicates.test.js <<'JS'
const test = require("node:test");
const assert = require("node:assert/strict");
const { findDuplicates } = require("../src/duplicates");

test("no duplicates", () => {
  assert.deepEqual(findDuplicates([1, 2, 3]), []);
});

test("duplicates keep first-appearance order", () => {
  assert.deepEqual(findDuplicates([3, 1, 3, 2, 1]), [3, 1]);
});

test("duplicates keep first-appearance order even when another value repeats first", () => {
  assert.deepEqual(findDuplicates([1, 2, 2, 1]), [1, 2]);
});

test("a value appearing three times is returned once", () => {
  assert.deepEqual(findDuplicates([2, 2, 2]), [2]);
});

test("empty input", () => {
  assert.deepEqual(findDuplicates([]), []);
});

test("strings and numbers are not conflated", () => {
  assert.deepEqual(findDuplicates([1, "1"]), []);
});
JS

cat > package.json <<'JSON'
{ "name": "orders", "version": "1.4.0", "private": true, "scripts": { "test": "node --test" } }
JSON

git init -q
"${GIT[@]}" add -A
"${GIT[@]}" commit -qm "initial order tools"
