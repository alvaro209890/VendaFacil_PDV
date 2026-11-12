/**
 * Testes F3.18 / S11: Auditoria de XSS em Impressão de Recibo (Chromium real via Node isolado).
 *
 * Estratégia:
 * - Executa em Chromium real headless isolado via @playwright/test.
 * - Transpilação em memória de src/lib/recibo.ts via typescript.transpileModule (ESNext/ES2022).
 * - Sem servidor/Vite, sem portas de rede (page.route aborta requisições externas).
 * - Passa largura 58/80 explicitamente para não depender de localStorage opaco.
 * - Inspeciona DOM do iframe síncrono antes dos timers de print/cleanup.
 * - Stub em window.print no iframe para evitar acionar diálogo de impressão.
 * - Flag canário benigno window.parent.__canarioTeste para provar execução real no DOM.
 * - Cobertura de campos já escapados (loja, itens, chave, cpf, protocolo) rotulados como GREEN.
 * - Testes RED para campos interpolados sem escape: forma, vendaId, nota.numero/serie, qrcode_base64.
 */

import test, { before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { chromium } from '@playwright/test';

// Força diretório scratch para processos e caches temporários no Windows
const SCRATCH_DIR = 'C:/Users/Usuario/AppData/Local/hermes/cache/scratch';
process.env.TEMP = SCRATCH_DIR;
process.env.TMP = SCRATCH_DIR;

// Fixture PNG 1x1 transparente válido para controle de cupom fiscal com QR
const PNG_FIXTURE_VALIDO_B64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

// Chave e dados fiscais sintéticos para controle (sem conexão SEFAZ / sem certificado)
const CHAVE_SINTETICA = '51260111222333000144650010000002001000002002';
const PROTOCOLO_SINTETICO = '151260000002001';

let browser;
let page;

before(async () => {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const tsPath = path.resolve(__dirname, '../src/lib/recibo.ts');
  const tsCode = fs.readFileSync(tsPath, 'utf8');

  const transpiled = ts.transpileModule(tsCode, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
  }).outputText;

  browser = await chromium.launch({ headless: true });
  page = await browser.newPage();

  // Bloqueio total de rede/APIs externas
  await page.route('**/*', (route) => route.abort());

  await page.goto('about:blank');
  await page.addScriptTag({
    type: 'module',
    content: `${transpiled}\nwindow.__vfImprimir = imprimirRecibo;`
  });

  await page.waitForFunction(() => typeof window.__vfImprimir === 'function');
});

after(async () => {
  if (browser) {
    await browser.close();
  }
});

beforeEach(async () => {
  await page.evaluate(() => {
    window.__canarioTeste = false;
    document.querySelectorAll('iframe').forEach((f) => f.remove());
  });
});

// Helper para executar impressão e capturar o DOM do iframe de forma síncrona
async function executarImpressaoEInspecionar(dados, larguraMm = 58) {
  return await page.evaluate(
    ({ d, mm }) => {
      window.__canarioTeste = false;
      window.__vfImprimir(d, mm);

      const iframe = document.querySelector('iframe');
      if (!iframe) {
        return { iframeEncontrado: false };
      }

      // Stub imediato no print do iframe para não engasgar o ambiente headless
      if (iframe.contentWindow) {
        try {
          iframe.contentWindow.print = () => {};
        } catch {
          /* ok */
        }
      }

      const doc = iframe.contentWindow?.document;
      if (!doc) {
        return { iframeEncontrado: true, docEncontrado: false };
      }

      const scripts = Array.from(doc.querySelectorAll('script')).map((s) => ({
        id: s.id || null,
        src: s.src || null,
        text: s.textContent || ''
      }));

      const elementosInjetados = {
        formaElem: !!doc.getElementById('xss-forma-elem'),
        formaScr: !!doc.getElementById('xss-forma-scr'),
        idElem: !!doc.getElementById('xss-id-elem'),
        idScr: !!doc.getElementById('xss-id-scr'),
        numElem: !!doc.getElementById('xss-num-elem'),
        serieElem: !!doc.getElementById('xss-serie-elem'),
        qrScr: !!doc.getElementById('xss-qr-scr'),
        qrElem: !!doc.getElementById('xss-qr-elem'),
        imgDataInjetado: !!doc.querySelector('[data-injetado]'),
        imgOnerror: !!doc.querySelector('img[onerror]'),
        safeLoja: !!doc.getElementById('xss-safe-loja'),
        safeItem: !!doc.getElementById('xss-safe-item'),
        safeChave: !!doc.getElementById('xss-safe-chave')
      };

      const img = doc.querySelector('img');
      const imgInfo = img
        ? {
            src: img.getAttribute('src') || '',
            style: img.getAttribute('style') || '',
            hasOnerror: img.hasAttribute('onerror')
          }
        : null;

      const bodyText = doc.body?.innerText || '';
      const htmlCompleto = doc.documentElement?.innerHTML || '';
      const canarioAtivado = window.__canarioTeste === true;

      // Limpeza antecipada do iframe para não disparar timers de cleanup da produção
      iframe.remove();

      return {
        iframeEncontrado: true,
        docEncontrado: true,
        scripts,
        elementosInjetados,
        imgInfo,
        bodyText,
        htmlCompleto,
        canarioAtivado
      };
    },
    { d: dados, mm: larguraMm }
  );
}

