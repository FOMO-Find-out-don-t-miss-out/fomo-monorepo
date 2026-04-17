#!/usr/bin/env node
/**
 * Extracts the FastAPI OpenAPI spec offline and generates TypeScript types
 * for all frontend consumers.
 *
 * Usage: node tooling/generate-frontend-types.mjs
 */
import { execSync } from 'child_process';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

// ── 1. Extract OpenAPI spec from FastAPI (offline, no server needed) ──────────
console.log('Extracting OpenAPI spec from FastAPI app...');
const specJson = execSync(
  'uv run python -c "from app.main import app; import json; print(json.dumps(app.openapi()))"',
  {
    cwd: resolve(ROOT, 'apps', 'api'),
    env: { ...process.env, PYTHONPATH: ROOT },
    encoding: 'utf8',
  }
);

const specPath = resolve(ROOT, 'packages', 'api-spec', 'openapi.json');
writeFileSync(specPath, specJson);

const spec = JSON.parse(specJson);
const endpointCount = Object.keys(spec.paths ?? {}).length;
const schemaCount = Object.keys(spec.components?.schemas ?? {}).length;
console.log(`  Spec saved to packages/api-spec/openapi.json`);
console.log(`  Endpoints: ${endpointCount}, Schemas: ${schemaCount}`);

if (endpointCount < 20) {
  console.error(`ERROR: Expected 20+ endpoints, got ${endpointCount}. Aborting.`);
  process.exit(1);
}

// ── 2. Emit TypeScript types for each frontend ────────────────────────────────
const outputs = [
  'apps/harvester-dashboard/types/api.generated.ts',
  'apps/mobile/types/api.generated.ts',
];

// On Windows pnpm uses .cmd shims; resolve the right bin path
const isWindows = process.platform === 'win32';
const binName = isWindows ? 'openapi-typescript.cmd' : 'openapi-typescript';
const bin = resolve(ROOT, 'node_modules', '.bin', binName);

for (const outRelative of outputs) {
  const outPath = resolve(ROOT, outRelative);
  mkdirSync(dirname(outPath), { recursive: true });

  console.log(`Generating ${outRelative}...`);
  execSync(`"${bin}" "${specPath}" -o "${outPath}"`, {
    cwd: ROOT,
    stdio: 'inherit',
    shell: true,
  });
}

console.log('\nDone — TypeScript types generated for all frontends.');
