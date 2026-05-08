#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const SERVER_RELATIVE_PATH = path.join('scripts', 'mcp-server.cjs');

function expandHome(value) {
  if (!value) return value;
  if (value === '~') return os.homedir();
  if (value.startsWith(`~${path.sep}`)) return path.join(os.homedir(), value.slice(2));
  return value;
}

function isDirectory(value) {
  try {
    return fs.statSync(value).isDirectory();
  } catch {
    return false;
  }
}

function isFile(value) {
  try {
    return fs.statSync(value).isFile();
  } catch {
    return false;
  }
}

function mcpServerPath(pluginRoot) {
  return path.join(pluginRoot, SERVER_RELATIVE_PATH);
}

function hasMcpServer(pluginRoot) {
  return isFile(mcpServerPath(pluginRoot));
}

function versionParts(name) {
  const match = name.match(/^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/);
  if (!match) return null;
  return match.slice(1, 4).map(Number);
}

function compareVersionsDescending(left, right) {
  const leftParts = versionParts(path.basename(left));
  const rightParts = versionParts(path.basename(right));
  if (leftParts && rightParts) {
    for (let index = 0; index < 3; index += 1) {
      if (leftParts[index] !== rightParts[index]) return rightParts[index] - leftParts[index];
    }
    return right.localeCompare(left);
  }
  if (leftParts) return -1;
  if (rightParts) return 1;
  return right.localeCompare(left);
}

function candidateRoots(env = process.env) {
  const roots = [];
  const push = (value) => {
    if (!value) return;
    const resolved = path.resolve(expandHome(value));
    if (!roots.includes(resolved)) roots.push(resolved);
  };

  push(env.CLAUDE_MEM_MCP_SERVER_ROOT);
  push(env.CLAUDE_MEM_UPSTREAM_PLUGIN_ROOT);
  push(env.CLAUDE_MEM_PLUGIN_ROOT);
  push(env.CLAUDE_PLUGIN_ROOT);
  push(env.PLUGIN_ROOT);

  const configDir = expandHome(env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'));

  for (const base of [env.CLAUDE_MEM_PLUGIN_CACHE]) {
    const expandedBase = base ? path.resolve(expandHome(base)) : null;
    if (!expandedBase || !isDirectory(expandedBase)) continue;
    const versions = fs.readdirSync(expandedBase)
      .map((entry) => path.join(expandedBase, entry))
      .filter(isDirectory)
      .sort(compareVersionsDescending);
    for (const version of versions) push(version);
  }

  push(path.join(configDir, 'plugins', 'marketplaces', 'thedotmack', 'plugin'));
  push(path.join(os.homedir(), '.claude', 'plugins', 'marketplaces', 'thedotmack', 'plugin'));
  push(path.join(os.homedir(), '.codex', 'plugins', 'marketplaces', 'thedotmack', 'plugin'));

  for (const base of [
    path.join(configDir, 'plugins', 'cache', 'thedotmack', 'claude-mem'),
    path.join(os.homedir(), '.claude', 'plugins', 'cache', 'thedotmack', 'claude-mem'),
    path.join(os.homedir(), '.codex', 'plugins', 'cache', 'thedotmack', 'claude-mem'),
    path.join(os.homedir(), '.codex', 'plugins', 'cache', 'claude-mem-local', 'claude-mem'),
  ]) {
    const expandedBase = base ? path.resolve(expandHome(base)) : null;
    if (!expandedBase || !isDirectory(expandedBase)) continue;
    const versions = fs.readdirSync(expandedBase)
      .map((entry) => path.join(expandedBase, entry))
      .filter(isDirectory)
      .sort(compareVersionsDescending);
    for (const version of versions) push(version);
  }

  return roots;
}

function resolveMcpServer(env = process.env) {
  if (env.CLAUDE_MEM_MCP_SERVER_PATH) {
    const explicitPath = path.resolve(expandHome(env.CLAUDE_MEM_MCP_SERVER_PATH));
    if (isFile(explicitPath)) return explicitPath;
    throw new Error(`CLAUDE_MEM_MCP_SERVER_PATH does not exist: ${explicitPath}`);
  }

  const root = candidateRoots(env).find(hasMcpServer);
  if (!root) {
    throw new Error([
      'claude-mem MCP server not found.',
      'Install the upstream thedotmack/claude-mem plugin or set CLAUDE_MEM_MCP_SERVER_PATH.',
      `Checked roots: ${candidateRoots(env).join(', ') || '(none)'}`,
    ].join(' '));
  }
  return mcpServerPath(root);
}

function main() {
  let serverPath;
  try {
    serverPath = resolveMcpServer();
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }

  if (process.argv.includes('--print-path')) {
    console.log(serverPath);
    return;
  }

  const child = spawn(process.execPath, [serverPath], { stdio: 'inherit' });
  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
  child.on('error', (error) => {
    console.error(`Failed to start claude-mem MCP server: ${error.message}`);
    process.exit(1);
  });
}

if (require.main === module) main();

module.exports = {
  candidateRoots,
  compareVersionsDescending,
  resolveMcpServer,
};
