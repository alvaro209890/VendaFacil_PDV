import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
// Credenciais exclusivamente da fixture, num SQLite temporário recém-criado.
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;
let codigo: string;
let produtoId: number;

test.beforeAll(async ({ request }) => {
  let registro = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (registro.status() === 401) {
    registro = await request.post(`${api}/api/auth/registro`, { data: fixture });
  }
  expect(registro.status()).toBe(200);
  token = (await registro.json()).token;
});

test.beforeEach(async ({ page, request }, info) => {
  codigo = `E2E-CART-${info.testId}`;
  const produto = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 20 },
  });
  expect(produto.status()).toBe(201);
  produtoId = (await produto.json()).produto.id;
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await expect(page.getByRole('button', { name: new RegExp(codigo) })).toBeVisible();
});

async function adicionar(page: import('@playwright/test').Page) {
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(codigo);
  await busca.press('Enter');
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
}

test('U01: F5 preserva o carrinho e finalizar apaga o rascunho', async ({ page, request }) => {
  await adicionar(page);
  await page.reload();
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
  await page.getByPlaceholder('0,00', { exact: true }).fill('5');
  await page.getByRole('button', { name: /finalizar venda/i }).click();
  await expect(page.getByText(/Venda finalizada!/)).toBeVisible();
  await page.reload();
  await expect(page.getByText('Total a Pagar', { exact: true })).toHaveCount(0);
  const produtos = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  const vendido = (await produtos.json()).produtos.find((p: { id: number }) => p.id === produtoId);
  expect(vendido.estoque).toBe(19);
});

test('U01: cancelar a venda apaga o rascunho sem baixar estoque', async ({ page, request }) => {
  await adicionar(page);
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Cancelar venda', exact: true }).click();
  await page.reload();
  await expect(page.getByText('Total a Pagar', { exact: true })).toHaveCount(0);
  const produtos = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  const intacto = (await produtos.json()).produtos.find((p: { id: number }) => p.id === produtoId);
  expect(intacto.estoque).toBe(20);
});

test('U01: rascunho corrompido não derruba a tela', async ({ page }) => {
  await adicionar(page);
  await page.evaluate(() => {
    const chave = Object.keys(localStorage).find(k => k.startsWith('vf_carrinho_v1:'));
    if (!chave) throw new Error('Carrinho não foi persistido');
    localStorage.setItem(chave, '{json-invalido');
  });
  await page.reload();
  await expect(page.getByRole('heading', { name: 'CARRINHO' })).toBeVisible();
  await expect(page.getByText('Total a Pagar', { exact: true })).toHaveCount(0);
});

test('U01: outro usuário não recebe o carrinho anterior', async ({ page, request }) => {
  await adicionar(page);
  const outro = await request.post(`${api}/api/auth/registro`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { usuario: 'outro-caixa', nome: 'Outro caixa', senha: 'fixture-outro-caixa' },
  });
  expect(outro.status()).toBe(200);
  const outroToken = (await outro.json()).token;
  await page.evaluate(t => localStorage.setItem('vf_token', t), outroToken);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'CARRINHO' })).toBeVisible();
  await expect(page.getByText('Total a Pagar', { exact: true })).toHaveCount(0);
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.reload();
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
});

test('U01: recarga atualiza o preço do rascunho pelo cadastro atual', async ({ page, request }) => {
  await adicionar(page);
  const atualizacao = await request.put(`${api}/api/produtos/${produtoId}`, {
    headers: { Authorization: `Bearer ${token}` }, data: { preco_venda: 8 },
  });
  expect(atualizacao.status()).toBe(200);
  await page.reload();
  await expect(page.getByPlaceholder('0,00', { exact: true })).toBeVisible();
  await expect(page.getByText('Falta R$ 8.00', { exact: true })).toBeVisible();
});
