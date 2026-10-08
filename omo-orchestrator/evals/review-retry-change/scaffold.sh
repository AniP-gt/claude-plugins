#!/usr/bin/env bash
# A billing job plus a follow-up commit that adds retries. The diff looks reasonable on its own; the defects
# need context outside it: the payment client can time out after capturing the charge (retrying without an
# idempotency key double-charges), and the scheduler only picks "pending" invoices, so marking an invoice
# "failed" means nothing ever retries it.
set -euo pipefail

# The eval runner calls this in a fresh workspace; refuse anywhere else so it never commits into a real repo.
if [ -n "$(ls -A)" ]; then
  echo "scaffold.sh: run it in an empty directory" >&2
  exit 1
fi

mkdir -p src/payments src/jobs
GIT=(git -c user.email=eval@example.com -c user.name=eval)

cat > src/payments/client.js <<'JS'
class TimeoutError extends Error {}

// The gateway may capture the charge and still time out before it answers, so a TimeoutError does not
// mean the customer was not charged. Pass the same idempotencyKey to make a repeated call safe.
async function charge({ customerId, amount, idempotencyKey }, gateway) {
  return gateway.post("/charges", { customerId, amount, idempotencyKey });
}

module.exports = { charge, TimeoutError };
JS

cat > src/jobs/scheduler.js <<'JS'
const { billInvoices } = require("./bill-invoices");

// Runs every 10 minutes. Only pending invoices are billed; anything else is left alone.
async function tick(db, gateway) {
  const invoices = await db.query("SELECT * FROM invoices WHERE status = 'pending'");
  await billInvoices(invoices, db, gateway);
}

module.exports = { tick };
JS

cat > src/jobs/bill-invoices.js <<'JS'
const { charge } = require("../payments/client");

async function billInvoices(invoices, db, gateway) {
  for (const invoice of invoices) {
    await charge({ customerId: invoice.customerId, amount: invoice.amount }, gateway);
    await db.update("invoices", invoice.id, { status: "paid" });
  }
}

module.exports = { billInvoices };
JS

cat > package.json <<'JSON'
{ "name": "billing", "version": "2.1.0", "private": true }
JSON

git init -q
"${GIT[@]}" add -A
"${GIT[@]}" commit -qm "initial billing job"

cat > src/jobs/bill-invoices.js <<'JS'
const { charge } = require("../payments/client");

const MAX_ATTEMPTS = 3;

// One flaky gateway call used to abort the whole batch. Retry each charge, and when it still fails,
// mark that invoice failed and move on so the rest of the batch is billed.
async function billInvoices(invoices, db, gateway) {
  for (const invoice of invoices) {
    let paid = false;
    for (let attempt = 1; attempt <= MAX_ATTEMPTS && !paid; attempt += 1) {
      try {
        await charge({ customerId: invoice.customerId, amount: invoice.amount }, gateway);
        paid = true;
      } catch (error) {
        if (attempt === MAX_ATTEMPTS) console.error(`invoice ${invoice.id}: ${error.message}`);
      }
    }
    await db.update("invoices", invoice.id, { status: paid ? "paid" : "failed" });
  }
}

module.exports = { billInvoices };
JS

"${GIT[@]}" add -A
"${GIT[@]}" commit -qm "Retry flaky charges and keep billing the rest of the batch"
