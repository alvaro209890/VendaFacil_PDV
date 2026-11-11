import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test.beforeEach(async ({ page, request }, info) => {
  const codigo = `FOCO-${info.testId}`;
  const cadastro = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 20 },
  });
  expect(cadastro.status()).toBe(201);
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await expect(page.getByRole('button', { name: new RegExp(codigo) })).toBeVisible();
});

test('U04: adicionar pelo botao devolve foco ao leitor', async ({ page }, info) => {
  const codigo = `FOCO-${info.testId}`;
  await page.getByRole('button', { name: new RegExp(codigo) }).click();
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
  await expect(page.getByPlaceholder(/Bipe o código/)).toBeFocused();
});

for (const forma of ['botao', 'Escape']) {
  test(`U04: fechar PIX por ${forma} devolve foco ao leitor`, async ({ page, request }, info) => {
    const config = await request.put(`${api}/api/pix/config`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { pix_chave: 'fixture-foco@example.invalid', pix_nome: 'Fixture', pix_cidade: 'Teste' },
    });
    expect(config.status()).toBe(200);
    await page.getByRole('button', { name: new RegExp(`FOCO-${info.testId}`) }).click();
    await page.getByRole('button', { name: 'PIX', exact: true }).click();
    await page.keyboard.press('F2');
    const titulo = page.getByRole('heading', { name: 'PAGAMENTO PIX' });
    await expect(titulo).toBeVisible();
    const fechar = titulo.locator('..').getByRole('button');
    await fechar.focus();
    if (forma === 'Escape') await page.keyboard.press('Escape');
    else await fechar.click();
    await expect(titulo).toHaveCount(0);
    await expect(page.getByPlaceholder(/Bipe o código/)).toBeFocused();
  });
}

for (const forma of ['botao', 'F2']) {
  test(`U04: finalizar por ${forma} devolve foco ao leitor`, async ({ page }, info) => {
    await page.getByRole('button', { name: new RegExp(`FOCO-${info.testId}`) }).click();
    await page.getByPlaceholder('0,00', { exact: true }).fill('5');
    if (forma === 'F2') await page.keyboard.press('F2');
    else await page.getByRole('button', { name: /finalizar venda/i }).click();
    await expect(page.getByText(/Venda finalizada!/)).toBeVisible();
    await expect(page.getByPlaceholder(/Bipe o código/)).toBeFocused();
  });
}
