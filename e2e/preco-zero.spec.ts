import { test, expect } from '@playwright/test';

// D3 (Álvaro, 12/11/2026): produto sem preço de venda não entra no carrinho.
const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };

test('D3: produto sem preço de venda não entra no carrinho e avisa', async ({ page, request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  const token = (await login.json()).token;
  const codigo = `SEMPRECO-${Date.now()}`;
  const cadastro = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 0, preco_custo: 3, estoque: 5 },
  });
  expect(cadastro.status()).toBe(201);

  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await page.getByRole('button', { name: new RegExp(codigo) }).click();
  await expect(page.getByText(/sem preço de venda/)).toBeVisible();
  await expect(page.getByLabel(`Quantidade de ${codigo}`)).toHaveCount(0);
  await expect(page.getByText('Total a Pagar', { exact: true })).toHaveCount(0);
});
