import { test, expect } from '@playwright/test';

// Janela do caixa (1.0.18): código não cadastrado abre o cadastro rápido;
// produto sem estoque/preço abre a entrada rápida. Tudo em banco descartável.
const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;
const h = () => ({ Authorization: `Bearer ${token}` });
const codigoNovo = () => `78${Date.now()}`.slice(0, 13);

test.beforeAll(async ({ request }) => {
  let r = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (r.status() === 401) r = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(r.status()).toBe(200);
  token = (await r.json()).token;
});

test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
});

async function produtoPorCodigo(request: import('@playwright/test').APIRequestContext, codigo: string) {
  const ps = (await (await request.get(`${api}/api/produtos`, { headers: h() })).json()).produtos;
  return ps.find((p: { codigo_barras: string }) => p.codigo_barras === codigo);
}

test('código não cadastrado abre a janela, cadastra e já vende', async ({ page, request }) => {
  const codigo = codigoNovo();
  await page.goto('/pdv');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(codigo); await busca.press('Enter');
  const janela = page.getByRole('dialog', { name: 'Produto não cadastrado' });
  await expect(janela).toBeVisible();
  await expect(janela).toContainText(codigo);
  await expect(janela.getByLabel('Código de barras')).toHaveValue(codigo);
  // F2 não finaliza nada com a janela aberta.
  await page.keyboard.press('F2');
  await janela.getByLabel('Nome do produto').fill(`Refri teste ${codigo}`);
  await janela.getByRole('button', { name: 'Cadastrar e vender' }).click();
  await expect(janela.getByRole('alert')).toContainText('preço de venda');
  await janela.getByLabel('Preço de venda').fill('6,50');
  await janela.getByLabel('Quantidade em estoque').fill('10');
  await page.screenshot({ path: 'output/playwright/janela-cadastro-rapido.png', animations: 'disabled' });
  await janela.getByRole('button', { name: 'Cadastrar e vender' }).click();
  await expect(janela).toHaveCount(0);
  await expect(page.getByText(/cadastrado e adicionado à venda/)).toBeVisible();
  await expect(page.getByLabel(`Quantidade de Refri teste ${codigo}`, { exact: true })).toHaveValue('1');
  const p = await produtoPorCodigo(request, codigo);
  expect([p.nome, p.preco_venda, p.estoque, p.unidade]).toEqual([`Refri teste ${codigo}`, 6.5, 10, 'UN']);
  await page.getByRole('button', { name: 'Exato', exact: true }).click();
  const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
  await page.keyboard.press('F2');
  expect((await checkout).status()).toBe(201);
  await expect(page.getByText(/Venda finalizada!/)).toBeVisible();
  expect((await produtoPorCodigo(request, codigo)).estoque).toBe(9);
});

test('produto zerado abre a entrada rápida e vende', async ({ page, request }) => {
  const codigo = codigoNovo();
  const r = await request.post(`${api}/api/produtos`, { headers: h(), data: { nome: `Zerado ${codigo}`, codigo_barras: codigo, preco_venda: 4, estoque: 0 } });
  expect(r.status()).toBe(201);
  const id = (await r.json()).produto.id;
  await page.goto('/pdv');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(codigo); await busca.press('Enter');
  const janela = page.getByRole('dialog', { name: 'Sem estoque' });
  await expect(janela).toContainText('Estoque insuficiente');
  await expect(janela).toContainText('tem 0 UN');
  await expect(janela.getByLabel('Preço de venda')).toHaveCount(0);
  await janela.getByLabel('Quantidade em estoque').fill('5');
  await janela.getByRole('button', { name: 'Dar entrada e vender' }).click();
  await expect(page.getByLabel(`Quantidade de Zerado ${codigo}`, { exact: true })).toHaveValue('1');
  expect((await (await request.get(`${api}/api/produtos/${id}`, { headers: h() })).json()).produto.estoque).toBe(5);
  const movs = (await (await request.get(`${api}/api/produtos/${id}/movimentacoes`, { headers: h() })).json()).movimentacoes;
  expect(movs.some((m: { observacao: string; quantidade: number }) => m.observacao === 'Entrada rápida no caixa' && m.quantidade === 5)).toBe(true);
});

test('Esc fecha a janela sem cadastrar nada', async ({ page, request }) => {
  const codigo = codigoNovo();
  await page.goto('/pdv');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(codigo); await busca.press('Enter');
  await expect(page.getByRole('dialog', { name: 'Produto não cadastrado' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(busca).toBeFocused();
  expect(await produtoPorCodigo(request, codigo)).toBeUndefined();
});

test('nome digitado que não existe vem preenchido na janela', async ({ page }) => {
  const nome = `Pao de queijo ${Date.now()}`;
  await page.goto('/pdv');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(nome); await busca.press('Enter');
  const janela = page.getByRole('dialog', { name: 'Produto não cadastrado' });
  await expect(janela.getByLabel('Nome do produto')).toHaveValue(nome);
  await expect(janela.getByLabel('Código de barras')).toHaveValue('');
  await expect(janela.getByLabel('Preço de venda')).toBeFocused();
});