// --------------------------------------------------------------------------
// 1. CONTROLE DE CUPOM NORMAL 58mm (GREEN)
// --------------------------------------------------------------------------
test('Controle: cupom normal 58mm não-fiscal renderiza texto e layout sem erros', async () => {
  const dados = {
    loja: {
      nome: 'Padaria Modelo',
      cnpj: '11.222.333/0001-44',
      endereco: 'Rua Principal, 100'
    },
    itens: [
      { nome: 'Pão Francês', qtd: 0.5, preco: 18.0, subtotal: 9.0, unidade: 'KG' }
    ],
    subtotal: 9.0,
    desconto: 0,
    total: 9.0,
    forma: 'dinheiro',
    recebido: 10.0,
    troco: 1.0,
    vendaId: 101
  };

  const res = await executarImpressaoEInspecionar(dados, 58);
  assert.equal(res.iframeEncontrado, true);
  assert.equal(res.docEncontrado, true);
  assert.equal(res.scripts.length, 0, 'Não deve haver scripts no cupom normal');
  assert.equal(res.canarioAtivado, false);
  assert.match(res.bodyText, /Padaria Modelo/);
  assert.match(res.bodyText, /CUPOM NÃO FISCAL/);
  assert.match(res.bodyText, /Pão Francês/);
  assert.match(res.bodyText, /R\$ 9,00/);
  assert.match(res.bodyText, /#101/);
});

// --------------------------------------------------------------------------
// 2. CONTROLE DE CUPOM NORMAL 80mm COM DANFE E PNG FIXTURE (GREEN)
// --------------------------------------------------------------------------
test('Controle: cupom normal 80mm com DANFE preserva fixture PNG válido e bloco fiscal', async () => {
  const dados = {
    loja: {
      nome: 'Mercadinho São José',
      cnpj: '99.888.777/0001-66'
    },
    itens: [
      { nome: 'Leite Integral', qtd: 2, preco: 5.5, subtotal: 11.0, unidade: 'UN' }
    ],
    subtotal: 11.0,
    desconto: 1.0,
    total: 10.0,
    forma: 'pix',
    vendaId: 'V-200',
    nota: {
      chave: CHAVE_SINTETICA,
      numero: 200,
      serie: 1,
      protocolo: PROTOCOLO_SINTETICO,
      qrcode_base64: PNG_FIXTURE_VALIDO_B64,
      status: 'autorizada',
      cpf: '000.111.222-33'
    }
  };

  const res = await executarImpressaoEInspecionar(dados, 80);
  assert.equal(res.iframeEncontrado, true);
  assert.equal(res.scripts.length, 0);
  assert.equal(res.canarioAtivado, false);
  assert.match(res.bodyText, /DANFE NFC-e/);
  assert.match(res.bodyText, /NFC-e no 200 serie 1/);
  assert.match(res.bodyText, /CONSUMIDOR CPF: 000\.111\.222-33/);
  assert.ok(res.imgInfo, 'Elemento img deve estar presente');
  assert.equal(res.imgInfo.src, `data:image/png;base64,${PNG_FIXTURE_VALIDO_B64}`);
  assert.match(res.imgInfo.style, /width:50mm/, 'Largura 80mm usa QR de 50mm');
  assert.equal(res.imgInfo.hasOnerror, false);
});

// --------------------------------------------------------------------------
// 3. COBERTURA: CAMPOS JÁ ESCAPADOS PELA PRODUÇÃO PERMANECEM INERTES (GREEN)
// --------------------------------------------------------------------------
test('Cobertura: campos protegidos por esc() (loja, itens, chave) são texto inerte', async () => {
  const dados = {
    loja: {
      nome: '<span id="xss-safe-loja">Loja Segura</span>',
      cnpj: '12.345.678/0001-90'
    },
    itens: [
      { nome: '<span id="xss-safe-item">Item Seguro</span>', qtd: 1, preco: 10.0, subtotal: 10.0 }
    ],
    subtotal: 10.0,
    desconto: 0,
    total: 10.0,
    forma: 'dinheiro',
    recebido: 10.0,
    troco: 0,
    nota: {
      chave: '<span id="xss-safe-chave">CHAVE-SINTETICA-SEGURA</span>',
      numero: 1,
      serie: 1
    }
  };

  const res = await executarImpressaoEInspecionar(dados, 58);
  assert.equal(res.elementosInjetados.safeLoja, false, 'Loja com esc() não pode injetar elemento');
  assert.equal(res.elementosInjetados.safeItem, false, 'Item com esc() não pode injetar elemento');
  assert.equal(res.elementosInjetados.safeChave, false, 'Chave com esc() não pode injetar elemento');
  assert.equal(res.canarioAtivado, false);
  assert.match(res.htmlCompleto, /&lt;span id="xss-safe-loja"&gt;/);
});

// --------------------------------------------------------------------------
// 4. RED: FORMA DE PAGAMENTO NÃO MAPEADA DEVE SER TEXTO INERTE
// --------------------------------------------------------------------------
test('RED F3.18: forma de pagamento maliciosa deve ser texto inerte e não executar scripts nem injetar DOM', async () => {
  const dados = {
    loja: { nome: 'Loja Teste' },
    itens: [{ nome: 'Item Teste', qtd: 1, preco: 10.0, subtotal: 10.0 }],
    subtotal: 10.0,
    desconto: 0,
    total: 10.0,
    forma: '<script id="xss-forma-scr">window.parent.__canarioTeste=true</script><span id="xss-forma-elem">Forma Injetada</span>'
  };

  const res = await executarImpressaoEInspecionar(dados, 58);
  assert.equal(res.elementosInjetados.formaElem, false, 'Elemento DOM injetado via forma de pagamento deve ser nulo');
  assert.equal(res.elementosInjetados.formaScr, false, 'Script injetado via forma de pagamento não pode existir no DOM');
  assert.equal(res.canarioAtivado, false, 'Script malicioso em forma não pode executar');
});

// --------------------------------------------------------------------------
// 5. RED: VENDA ID DEVE SER TEXTO INERTE
// --------------------------------------------------------------------------
test('RED F3.18: vendaId malicioso deve ser texto inerte e não executar scripts nem injetar DOM', async () => {
  const dados = {
    loja: { nome: 'Loja Teste' },
    itens: [{ nome: 'Item Teste', qtd: 1, preco: 10.0, subtotal: 10.0 }],
    subtotal: 10.0,
    desconto: 0,
    total: 10.0,
    forma: 'pix',
    vendaId: '<script id="xss-id-scr">window.parent.__canarioTeste=true</script><span id="xss-id-elem">Venda Injetada</span>'
  };

  const res = await executarImpressaoEInspecionar(dados, 58);
  assert.equal(res.elementosInjetados.idElem, false, 'Elemento DOM injetado via vendaId deve ser nulo');
  assert.equal(res.elementosInjetados.idScr, false, 'Script injetado via vendaId não pode existir no DOM');
  assert.equal(res.canarioAtivado, false, 'Script malicioso em vendaId não pode executar');
});

// --------------------------------------------------------------------------
// 6. RED: NOTA.NUMERO E NOTA.SERIE DEVEM SER TEXTO INERTE
// --------------------------------------------------------------------------
test('RED F3.18: nota.numero e nota.serie maliciosos devem ser texto inerte no bloco fiscal', async () => {
  const dados = {
    loja: { nome: 'Loja Teste' },
    itens: [{ nome: 'Item Teste', qtd: 1, preco: 10.0, subtotal: 10.0 }],
    subtotal: 10.0,
    desconto: 0,
    total: 10.0,
    forma: 'pix',
    nota: {
      chave: CHAVE_SINTETICA,
      numero: '<span id="xss-num-elem">999</span>',
      serie: '<span id="xss-serie-elem">1</span>'
    }
  };

  const res = await executarImpressaoEInspecionar(dados, 58);
  assert.equal(res.elementosInjetados.numElem, false, 'nota.numero não pode injetar tags HTML');
  assert.equal(res.elementosInjetados.serieElem, false, 'nota.serie não pode injetar tags HTML');
});

// --------------------------------------------------------------------------
// 7. RED: QRCODE_BASE64 MALICIOSO NÃO PODE INJETAR ATRIBUTOS, EVENTOS OU SCRIPTS
// --------------------------------------------------------------------------
test('RED F3.18: qrcode_base64 com escape de aspas não pode injetar atributos/eventos nem quebrar tag img', async () => {
  const dados = {
    loja: { nome: 'Loja Teste' },
    itens: [{ nome: 'Item Teste', qtd: 1, preco: 10.0, subtotal: 10.0 }],
    subtotal: 10.0,
    desconto: 0,
    total: 10.0,
    forma: 'pix',
    nota: {
      chave: CHAVE_SINTETICA,
      numero: 1,
      serie: 1,
      qrcode_base64: '" onerror="window.parent.__canarioTeste=true" data-injetado="1'
    }
  };

  const res = await executarImpressaoEInspecionar(dados, 58);
  assert.equal(res.elementosInjetados.imgDataInjetado, false, 'Atributo data-injetado não pode ser introduzido na tag img');
  assert.equal(res.elementosInjetados.imgOnerror, false, 'Atributo onerror não pode ser injetado na tag img');
  assert.equal(res.canarioAtivado, false, 'Handler onerror não pode ser disparado');
});
