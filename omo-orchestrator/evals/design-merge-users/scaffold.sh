#!/usr/bin/env bash
# A user store with duplicates that only match after normalization, users without an email, and orders that
# point at user ids. A merge that compares raw strings or drops the losing ids corrupts or misses data.
set -euo pipefail

# The eval runner calls this in a fresh workspace; refuse anywhere else so it never commits into a real repo.
if [ -n "$(ls -A)" ]; then
  echo "scaffold.sh: run it in an empty directory" >&2
  exit 1
fi

mkdir -p src data

cat > src/users.js <<'JS'
const fs = require("fs");
const path = require("path");

const USERS_FILE = path.join(__dirname, "..", "data", "users.json");

function loadUsers() {
  return JSON.parse(fs.readFileSync(USERS_FILE, "utf8"));
}

function saveUsers(users) {
  fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

function findByEmail(email) {
  return loadUsers().find((user) => user.email === email);
}

module.exports = { loadUsers, saveUsers, findByEmail, USERS_FILE };
JS

cat > src/orders.js <<'JS'
const fs = require("fs");
const path = require("path");

const ORDERS_FILE = path.join(__dirname, "..", "data", "orders.json");

function loadOrders() {
  return JSON.parse(fs.readFileSync(ORDERS_FILE, "utf8"));
}

function ordersFor(userId) {
  return loadOrders().filter((order) => order.userId === userId);
}

module.exports = { loadOrders, ordersFor, ORDERS_FILE };
JS

cat > data/users.json <<'JSON'
[
  { "id": 1, "name": "Aoki", "email": "aoki@example.com", "createdAt": "2024-01-10" },
  { "id": 2, "name": "Aoki K.", "email": "Aoki@Example.com ", "createdAt": "2025-03-02" },
  { "id": 3, "name": "Baba", "email": "", "createdAt": "2024-05-01" },
  { "id": 4, "name": "Chiba", "email": "", "createdAt": "2024-06-12" },
  { "id": 5, "name": "Doi", "email": null, "createdAt": "2024-07-20" },
  { "id": 6, "name": "Endo", "email": "endo@example.com", "createdAt": "2024-02-14" }
]
JSON

cat > data/orders.json <<'JSON'
[
  { "id": 101, "userId": 1, "total": 3200 },
  { "id": 102, "userId": 2, "total": 1800 },
  { "id": 103, "userId": 4, "total": 900 },
  { "id": 104, "userId": 6, "total": 4500 }
]
JSON

cat > package.json <<'JSON'
{ "name": "shop-users", "version": "0.3.0", "private": true }
JSON

git init -q
git -c user.email=eval@example.com -c user.name=eval add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm "initial"
