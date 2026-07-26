#!/usr/bin/env node
// Validates the resolved public Expo configuration without printing it.
//
// Used by the `validate:config` package script (part of `ci:quality`, run
// by the dedicated fomo-mobile-quality Jenkins job). The aggregate script is
// deliberately named `ci:quality`, NOT `check-quality` — the root
// `turbo run check-quality` must never discover the mobile package; mobile
// quality runs exclusively in its dedicated job. Requirements:
//   - Node built-ins only (no dependencies)
//   - Windows + Linux compatible
//   - never prints the config, tokens, URLs, or environment values
//   - EXPO_NO_DOTENV=1 so `.env` is neither required nor loaded — the public
//     app config in app.json must be valid on its own.

import { spawnSync } from 'node:child_process';
import process from 'node:process';

const isWindows = process.platform === 'win32';
const pnpmExecArgs = ['exec', 'expo', 'config', '--type', 'public', '--json'];

// Preferred spawn strategy: when this script runs via a pnpm package script,
// npm_execpath points at pnpm's own JS entry point, so we can run it with the
// current Node binary directly — no shell, no .cmd shim, fully cross-platform.
const npmExecPath = process.env.npm_execpath ?? '';
const viaNode = /\.(c|m)?js$/.test(npmExecPath);

const spawnOptions = {
  encoding: 'utf8',
  env: { ...process.env, EXPO_NO_DOTENV: '1' },
  maxBuffer: 16 * 1024 * 1024,
};

let result;
let pnpmCommand;
if (viaNode) {
  pnpmCommand = `node ${npmExecPath}`;
  result = spawnSync(process.execPath, [npmExecPath, ...pnpmExecArgs], spawnOptions);
} else {
  // Fallback for direct invocation outside pnpm. Node refuses to spawn .cmd
  // shims without a shell (CVE-2024-27980 hardening), so on Windows a shell
  // is technically required — pass one fixed literal command string.
  pnpmCommand = isWindows ? 'pnpm.cmd' : 'pnpm';
  result = spawnSync(`${pnpmCommand} ${pnpmExecArgs.join(' ')}`, {
    ...spawnOptions,
    shell: true,
  });
}

function fail(message) {
  console.error(`Expo config validation FAILED: ${message}`);
  process.exit(1);
}

if (result.error) {
  fail(`could not run ${pnpmCommand}: ${result.error.message}`);
}

if (result.status !== 0) {
  // stderr is safe to surface: EXPO_NO_DOTENV=1 means no env values are
  // loaded, and expo's own error text is what makes the failure actionable.
  const stderrSnippet = (result.stderr ?? '').trim().slice(0, 1000);
  fail(
    `'expo config --type public --json' exited with code ${result.status}.` +
      (stderrSnippet ? `\n--- expo stderr (truncated) ---\n${stderrSnippet}` : ''),
  );
}

let config;
try {
  config = JSON.parse(result.stdout);
} catch {
  // Tolerate any non-JSON preamble a wrapper might emit before the config.
  const jsonStart = result.stdout.indexOf('{');
  try {
    config = JSON.parse(result.stdout.slice(jsonStart));
  } catch {
    fail('expo produced output that is not parseable JSON.');
  }
}

const isNonEmptyString = (value) => typeof value === 'string' && value.length > 0;

// `scheme` may resolve as a single string or an array of strings — both are
// valid Expo shapes. This app currently resolves a single string.
const isValidScheme = (value) =>
  isNonEmptyString(value) ||
  (Array.isArray(value) && value.length > 0 && value.every(isNonEmptyString));

const problems = [];
if (!isNonEmptyString(config.name)) problems.push('name: missing or not a non-empty string');
if (!isNonEmptyString(config.slug)) problems.push('slug: missing or not a non-empty string');
if (!isValidScheme(config.scheme)) problems.push('scheme: missing or not a string / string array');
if (!isNonEmptyString(config.android?.package)) problems.push('android.package: missing or not a non-empty string');
if (!isNonEmptyString(config.ios?.bundleIdentifier)) problems.push('ios.bundleIdentifier: missing or not a non-empty string');
if (!Array.isArray(config.plugins)) problems.push('plugins: missing or not an array');

if (problems.length > 0) {
  // Field names only — never the resolved values.
  fail(`resolved public config is invalid:\n  - ${problems.join('\n  - ')}`);
}

console.log('Expo public config is valid.');
