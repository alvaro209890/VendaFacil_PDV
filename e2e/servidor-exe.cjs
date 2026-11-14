// Aceitação do binário baixado do Actions; dados, porta e painel isolados.
const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const exe = process.env.VF_TEST_EXE;
if (!exe || !fs.existsSync(exe)) throw new Error('Informe VF_TEST_EXE com o binário Windows baixado.');
const dados = fs.mkdtempSync(path.join(os.tmpdir(), 'vf-exe-embalagem-'));
const env = {...process.env, VENDAFACIL_DATA_DIR:dados, VENDAFACIL_PORT:'3021',
  VENDAFACIL_NO_BROWSER:'1', VENDAFACIL_PAINEL_URL:''};
delete env.PYTHONPATH;
delete env.VENDAFACIL_JWT_SECRET;
const child = spawn(exe, [], {cwd:path.dirname(exe), env, stdio:'inherit', windowsHide:true});
let parando = false;
function parar() {
  if (parando) return;
  parando = true;
  if (process.platform === 'win32' && child.pid && child.exitCode === null) {
    spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{stdio:'ignore',windowsHide:true});
  } else child.kill();
}
process.on('SIGINT',parar);
process.on('SIGTERM',parar);
process.on('exit',parar);
child.on('error',err=>{console.error(err.message);process.exit(1);});
child.on('exit',code=>process.exit(code || 0));
async function conferir() {
  for (let n=0;n<120;n++) {
    if (child.exitCode !== null) throw new Error('Executável encerrou antes de responder.');
    try {
      const r=await fetch('http://127.0.0.1:3021/health',{signal:AbortSignal.timeout(500)});
      if(r.ok) {
        const body=await r.json();
        if(body.version !== '1.0.16') throw new Error('Artefato não é 1.0.16.');
        console.log('Artefato 1.0.16 pronto na porta 3021, com banco temporário.'); return;
      }
    } catch(err) { if(err.message === 'Artefato não é 1.0.16.') throw err; }
    await new Promise(r=>setTimeout(r,500));
  }
  throw new Error('Executável não respondeu em 60 segundos.');
}
conferir().catch(err=>{console.error(err.message);parar();process.exit(1);});
