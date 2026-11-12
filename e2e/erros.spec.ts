import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;
let produtoId: number;

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test.beforeEach(async ({ page, request }, info) => {
  const codigo = `ERRO-${info.testId}`;
  const cadastro = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 2 },
  });
  expect(cadastro.status()).toBe(201);
  produtoId = (await cadastro.json()).produto.id;
  // Configuração apenas do SQLite descartável; falha local antes de qualquer SEFAZ.
  const fiscal = await request.put(`${api}/api/fiscal/config`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { habilitado: false, ambiente: 'homologacao' },
  });
  expect(fiscal.status()).toBe(200);
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await page.getByRole('button', { name: new RegExp(codigo) }).click();
  await page.getByPlaceholder('0,00', { exact: true }).fill('5');
});

test('F3.13: estoque alterado no backend mostra motivo e preserva carrinho', async ({ page, request }) => {
  const erros: string[] = [];
  page.on('pageerror', e => erros.push(e.message));
  const ajuste = await request.put(`${api}/api/produtos/${produtoId}`, {
    headers: { Authorization: `Bearer ${token}` }, data: { estoque: 0 },
  });
  expect(ajuste.status()).toBe(200);
  const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
  await page.keyboard.press('F2');
  const resposta = await checkout;
  expect(resposta.status()).toBe(400);
  const detalhe = (await resposta.json()).detail;
  expect(Array.isArray(detalhe.erros)).toBe(true);
  const mensagem = detalhe.erros.join(' ');
  expect(mensagem).toContain('Estoque insuficiente');
  await expect(page.getByText(mensagem, { exact: false })).toBeVisible();
  await expect(page.getByLabel(/^Quantidade de ERRO-/)).toHaveValue('1');
  expect(erros).toEqual([]);
});

test('F3.13: caixa fechado avisa sem impedir venda conforme D4', async ({ page, request }) => {
  const caixa = await request.get(`${api}/api/caixa/atual`, { headers: { Authorization: `Bearer ${token}` } });
  expect(caixa.status()).toBe(200);
  expect((await caixa.json()).aberto).toBe(false);
  await expect(page.getByText(/Caixa fechado\. A venda será registrada/)).toBeVisible();
  const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
  await page.keyboard.press('F2');
  expect((await checkout).status()).toBe(201);
  await expect(page.getByText(/Venda finalizada!/)).toBeVisible();
});

test('F3.13: falha fiscal real local aparece sem alegar nota emitida ou repetir venda', async ({ page, request }) => {
  const erros: string[] = [];
  let envios = 0;
  page.on('pageerror', e => erros.push(e.message));
  page.on('request', r => { if (r.url().endsWith('/api/vendas/checkout')) envios += 1; });
  await page.getByRole('checkbox', { name: /Emitir NFC-e/ }).check();
  const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
  await page.keyboard.press('F2');
  const resposta = await checkout;
  expect(resposta.status()).toBe(201);
  const corpo = await resposta.json();
  expect(typeof corpo.erro_nota).toBe('string');
  expect(corpo.erro_nota.length).toBeGreaterThan(0);
  await expect(page.getByText(corpo.erro_nota, { exact: false })).toBeVisible();
  await expect(page.getByText(/Nota emitida/)).toHaveCount(0);
  await expect(page.getByLabel(/^Quantidade de ERRO-/)).toHaveCount(0);
  const venda = await request.get(`${api}/api/vendas/${corpo.venda.id}`, { headers: { Authorization: `Bearer ${token}` } });
  expect(venda.status()).toBe(200);
  expect((await venda.json()).venda.total).toBe(5);
  expect(envios).toBe(1);
  expect(erros).toEqual([]);
});

for (const status of ['rejeitada', 'pendente', 'contingencia', 'autorizada']) {
  test(`F3.13: contrato UI distingue nota ${status} (fixture sem SEFAZ)`, async ({ page }) => {
    // Somente o retorno fiscal na camada do navegador é uma fixture.
    // A venda comercial é gravada pelo backend real; nenhuma nota é autorizada.
    const mensagem = `Simulação local de apresentação: nota ${status} (sem SEFAZ).`;
    await page.route('**/api/vendas/checkout', async route => {
      const resposta = await route.fetch();
      expect(resposta.status()).toBe(201);
      const corpo = await resposta.json();
      await route.fulfill({ response: resposta, json: {
        ...corpo, erro_nota: undefined,
        nota: {
          id: 0, venda_id: corpo.venda.id, ref: 'fixture-ui', modelo: '65',
          numero: null, serie: null, ambiente: 'homologacao', status,
          chave: null, protocolo: null, mensagem,
          motivo_rejeicao: status === 'rejeitada' ? mensagem : null,
          xml_url: null, danfe_url: null, qrcode_url: null,
        },
      } });
    });
    await page.getByRole('checkbox', { name: /Emitir NFC-e/ }).check();
    const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
    await page.getByRole('button', { name: /Finalizar venda/i }).click();
    expect((await checkout).status()).toBe(201);
    if (status === 'autorizada') {
      await expect(page.getByText(/Nota emitida/)).toBeVisible();
    } else {
      await expect(page.getByText(mensagem, { exact: false })).toBeVisible();
      await expect(page.getByText(/Nota emitida/)).toHaveCount(0);
    }
    if (status === 'contingencia') {
      await expect(page.getByRole('button', { name: /Imprimir recibo/ })).toBeVisible();
    }
    await expect(page.getByLabel(/^Quantidade de ERRO-/)).toHaveCount(0);
  });
}
