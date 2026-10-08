#!/usr/bin/env bash
# Builds a small service whose retryLimit setting is also read outside the obvious code path.
# Plain `grep retryLimit` finds the persisted value and the API doc; it misses two derived names:
# the RETRY_LIMIT environment override computed from the key, and the retry_limit CSV import column.
set -euo pipefail

# The eval runner calls this in a fresh workspace; refuse anywhere else so it never commits into a real repo.
if [ -n "$(ls -A)" ]; then
  echo "scaffold.sh: run it in an empty directory" >&2
  exit 1
fi

mkdir -p src/admin src/jobs data docs deploy imports

cat > src/config.js <<'JS'
const fs = require("fs");
const path = require("path");

const SETTINGS_FILE = path.join(__dirname, "..", "data", "settings.json");
const DEFAULTS = { retryLimit: 3, timeoutMs: 5000 };

// timeoutMs -> TIMEOUT_MS; operators override settings per environment this way.
function envName(key) {
  return key.replace(/[A-Z]/g, (c) => `_${c}`).toUpperCase();
}

function loadConfig(env = process.env) {
  const stored = JSON.parse(fs.readFileSync(SETTINGS_FILE, "utf8"));
  const config = { ...DEFAULTS, ...stored };
  for (const key of Object.keys(DEFAULTS)) {
    const value = env[envName(key)];
    if (value !== undefined) config[key] = Number(value);
  }
  return config;
}

module.exports = { loadConfig, envName, SETTINGS_FILE, DEFAULTS };
JS

cat > src/jobs/resend.js <<'JS'
const { loadConfig } = require("../config");

async function resend(message, send) {
  const { retryLimit } = loadConfig();
  for (let attempt = 0; attempt <= retryLimit; attempt += 1) {
    if (await send(message)) return true;
  }
  return false;
}

module.exports = { resend };
JS

cat > src/admin/settings.js <<'JS'
const fs = require("fs");
const { loadConfig, SETTINGS_FILE } = require("../config");

const EDITABLE_KEYS = ["retryLimit", "timeoutMs"];

function getSettings() {
  return loadConfig();
}

function updateSetting(key, value) {
  if (!EDITABLE_KEYS.includes(key)) throw new Error(`unknown setting: ${key}`);
  const stored = JSON.parse(fs.readFileSync(SETTINGS_FILE, "utf8"));
  stored[key] = value;
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(stored, null, 2));
}

module.exports = { getSettings, updateSetting };
JS

cat > data/settings.json <<'JSON'
{
  "retryLimit": 7,
  "timeoutMs": 8000
}
JSON

cat > docs/API.md <<'MD'
# Admin API

`GET /admin/settings` returns the effective settings. The mobile app and the ops dashboard read it.

```json
{ "retryLimit": 7, "timeoutMs": 8000 }
```

`PUT /admin/settings/:key` updates one setting. Allowed keys: `retryLimit`, `timeoutMs`.
MD

cat > deploy/production.env <<'ENV'
# Loaded by the process manager in production.
RETRY_LIMIT=10
TIMEOUT_MS=12000
ENV

cat > src/admin/import.js <<'JS'
const { updateSetting } = require("./settings");

// Bulk import from the ops spreadsheet export: one "column,value" row per setting.
function camel(column) {
  return column.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

function importCsv(text) {
  for (const line of text.trim().split("\n").slice(1)) {
    const [column, value] = line.split(",");
    updateSetting(camel(column), Number(value));
  }
}

module.exports = { importCsv };
JS

cat > imports/settings-template.csv <<'CSV'
column,value
retry_limit,5
timeout_ms,6000
CSV

cat > package.json <<'JSON'
{ "name": "notify-service", "version": "1.4.0", "private": true }
JSON

git init -q
git -c user.email=eval@example.com -c user.name=eval add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm "initial"
