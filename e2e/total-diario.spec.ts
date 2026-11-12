import { test, expect } from '@playwright/test';

test('U07: historico usa total diario do backend mesmo com pagina de 100 vendas', async ({ page, request }) => {
  const data = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
  let login = await request.post('http://127.0.0.1:3121/api/auth/login', { data });
  if (login.status() === 401) login = await request.post('http://127.0.0.1:3121/api/auth/registro', { data });
  expect(login.status()).toBe(200);
  const token = (await login.json()).token;
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  // Contrato sintético da API: a página é menor que o total do dia inteiro.
  await page.route('**/api/vendas?*', route => route.fulfill({ json: {
    vendas: Array.from({ length: 100 }, (_, id) => ({ id, total: 1,
      criado_em: new Date().toISOString(), status: 'concluida', forma_pagamento: 'dinheiro' })),
    resumo_hoje: { data: '2026-11-12', fuso: 'America/Cuiaba', quantidade: 120, total: 120.27 },
  } }));
  await page.goto('/vendas');
  await expect(page.getByText('Hoje: R$ 120.27', { exact: true })).toBeVisible();
});
