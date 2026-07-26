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
//
// Must be run through pnpm:
//   pnpm --filter @fomo/mobile validate:config
// Direct `node validate-expo-config.mjs` invocation is intentionally
// unsupported — this script relies on `npm_execpath` (set by pnpm) to launch
// pnpm's own JavaScript entry point directly with the current Node binary.
// There is no shell-based fallback: a shell fallback would have to invoke
// `pnpm`/`pnpm.cmd` through a shell, which is exactly the
// spawn-shell-true pattern this design avoids, keeping the CI security scan
// (Semgrep) clean.

import { spawnSync } from 'node:child_process';
import process from 'node:process';

function fail(message) {
  console.error(`Expo config validation FAILED: ${message}`);
  process.exit(1);
}

// npm_execpath is set by pnpm (and npm/yarn) to the absolute path of its own
// JS entry point when invoking a package script's "scripts" command. Only a
// .js/.cjs/.mjs entry point can be executed directly via `process.execPath`
// with no shell involved.
const npmExecPath = process.env.npm_execpath ?? '';
const isSupportedEntryPoint = /\.(c|m)?js$/.test(npmExecPath);

if (!npmExecPath || !isSupportedEntryPoint) {
  fail(
    'this script must be run through pnpm, not invoked with node directly.\n' +
      '  Run: pnpm --filter @fomo/mobile validate:config',
  );
}

const pnpmExecArgs = ['exec', 'expo', 'config', '--type', 'public', '--json'];

const spawnOptions = {
  encoding: 'utf8',
  env: { ...process.env, EXPO_NO_DOTENV: '1' },
  maxBuffer: 16 * 1024 * 1024,
};

const result = spawnSync(process.execPath, [npmExecPath, ...pnpmExecArgs], spawnOptions);

if (result.error) {
  fail(`could not run '${process.execPath} ${npmExecPath}': ${result.error.message}`);
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
