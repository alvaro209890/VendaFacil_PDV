import { test, expect } from '@playwright/test';
// Layout: o formulario de produto (coluna direita) tem de ficar dentro do cartao.
// Antes o conteudo vazava para fora da borda e empurrava a pagina (pedido 16/11).
const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
const nomeProduto = 'PRODUTO DE LAYOUT COM NOME COMPRIDO PARA QUEBRAR LINHA';
let token = '';
let produtoId = 0;
let categoriaId = 0;

test.beforeAll(async ({ request }) => {
  let r = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (r.status() === 401) r = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(r.status()).toBe(200);
  token = (await r.json()).token;
  const h = { Authorization: `Bearer ${token}` };
  const c = await request.post(`${api}/api/categorias`, { headers: h, data: { nome: 'Cat layout', cor: '#2563eb' } });
  categoriaId = (await c.json()).categoria.id;
  const p = await request.post(`${api}/api/produtos`, { headers: h, data: {
    nome: nomeProduto, categoria_id: categoriaId,
    preco_custo: 2, preco_venda: 3.8, estoque: 31, unidade: 'UN', unidade_compra: 'CART',
    quantidade_por_embalagem: 10, vende_por_unidade: true, preco_embalagem: 30, preco_unidade: 3.8 } });
  expect([200, 201]).toContain(p.status());
  produtoId = (await p.json()).produto.id;
});

test.afterAll(async ({ request }) => {
  const h = { Authorization: `Bearer ${token}` };
  if (produtoId) await request.delete(`${api}/api/produtos/${produtoId}`, { headers: h });
  if (categoriaId) await request.delete(`${api}/api/categorias/${categoriaId}`, { headers: h });
});

for (const altura of [768, 640]) {
  test(`Produtos: formulario de edicao fica dentro do cartao (${altura}px)`, async ({ page }) => {
    await page.addInitScript(t => localStorage.setItem('vf_token', t), token);
    await page.setViewportSize({ width: 1366, height: altura });
    await page.goto('/produtos');
    await page.getByRole('row', { name: new RegExp(nomeProduto) }).getByRole('button', { name: 'Editar' }).click();
    await page.waitForTimeout(400);

    const med = await page.evaluate(() => {
      const card = Array.from(document.querySelectorAll('div')).find(d => (d.className || '').toString().includes('lg:w-80')) as HTMLElement | undefined;
      const main = document.querySelector('main') as HTMLElement;
      return {
        mainScroll: main.scrollHeight,
        mainClient: main.clientHeight,
        cardScroll: card?.scrollHeight ?? 0,
        cardClient: card?.clientHeight ?? 0,
        cardOverflowY: card ? getComputedStyle(card).overflowY : '',
      };
    });

    // O conteudo longo rola dentro do cartao (nao estica a pagina).
    expect(med.cardOverflowY).toBe('auto');
    expect(med.cardScroll).toBeGreaterThan(med.cardClient);
    expect(med.mainScroll).toBeLessThanOrEqual(med.mainClient + 1);
    expect(await page.locator('form button[type="submit"]').count()).toBeGreaterThan(0);
  });
}
