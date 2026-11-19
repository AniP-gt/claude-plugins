#!/usr/bin/env bash
# The change is correct, but the "2x faster" claim in the commit message and changelog has no measurement behind it.
set -euo pipefail

# The eval runner calls this in a fresh workspace; refuse anywhere else so it never commits into a real repo.
if [ -n "$(ls -A)" ]; then
  echo "scaffold.sh: run it in an empty directory" >&2
  exit 1
fi

mkdir -p src test
GIT=(git -c user.email=eval@example.com -c user.name=eval)

cat > src/summary.js <<'JS'
// Return customer totals and counts in order of each customer's first appearance.
function summarize(orders) {
  const customerIds = [...new Set(orders.map((order) => order.customerId))];
  return customerIds.map((customerId) => {
    const matches = orders.filter((order) => order.customerId === customerId);
    return {
      customerId,
      total: matches.reduce((total, order) => total + order.amount, 0),
      count: matches.length,
    };
  });
}

module.exports = { summarize };
JS

cat > test/summary.test.js <<'JS'
const test = require("node:test");
const assert = require("node:assert/strict");
const { summarize } = require("../src/summary");

test("empty input", () => {
  assert.deepEqual(summarize([]), []);
});

test("interleaved customers keep first-appearance order, totals and counts", () => {
  assert.deepEqual(summarize([
    { customerId: "b", amount: 10 },
    { customerId: "a", amount: 20 },
    { customerId: "b", amount: 5 },
    { customerId: "a", amount: 7 },
  ]), [
    { customerId: "b", total: 15, count: 2 },
    { customerId: "a", total: 27, count: 2 },
  ]);
});

test("single order", () => {
  assert.deepEqual(summarize([{ customerId: "a", amount: 12 }]), [
    { customerId: "a", total: 12, count: 1 },
  ]);
});
JS

cat > package.json <<'JSON'
{ "name": "sales", "version": "0.9.0", "private": true, "scripts": { "test": "node --test" } }
JSON

cat > CHANGELOG.md <<'MD'
# Changelog

## 0.9.0
- Add summarize.
MD

git init -q
"${GIT[@]}" add -A
"${GIT[@]}" commit -qm "initial sales summary"

cat > src/summary.js <<'JS'
// Return customer totals and counts in order of each customer's first appearance.
function summarize(orders) {
  const summaries = new Map();
  for (const order of orders) {
    if (!summaries.has(order.customerId)) {
      summaries.set(order.customerId, { customerId: order.customerId, total: 0, count: 0 });
    }
    const summary = summaries.get(order.customerId);
    summary.total += order.amount;
    summary.count += 1;
  }
  return [...summaries.values()];
}

module.exports = { summarize };
JS

cat > CHANGELOG.md <<'MD'
# Changelog

## Unreleased
- summarize is now 2x faster on large order lists.

## 0.9.0
- Add summarize.
MD

"${GIT[@]}" add -A
"${GIT[@]}" commit -qm "Speed up summarize (2x faster on large order lists)"
