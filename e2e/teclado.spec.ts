import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
// Mesma conta descartável do harness U01, para os arquivos funcionarem em qualquer ordem.
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test.beforeEach(async ({ page, request }, info) => {
  // Não capturar console/requisições com credenciais da fixture.
  const codigo = `KEY-${info.testId}`;
  const produto = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 20 },
  });
  expect(produto.status()).toBe(201);
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await expect(page.getByRole('button', { name: new RegExp(codigo) })).toBeVisible();
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.focus();
  await page.keyboard.type(codigo, { delay: 2 });
  await page.keyboard.press('Enter');
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
});

test('U02: F3 foca quantidade e Enter confirma sem vender', async ({ page }) => {
  const quantidade = page.locator('input[type="number"][max="20"]');
  await page.keyboard.press('F3');
  await expect(quantidade).toBeFocused();
  await page.keyboard.press('ControlOrMeta+A');
  await page.keyboard.type('3');
  await page.keyboard.press('Enter');
  await expect(quantidade).toHaveValue('3');
  await expect(page.getByText(`Falta R$ ${(3 * 5).toFixed(2)}`, { exact: true })).toBeVisible();
  await expect(page.getByText(/Venda finalizada!/)).toHaveCount(0);
});

test('U02: F7 seleciona pagamento com Tab e Enter, F2 vende', async ({ page }) => {
  await page.keyboard.press('F7');
  await expect(page.getByRole('button', { name: 'Dinheiro', exact: true })).toBeFocused();
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Débito', exact: true })).toBeFocused();
  await page.keyboard.press('Enter');
  await page.keyboard.press('F2');
  await expect(page.getByText(/Venda finalizada!/)).toBeVisible();
});

test('U02: Enter no dinheiro recebido confirma a venda', async ({ page }) => {
  await page.getByPlaceholder('0,00', { exact: true }).focus();
  await page.keyboard.type('5');
  await page.keyboard.press('Enter');
  await expect(page.getByText(/Venda finalizada!/)).toBeVisible();
});

test('U02: Escape fecha PIX sem finalizar nem apagar carrinho', async ({ page, request }) => {
  const config = await request.put(`${api}/api/pix/config`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { pix_chave: 'fixture-e2e@example.invalid', pix_nome: 'Fixture', pix_cidade: 'Teste' },
  });
  expect(config.status()).toBe(200);
  await page.keyboard.press('F7');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await page.keyboard.press('F2');
  await expect(page.getByRole('heading', { name: 'PAGAMENTO PIX' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('heading', { name: 'PAGAMENTO PIX' })).toHaveCount(0);
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
  await expect(page.getByText(/Venda finalizada!/)).toHaveCount(0);
});

test('U02: F2 e atalhos nao atravessam PIX ainda carregando', async ({ page }) => {
  let liberar!: () => void;
  const trava = new Promise<void>(resolve => { liberar = resolve; });
  let pedidos = 0;
  await page.route('**/api/pix/qrcode', async route => {
    pedidos += 1;
    await trava;
    await route.continue(); // Resposta real do backend, apenas adiada.
  });
  try {
    await page.keyboard.press('F7');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await page.keyboard.press('F2');
    await expect.poll(() => pedidos).toBe(1);
    await expect(page.getByRole('button', { name: /finalizar venda/i })).toBeDisabled();
    await page.keyboard.press('F2');
    await page.keyboard.press('F6');
    expect(pedidos).toBe(1);
    await expect(page.getByPlaceholder('0.00', { exact: true })).not.toBeFocused();
  } finally {
    liberar();
    await page.unrouteAll({ behavior: 'wait' });
  }
});

test('U02: leitor e F4 nao alteram carrinho sob janela PIX', async ({ page, request }) => {
  await request.put(`${api}/api/pix/config`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { pix_chave: 'fixture-e2e@example.invalid', pix_nome: 'Fixture', pix_cidade: 'Teste' },
  });
  const quantidade = page.getByRole('spinbutton', { name: /^Quantidade de KEY-/ });
  const codigo = (await quantidade.getAttribute('aria-label'))!.replace('Quantidade de ', '');
  await page.keyboard.press('F7');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await page.keyboard.press('F4');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await expect(busca).toBeFocused();
  await page.keyboard.press('F2');
  await expect(page.getByRole('heading', { name: 'PAGAMENTO PIX' })).toBeVisible();
  await page.keyboard.type(codigo);
  await page.keyboard.press('Enter');
  await expect(quantidade).toHaveValue('1');
  await page.getByRole('heading', { name: 'PAGAMENTO PIX' }).locator('..').getByRole('button').focus();
  await page.keyboard.press('F4');
  await expect(busca).not.toBeFocused();
});

test('U02: tres produtos distintos e venda inteira so com teclado', async ({ page, request }, info) => {
  const codigos = ['A', 'B'].map(s => `KEY-${info.testId}-${s}`);
  for (const codigo of codigos) {
    const resposta = await request.post(`${api}/api/produtos`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 20 },
    });
    expect(resposta.status()).toBe(201);
  }
  await page.reload(); // Catálogo novo; o primeiro item continua no rascunho.
  for (const codigo of codigos) {
    await expect(page.getByRole('button', { name: codigo, exact: false })).toBeVisible();
    await page.keyboard.press('F4');
    await page.keyboard.type(codigo, { delay: 2 });
    await page.keyboard.press('Enter');
  }
  await expect(page.getByRole('spinbutton', { name: /^Quantidade de KEY-/ })).toHaveCount(3);
  await page.keyboard.press('F7');
  await expect(page.getByRole('button', { name: 'Dinheiro', exact: true })).toBeFocused();
  for (let n = 0; n < 5; n += 1) await page.keyboard.press('Tab');
  await expect(page.getByPlaceholder('0,00', { exact: true })).toBeFocused();
  await page.keyboard.type(String(3 * 5));
  await page.keyboard.press('F2');
  await expect(page.getByText(`Venda finalizada! Total: R$ ${(3 * 5).toFixed(2)}`, { exact: true })).toBeVisible();
});

test('U02: F6 foca desconto e permite ajustar pelo teclado', async ({ page }) => {
  await page.keyboard.press('F6');
  const desconto = page.getByPlaceholder('0.00', { exact: true });
  await expect(desconto).toBeFocused();
  await page.keyboard.type('1');
  await expect(page.getByText('Falta R$ 4.00', { exact: true })).toBeVisible();
});
