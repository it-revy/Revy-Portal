/**
 * REVY Enterprise Portal — Node.js Seed Bridge
 * Ensures compatibility with environments executing `node seed.js` or `npm run seed`.
 * Centrally delegates to seed_development.py ensuring 100% idempotent database seeding.
 */
const { spawnSync } = require('child_process');
const path = require('path');

const pythonScript = path.join(__dirname, 'seed_development.py');
const pythonCmd = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

console.log(`[Seed.js] Executing Centralized Seed Script via ${pythonCmd}...`);
const result = spawnSync(pythonCmd, [pythonScript], {
  stdio: 'inherit',
  env: process.env,
  cwd: path.resolve(__dirname, '..')
});

if (result.error) {
  console.error('[Seed.js] Failed to execute Python seed:', result.error);
  process.exit(1);
}

if (result.status !== 0) {
  console.error(`[Seed.js] Seed execution exited with status code ${result.status}`);
  process.exit(result.status || 1);
}

console.log('[Seed.js] Seed completed successfully!');
process.exit(0);
