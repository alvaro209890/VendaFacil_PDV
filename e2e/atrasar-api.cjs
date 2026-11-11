// Hook exclusivo de teste: atrasa o backend descartável para provar a barreira health.
// Ativar apenas no E2E: NODE_OPTIONS=--require=./e2e/atrasar-api.cjs npx playwright test
const cp = require('node:child_process');
const spawn = cp.spawn;
cp.spawn = function (cmd, args, options) {
  if (/python(?:\.exe)?$/i.test(cmd) && Array.isArray(args) && args.includes('-c')) {
    args = [...args];
    const i = args.indexOf('-c') + 1;
    args[i] = 'import time; time.sleep(4); ' + args[i];
  }
  return spawn.call(this, cmd, args, options);
};
