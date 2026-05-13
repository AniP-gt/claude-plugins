#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const { resolveMcpServer } = require('../scripts/opencode-mcp-launcher.cjs');

function makeServer(root) {
  const server = path.join(root, 'scripts', 'mcp-server.cjs');
  fs.mkdirSync(path.dirname(server), { recursive: true });
  fs.writeFileSync(server, '', 'utf8');
  return server;
}

test('uses explicit server path when provided', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-mem-mcp-'));
  const server = makeServer(dir);
  assert.strictEqual(resolveMcpServer({ CLAUDE_MEM_MCP_SERVER_PATH: server }), server);
});

test('rejects missing explicit server path', () => {
  assert.throws(
    () => resolveMcpServer({ CLAUDE_MEM_MCP_SERVER_PATH: '/definitely/missing/mcp-server.cjs' }),
    /does not exist/
  );
});

test('uses explicit upstream plugin root', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-mem-root-'));
  const server = makeServer(dir);
  assert.strictEqual(resolveMcpServer({ CLAUDE_MEM_UPSTREAM_PLUGIN_ROOT: dir }), server);
});

test('selects latest semver cache directory with a server', () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'claude-mem-cache-'));
  makeServer(path.join(base, '12.4.8'));
  const latest = makeServer(path.join(base, '12.7.5'));
  fs.mkdirSync(path.join(base, 'not-a-version'), { recursive: true });
  assert.strictEqual(resolveMcpServer({ CLAUDE_MEM_PLUGIN_CACHE: base }), latest);
});

test('handles paths with spaces', () => {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'claude mem cache '));
  const server = makeServer(path.join(base, '1.2.3'));
  assert.strictEqual(resolveMcpServer({ CLAUDE_MEM_PLUGIN_CACHE: base }), server);
});
