// Exercita o React embutido no .exe já aberto pelo roteiro (porta 3021).
// Etapas: "vender" (SEFAZ de teste desligada), "retomar" (após reinício) e
// "autorizada" (SEFAZ de teste ligada). Cada cupom impresso pela tela é salvo
// como HTML e como PDF da impressão do Chromium, na largura escolhida no PDV.
import fs from 'node:fs';
import path from 'node:path';
import { chromium, expect } from '@playwright/test';

const { token, estado, resultado, cupons } = JSON.parse(fs.readFileSync(0, 'utf8'));
const etapa = process.argv[2];
const retomar = etapa === 'retomar';
const offline = etapa === 'vender';

async function salvarCupom(browser, html, nome, mm) {
  fs.mkdirSync(cupons, { recursive: true });
  fs.writeFileSync(path.join(cupons, `${nome}.html`), html);
  const page = await browser.newPage();
  await page.emulateMedia({ media: 'print' });
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => Promise.all(Array.from(document.images, img => img.decode())));
  const altura = await page.evaluate(() => Math.ceil(document.documentElement.scrollHeight));
  await page.pdf({ path: path.join(cupons, `${nome}.pdf`), width: `${mm}mm`, height: `${altura + 4}px`,
    printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  await page.close();
}

async function venderEImprimir(browser, page, mm) {
  const produto = page.getByRole('button', { name: /Açúcar de teste/ });
  await produto.click();
  await page.getByTitle('Largura do papel da impressora térmica').selectOption(String(mm));
  await page.getByLabel('Dinheiro recebido').fill('10');
  await page.getByRole('checkbox', { name: /Emitir NFC-e/ }).check();
  const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
  await page.getByRole('button', { name: /Finalizar venda/i }).click();
  const resposta = await checkout;
  expect(resposta.status()).toBe(201);
  const corpo = await resposta.json();
  expect(corpo.nota?.status).toBe(offline ? 'contingencia' : 'autorizada');
  const imprimir = page.getByRole('button', { name: /Imprimir recibo/ });
  // Duas impressões: a primeira e a reimpressão pelo botão que fica na tela.
  for (let impressao = 0; impressao < 2; impressao++) {
    await page.evaluate(() => { window.__cupom = ''; window.__html = ''; });
    await imprimir.click();
    await page.waitForFunction(() => window.__cupom.includes('DANFE NFC-e'));
    const cupom = await page.evaluate(() => ({ texto: window.__cupom, html: window.__html, qrs: window.__qrs }));
    expect(cupom.html).toContain(`size: ${mm}mm auto`);
    if (offline) {
      expect(cupom.texto).toContain('EMITIDA EM CONTINGÊNCIA');
      expect(cupom.texto).toContain('VIA DO CONSUMIDOR');
      expect(cupom.texto).toContain('VIA DO ESTABELECIMENTO');
      expect(cupom.qrs).toBe(2);
    } else {
      expect(cupom.texto).toContain('Protocolo de autorização');
      expect(cupom.texto).not.toContain('CONTINGÊNCIA');
      expect(cupom.qrs).toBe(1);
    }
    if (impressao === 1) await salvarCupom(browser, cupom.html, `${offline ? 'contingencia' : 'autorizada'}-${mm}mm`, mm);
  }
  return corpo.venda.id;
}

const browser = await chromium.launch();
try {
  const ctx = await browser.newContext({
    storageState: retomar ? estado : undefined,
    viewport: { width: 1366, height: 900 },
  });
  const page = await ctx.newPage();
  if (!retomar) {
    await page.addInitScript(t => {
      localStorage.setItem('vf_token', t);
      localStorage.removeItem('recibo_auto');
      const anexar = Element.prototype.appendChild;
      Element.prototype.appendChild = function (node) {
        const inserido = anexar.call(this, node);
        if (node instanceof HTMLIFrameElement) {
          const win = node.contentWindow;
          win.print = () => {
            window.__cupom = win.document.body.innerText;
            window.__html = '<!doctype html>' + win.document.documentElement.outerHTML;
            window.__qrs = Array.from(win.document.images).filter(img => img.naturalWidth > 0).length;
            win.dispatchEvent(new win.Event('afterprint'));
          };
        }
        return inserido;
      };
    }, token);
  }
  await page.goto('http://127.0.0.1:3021/pdv');
  const total = page.getByText('Total a Pagar', { exact: true });
  if (retomar) {
    await expect(total).toBeVisible({ timeout: 12_000 });
    await expect(page.getByLabel('Quantidade de Açúcar de teste')).toHaveValue('1');
    console.log('Chromium: o carrinho reapareceu no executável reiniciado.');
  } else {
    const vendas = [];
    for (const mm of [58, 80]) vendas.push(await venderEImprimir(browser, page, mm));
    if (offline) {
      await page.getByRole('button', { name: /Açúcar de teste/ }).click();
      await expect(total).toBeVisible();
      await ctx.storageState({ path: estado });
    }
    fs.writeFileSync(resultado, JSON.stringify({ vendas }));
    console.log(`Chromium: ${offline ? 'vendas em contingência' : 'vendas autorizadas'} ${vendas.join(', ')}; ` +
      'impressão e reimpressão do DANFE em 58 e 80 mm salvas em PDF.');
  }
} finally {
  await browser.close();
}
