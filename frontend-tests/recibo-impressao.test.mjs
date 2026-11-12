import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import { chromium } from '@playwright/test';

test('E10 aguarda a imagem e remove o iframe somente em afterprint', async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const js = ts.transpileModule(fs.readFileSync('src/lib/recibo.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
    }).outputText;
    await page.addScriptTag({ type: 'module', content: `${js}\nwindow.__imprimir = imprimirRecibo;` });
    await page.waitForFunction(() => typeof window.__imprimir === 'function');
    await page.evaluate(() => {
      const anexar = document.body.appendChild.bind(document.body);
      window.__impressas = 0;
      document.body.appendChild = node => {
        const result = anexar(node);
        if (node.tagName === 'IFRAME') {
          const win = node.contentWindow;
          win.print = () => { window.__impressas++; };
          win.HTMLImageElement.prototype.decode = () =>
            new Promise(resolve => { window.__liberarImagem = resolve; });
        }
        return result;
      };
      window.__imprimir({
        loja: { nome: 'Loja de teste' }, itens: [], subtotal: 1, desconto: 0,
        total: 1, forma: 'dinheiro',
        nota: { chave: '5'.repeat(44), status: 'autorizada',
          qrcode_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=' },
      }, 58);
    });
    await page.waitForTimeout(400);
    assert.equal(await page.evaluate(() => window.__impressas), 0);
    await page.evaluate(() => window.__liberarImagem());
    await page.waitForFunction(() => window.__impressas === 1);
    await page.waitForTimeout(1100);
    assert.equal(await page.locator('iframe').count(), 1);
    await page.evaluate(() => {
      const win = document.querySelector('iframe').contentWindow;
      win.dispatchEvent(new win.Event('afterprint'));
    });
    assert.equal(await page.locator('iframe').count(), 0);
  } finally {
    await browser.close();
  }
});
