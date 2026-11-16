import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
// Credenciais exclusivamente da fixture, num SQLite temporário recém-criado.
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;
let codigo: string;

test.beforeAll(async ({ request }) => {
  let registro = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (registro.status() === 401) {
    registro = await request.post(`${api}/api/auth/registro`, { data: fixture });
  }
  expect(registro.status()).toBe(200);
  token = (await registro.json()).token;
  codigo = `E2E-NFCE-PADRAO-${Date.now()}`;
  const produto = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 20 },
  });
  expect(produto.status()).toBe(201);
});

async function fiscal(request: import('@playwright/test').APIRequestContext, dados: Record<string, unknown>) {
  const r = await request.put(`${api}/api/fiscal/config`, {
    headers: { Authorization: `Bearer ${token}` },
    data: dados,
  });
  expect(r.status()).toBe(200);
}

async function abrirPdv(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await expect(page.getByRole('button', { name: new RegExp(codigo) }).first()).toBeVisible();
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(codigo);
  await busca.press('Enter');
  await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
  return page.getByRole('checkbox', { name: /Emitir NFC-e/ });
}

// Nenhuma venda é finalizada aqui: em produção isso iria à SEFAZ.
test('NFC-e marcada por padrão só com fiscal habilitado em produção', async ({ page, request }) => {
  await fiscal(request, { habilitado: true, ambiente: 'homologacao' });
  let caixa = await abrirPdv(page);
  await expect(caixa).not.toBeChecked();

  await fiscal(request, { habilitado: true, ambiente: 'producao' });
  caixa = await abrirPdv(page);
  await expect(caixa).toBeChecked();
  // Operador pode desmarcar numa venda específica.
  await caixa.uncheck();
  await expect(caixa).not.toBeChecked();

  await fiscal(request, { habilitado: false, ambiente: 'producao' });
  caixa = await abrirPdv(page);
  await expect(caixa).not.toBeChecked();

  await fiscal(request, { habilitado: false, ambiente: 'homologacao' });
});
