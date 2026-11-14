// Servidores E2E descartáveis: nunca usam dados reais nem o certificado da loja.
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const scratch = process.env.TMPDIR || path.join(process.env.LOCALAPPDATA, 'hermes/cache/scratch');
fs.mkdirSync(scratch, { recursive: true });
const dados = fs.mkdtempSync(path.join(scratch, 'vf-e2e-'));
const porta = Number(process.env.VF_E2E_API_PORT || 3121);
if (![3021,3121].includes(porta)) throw new Error('Porta E2E inválida.');
const env = { ...process.env, VENDAFACIL_DATA_DIR: dados, VENDAFACIL_PAINEL_URL: '',
  VENDAFACIL_NO_BROWSER: '1', VENDAFACIL_PORT: String(porta), PYTHONIOENCODING: 'utf-8' };
delete env.PYTHONPATH;
delete env.VENDAFACIL_JWT_SECRET;
const python = path.join(root, 'backend/.venv/Scripts/python.exe');
const api = spawn(python, ['-X', 'utf8', '-I', '-c',
  `import sys; sys.path.insert(0, ${JSON.stringify(path.join(root, 'backend'))}); import uvicorn; uvicorn.run('main:app', host='127.0.0.1', port=${porta}, access_log=False)`],
  { cwd: root, env, stdio: 'inherit' });
let vite = null;
async function iniciarFrontend() {
  const limite = Date.now() + 45000;
  let pronta = false;
  while (Date.now() < limite) {
    if (api.exitCode !== null) throw new Error('Backend E2E encerrou antes de ficar pronto.');
    try {
      const resposta = await fetch(`http://127.0.0.1:${porta}/health`, { signal: AbortSignal.timeout(500) });
      if (resposta.ok) { pronta = true; break; }
    } catch { /* backend ainda está iniciando */ }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (!pronta) throw new Error('Backend E2E não respondeu ao health em 45 segundos.');
  vite = spawn(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'),
    '--host', '127.0.0.1', '--port', '5173', '--strictPort'],
    { cwd: root, env: { ...env, VITE_API_URL: `http://127.0.0.1:${porta}` }, stdio: 'inherit' });
  vite.on('error', () => { parar(); process.exit(1); });
  vite.on('exit', code => { api.kill(); process.exit(code || 0); });
}
function parar() { api.kill(); vite?.kill(); }
process.on('SIGINT', parar);
process.on('SIGTERM', parar);
process.on('exit', parar);
api.on('error', () => { parar(); process.exit(1); });
api.on('exit', code => { vite?.kill(); process.exit(code || 0); });
iniciarFrontend().catch(error => { console.error(error.message); parar(); process.exit(1); });
