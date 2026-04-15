const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(projectRoot);

// ─── Monorepo: watch the entire workspace ─────────────────────────────────────
config.watchFolders = [workspaceRoot];

// ─── Monorepo: resolve node_modules from both roots ──────────────────────────
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

// ─── Block list: ignore Python venv and api Python folders ───────────────────
// Metro follows symlinks into pnpm's .pnpm store; these regexes prevent it
// from crawling the Python virtual-env or any __pycache__ trees.
const escapeForRegex = (str) => str.replace(/[/\\]/g, '[/\\\\]');
const wsEscaped = escapeForRegex(workspaceRoot);

config.resolver.blockList = [
  // Monorepo-root .venv (uv / virtualenv)
  new RegExp(`^${wsEscaped}[\\/\\\\]\\.venv[\\/\\\\].*$`),
  // apps/api Python tree
  new RegExp(`^${wsEscaped}[\\/\\\\]apps[\\/\\\\]api[\\/\\\\]\\.venv[\\/\\\\].*$`),
  new RegExp(`^${wsEscaped}[\\/\\\\]apps[\\/\\\\]api[\\/\\\\]__pycache__[\\/\\\\].*$`),
  new RegExp(`^${wsEscaped}[\\/\\\\]apps[\\/\\\\]api[\\/\\\\].*\\.pyc$`),
  // Any __pycache__ anywhere in the workspace
  new RegExp(`^${wsEscaped}[\\/\\\\].*[\\/\\\\]__pycache__[\\/\\\\].*$`),
];

// ─── NativeWind: compile global.css through Tailwind ─────────────────────────
module.exports = withNativeWind(config, {
  input: './global.css',
  inlineRem: 16,
});
