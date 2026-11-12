import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import { chromium } from '@playwright/test';

let browser, page;
const xml = fs.readFileSync('backend/tests/fixtures/cupom_nfce.xml', 'utf8');
before(async () => {
  browser = await chromium.launch({ headless: true });
  page = await browser.newPage();
  await page.route('**/*', route => route.abort());
  await page.goto('about:blank');
  const codigo = ts.transpileModule(fs.readFileSync('src/lib/recibo.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
  }).outputText;
  await page.addScriptTag({ type: 'module', content: `${codigo}\nwindow.__htmlFiscal = montarHtml;` });
  await page.waitForFunction(() => typeof window.__htmlFiscal === 'function');
});
after(async () => { await browser?.close(); });

for (const largura of [58, 80]) {
  test(`F4.19: DANFE ${largura}mm usa dados do XML e avisa homologacao`, async () => {
    const html = await page.evaluate(({ xml, largura }) => window.__htmlFiscal({
      loja: { nome: 'Nome atual diferente do emitente' }, itens: [{ nome: 'Açúcar', codigo: 'SKU-7', qtd: 1, preco: 10, subtotal: 10 }],
      subtotal: 10, desconto: 0, total: 10, forma: 'dinheiro',
      nota: { chave: '5'.repeat(44), status: 'autorizada', xml }
    }, largura), { xml, largura });
    for (const texto of ['SEM VALOR FISCAL', 'Mercearia Açúcar de Teste', 'IE: 00130000019',
      'Cuiabá', 'SKU-7', '1,23', '151260000000007', '12345678909', 'homologacao.sefaz.mt.gov.br', '12/11/2026']) {
      assert.ok(html.includes(texto), `Campo ausente: ${texto}`);
    }
    assert.ok(!html.includes('Nome atual diferente do emitente'));
    assert.ok(!html.includes('24h'));
    fs.mkdirSync('output/playwright', { recursive: true });
    const render = await browser.newPage({ viewport: { width: Math.ceil(largura / 25.4 * 96), height: 650 } });
    await render.setContent(html);
    await render.screenshot({ path: `output/playwright/danfe-${largura}.png`, fullPage: true });
    await render.close();
  });
}

test('F4.19: tributo ausente nao declara valor nem fonte IBPT inexistente', async () => {
  const html = await page.evaluate(() => window.__htmlFiscal({
    loja: { nome: 'Loja' }, itens: [], subtotal: 10, desconto: 0, total: 10, forma: 'pix',
    nota: { chave: '5'.repeat(44), status: 'contingencia', ambiente: 'homologacao' }
  }, 58));
  assert.ok(html.includes('Tributos aproximados não informados'));
  assert.ok(!html.includes('conforme tabela IBPT'));
  assert.ok(html.includes('primeiro dia útil'));
});

test('F4.19: texto do XML nao injeta HTML no recibo', async () => {
  const malicioso = xml.replace('Mercearia Açúcar de Teste', '&lt;img data-fiscal-injetado="1" src="x"&gt;');
  const seguro = await page.evaluate(xml => {
    const html = window.__htmlFiscal({ loja: { nome: 'Loja' }, itens: [], subtotal: 0, desconto: 0,
      total: 0, forma: 'dinheiro', nota: { chave: '5'.repeat(44), status: 'autorizada', xml } }, 58);
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return !doc.querySelector('[data-fiscal-injetado]') && doc.body.textContent.includes('<img');
  }, malicioso);
  assert.equal(seguro, true);
});
