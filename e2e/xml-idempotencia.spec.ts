import { test, expect } from '@playwright/test';
import { randomBytes } from 'node:crypto';

// Apenas fixture comercial sintética; não demonstra XSD, assinatura ou SEFAZ.
const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test('I08: reimportar a mesma chave pela tela recusa duplicacao sem alterar estoque', async ({ page, request }, info) => {
  const nome = `XML-idempotencia-${info.testId}-${info.repeatEachIndex}`;
  const chave = BigInt(`0x${randomBytes(20).toString('hex')}`).toString().padStart(44, '0').slice(-44);
  const xml = `<NFe><infNFe Id="NFe${chave}"><ide><mod>55</mod><nNF>1</nNF></ide><emit><xNome>Fornecedor de teste sintetico</xNome></emit><det nItem="1"><prod><xProd>${nome}</xProd><cEAN>SEM GTIN</cEAN><uCom>KG</uCom><qCom>2</qCom><vUnCom>3</vUnCom></prod></det></infNFe></NFe>`;
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/produtos');
  await expect(page.getByRole('button', { name: '+ Novo', exact: true })).toBeVisible();

  async function abrirXml() {
    const previewPromise = page.waitForResponse(r => r.url().endsWith('/api/produtos/importar-xml/preview') && r.request().method() === 'POST');
    await page.locator('input[type="file"]').setInputFiles({ name: 'nota-sintetica.xml', mimeType: 'text/xml', buffer: Buffer.from(xml) });
    const preview = await previewPromise;
    expect(preview.status()).toBe(200);
    await expect(page.getByRole('heading', { name: /Importar XML — entrada de estoque/ })).toBeVisible();
  }

  async function confirmar() {
    const resposta = page.waitForResponse(r => r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
    return await resposta;
  }

  await abrirXml();
  const primeira = await confirmar();
  expect(primeira.status()).toBe(200);
  await expect(page.getByRole('heading', { name: /Importar XML — entrada de estoque/ })).toHaveCount(0);
  await abrirXml();
  const repetida = await confirmar();
  expect(repetida.status()).toBe(409);
  expect(primeira.request().postDataJSON().chave).toBe(chave);
  expect(repetida.request().postDataJSON().chave).toBe(chave);
  const erro = await repetida.json();
  expect(typeof erro.detail).toBe('string');
  expect(typeof erro.request_id).toBe('string');
  await expect(page.getByRole('alert')).toContainText(erro.detail);
  await expect(page.getByRole('alert')).toContainText(erro.request_id);

  const respostaLista = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  expect(respostaLista.status()).toBe(200);
  const produtos = (await respostaLista.json()).produtos as Array<{ nome: string; estoque: number }>;
  const encontrados = produtos.filter(p => p.nome === nome);
  expect(encontrados).toHaveLength(1);
  expect(encontrados[0].estoque).toBe(2);
});
