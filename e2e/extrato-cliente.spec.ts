import { readFileSync } from 'node:fs';
import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-extrato', nome: 'Teste descartável', senha: 'fixture-e2e-extrato' };
let token = '';

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) {
    login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  }
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test('U08: extrato do cliente mostra o que comprou e exporta PDF', async ({ page, request }, testInfo) => {
  const auth = { Authorization: `Bearer ${token}` };
  const sufixo = Date.now();

  const produto = await request.post(`${api}/api/produtos`, {
    headers: auth,
    data: { nome: `COCA EXTRATO ${sufixo}`, preco_venda: 10, preco_custo: 5, estoque: 30 },
  });
  expect(produto.status()).toBe(201);
  const produtoId = (await produto.json()).produto.id;

  const cliente = await request.post(`${api}/api/clientes`, {
    headers: auth,
    data: { nome: `Cliente Extrato ${sufixo}` },
  });
  expect(cliente.status()).toBe(201);
  const clienteId = (await cliente.json()).cliente.id;

  const venda = await request.post(`${api}/api/vendas/checkout`, {
    headers: auth,
    data: {
      itens: [{ produto_id: produtoId, quantidade: 3 }],
      forma_pagamento: 'fiado',
      cliente_id: clienteId,
    },
  });
  expect(venda.status()).toBe(201);

  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/contas-receber');
  await expect(page.getByText(`Cliente Extrato ${sufixo}`)).toBeVisible();

  await page.getByRole('button', { name: 'Extrato', exact: true }).first().click();
  await expect(page.getByText('Extrato de compras')).toBeVisible();
  await expect(page.getByText(`COCA EXTRATO ${sufixo}`, { exact: false })).toBeVisible();
  await expect(page.getByText('Total comprado')).toBeVisible();
  await expect(page.getByText('Em aberto')).toBeVisible();
  await expect(page.getByText('30,00').first()).toBeVisible();

  // O PDF tem de ser um PDF de verdade: assinatura %PDF e tamanho plausível.
  const esperaDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: /Baixar PDF/ }).click();
  const download = await esperaDownload;
  const caminho = await download.path();
  expect(caminho).toBeTruthy();
  const bytes = readFileSync(caminho as string);
  expect(bytes.subarray(0, 4).toString()).toBe('%PDF');
  expect(bytes.length).toBeGreaterThan(1000);
  expect(download.suggestedFilename()).toMatch(/^extrato-.*\.pdf$/);

  await page.screenshot({ path: testInfo.outputPath('extrato-cliente.png'), fullPage: false });
});
