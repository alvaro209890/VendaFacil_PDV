import { test, expect } from '@playwright/test';
// Regressões da revisão visual 1.0.26: moeda pt-BR, "0" solto no card,
// categoria no PDV, busca em Produtos, venda cancelada e preço sugerido.
const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
const sufixo = Date.now().toString().slice(-6);
const nomeSimples = `Visual simples ${sufixo}`;
const nomeCaixa = `Visual caixa ${sufixo}`;
let token: string;
const h = () => ({ Authorization: `Bearer ${token}` });
const ids: number[] = [];
let categoriaId: number;

test.beforeAll(async ({ request }) => {
  let r = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (r.status() === 401) r = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(r.status()).toBe(200); token = (await r.json()).token;
  const caixa = await (await request.get(`${api}/api/caixa/atual`, { headers: h() })).json();
  if (!caixa.aberto) await request.post(`${api}/api/caixa/abrir`, { headers: h(), data: { valor_abertura: 0 } });
  const c = await request.post(`${api}/api/categorias`, { headers: h(), data: { nome: `Cat visual ${sufixo}`, cor: '#2563eb' } });
  categoriaId = (await c.json()).categoria.id;
  for (const data of [
    { nome: nomeSimples, categoria_id: categoriaId, preco_custo: 1000, preco_venda: 1234.5, estoque: 30, unidade: 'UN' },
    { nome: nomeCaixa, preco_custo: 2, preco_venda: 3.8, estoque: 31, unidade: 'UN', unidade_compra: 'CART', quantidade_por_embalagem: 10,
      vende_por_unidade: true, preco_embalagem: 30, preco_unidade: 3.8 },
  ]) {
    const r2 = await request.post(`${api}/api/produtos`, { headers: h(), data });
    expect(r2.status()).toBe(201); ids.push((await r2.json()).produto.id);
  }
});
test.afterAll(async ({ request }) => {
  for (const id of ids) await request.delete(`${api}/api/produtos/${id}`, { headers: h() });
  await request.delete(`${api}/api/categorias/${categoriaId}`, { headers: h() });
});
test.beforeEach(async ({ page }) => { await page.addInitScript(t => localStorage.setItem('vf_token', t), token); });

test('PDV: card mostra categoria, preço em pt-BR e nenhum "0" solto', async ({ page }) => {
  await page.goto('/pdv');
  const card = page.getByRole('button').filter({ hasText: nomeSimples });
  await expect(card).toContainText(`Cat visual ${sufixo}`);
  await expect(card).toContainText('R$ 1.234,50');
  // O texto do card termina no estoque; antes saía "0" entre o preço e o estoque.
  expect((await card.innerText()).split('\n').map(t => t.trim()).filter(Boolean)).not.toContain('0');
});

test('Produtos: busca por nome, estoque em UN no total e preços em pt-BR', async ({ page }) => {
  await page.goto('/produtos');
  await page.getByLabel('Buscar produto').fill(`visual caixa ${sufixo}`);
  const linhas = page.locator('table tbody tr');
  await expect(linhas).toHaveCount(1);
  await expect(linhas.first()).toContainText('3 carteiras e 1 avulso (31 UN no total)');
  await expect(linhas.first()).toContainText('CART: R$ 30,00');
  await expect(linhas.first()).toContainText('Unidade: R$ 3,80');
  await page.getByLabel('Buscar produto').fill('nada-com-esse-nome');
  await expect(page.getByText(/Nenhum produto encontrado para/)).toBeVisible();
});

test('Vendas: venda cancelada aparece marcada na lista', async ({ page, request }) => {
  const v = await request.post(`${api}/api/vendas/checkout`, { headers: h(), data: { itens: [{ produto_id: ids[0], quantidade: 1 }], forma_pagamento: 'debito' } });
  expect(v.status()).toBe(201);
  const id = (await v.json()).venda.id;
  await page.goto('/vendas');
  const linha = page.locator('table tbody tr').filter({ has: page.getByRole('cell', { name: String(id), exact: true }) });
  await expect(linha).toContainText('Débito');
  await expect(linha).not.toContainText('Cancelada');
  expect((await request.post(`${api}/api/vendas/${id}/cancelar`, { headers: h(), data: { motivo: 'Teste visual' } })).ok()).toBeTruthy();
  await page.reload();
  await expect(linha).toContainText('Cancelada');
});

test('Importação: preço sugerido acompanha o custo; preço digitado fica', async ({ page }) => {
  const xml = `<NFe><infNFe><ide><mod>55</mod><nNF>${sufixo}</nNF></ide><emit><xNome>Fornecedor visual</xNome></emit><det><prod><cEAN>SEM GTIN</cEAN><xProd>CX Cerveja visual ${sufixo}</xProd><uCom>CX</uCom><qCom>10</qCom><vUnCom>36.00</vUnCom></prod></det></infNFe></NFe>`;
  await page.goto('/produtos');
  await page.locator('input[type=file]').setInputFiles({ name: 'visual.xml', mimeType: 'text/xml', buffer: Buffer.from(xml) });
  const d = page.getByRole('dialog').filter({ hasText: 'Confirmar importação' });
  const venda = d.getByLabel('Preço de venda do item 1', { exact: true });
  await expect(venda).toHaveValue('46.8');
  await d.getByLabel('Unidades por embalagem do item 1', { exact: true }).fill('12');
  await expect(d.getByLabel('Custo por unidade do item 1', { exact: true })).toHaveValue('3');
  await expect(venda).toHaveValue('3.9');
  await d.getByRole('radio', { name: /^Em unidades soltas/ }).check();
  await expect(venda).toHaveValue('46.8');
  await d.getByRole('radio', { name: /fechada:/ }).check();
  await expect(venda).toHaveValue('3.9');
  await venda.fill('4,50');
  await d.getByRole('radio', { name: /^Em unidades soltas/ }).check();
  await expect(venda).toHaveValue('4,50');
});
