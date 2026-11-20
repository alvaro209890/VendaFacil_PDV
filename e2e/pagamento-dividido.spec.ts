import { expect, test } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test('dinheiro com troco e saldo fiado, com soma inválida bloqueada', async ({ page, request }) => {
  const headers = { Authorization: `Bearer ${token}` };
  const produto = await request.post(`${api}/api/produtos`, {
    headers, data: { nome: 'Produto divisão', preco_venda: 10, estoque: 10 },
  });
  const cadastro = await request.post(`${api}/api/clientes`, { headers, data: { nome: 'Cliente divisão' } });
  expect(produto.status()).toBe(201);
  expect(cadastro.status()).toBe(201);
  const { cliente } = await cadastro.json();
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await page.getByRole('button', { name: /Produto divisão/i }).click();

  const finalizar = page.getByRole('button', { name: /finalizar venda/i });
  await page.getByRole('button', { name: 'Dividir', exact: true }).click();
  await expect(page.getByLabel('Valor da parcela 1')).toHaveValue('10,00');
  await page.getByLabel('Valor da parcela 1').fill('4,50');
  await page.getByLabel('Forma da parcela 2').selectOption('fiado');
  await page.getByLabel('Valor da parcela 2').fill('5,00');
  await expect(page.getByText('Falta R$ 0,50', { exact: true })).toBeVisible();
  await expect(finalizar).toBeDisabled();
  await page.getByLabel('Valor da parcela 2').fill('6,00');
  await expect(page.getByText('Sobra R$ 0,50', { exact: true })).toBeVisible();
  await expect(finalizar).toBeDisabled();
  await page.getByLabel('Valor da parcela 2').fill('5,50');
  await page.getByLabel('Cliente do fiado').selectOption(String(cliente.id));
  await page.getByLabel('Dinheiro recebido').fill('5');
  await expect(page.getByText('Troco R$ 0,50', { exact: true })).toBeVisible();
  const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
  await finalizar.click();
  const resp = await checkout;
  expect(resp.status()).toBe(201);
  expect((await resp.json()).venda.forma_pagamento).toBe('misto');
  const contas = await request.get(`${api}/api/contas-receber`, { headers });
  expect((await contas.json()).contas).toEqual(expect.arrayContaining([
    expect.objectContaining({ cliente_id: cliente.id, valor_pendente: 5.50 }),
  ]));
});

test('PIX automático, débito e crédito cobram somente o valor de cada parcela', async ({ page, request }) => {
  const headers = { Authorization: `Bearer ${token}` };
  const produto = await request.post(`${api}/api/produtos`, {
    headers, data: { nome: 'Produto integrações', preco_venda: 10, estoque: 10 },
  });
  expect(produto.status()).toBe(201);
  const cobrancas: { forma: string; valor: number }[] = [];
  await page.route('**/api/maquininha/config', route => route.fulfill({
    json: { config: { habilitado: true, device_id: 'fixture' } },
  }));
  await page.route('**/api/pix/mp/status', route => route.fulfill({ json: { configurado: true } }));
  await page.route('**/api/pix/mp/cobranca', async route => {
    const { valor } = route.request().postDataJSON();
    cobrancas.push({ forma: 'pix', valor });
    await route.fulfill({ json: { id: 'pix-fixture', valor } });
  });
  await page.route('**/api/pix/mp/cobranca/pix-fixture', route => route.fulfill({
    json: { id: 'pix-fixture', valor: 4, aprovado: true },
  }));
  await page.route('**/api/maquininha/cobranca', async route => {
    const { forma, valor } = route.request().postDataJSON();
    cobrancas.push({ forma, valor });
    await route.fulfill({ json: { payment_intent_id: forma } });
  });
  await page.route('**/api/maquininha/cobranca/*', route => route.fulfill({
    json: { pago: true, state: 'FINISHED', payment_status: 'approved', payment_id: route.request().url().split('/').pop() },
  }));
  await page.route('**/api/vendas/checkout', route => route.fulfill({
    status: 201, json: { venda: { id: 1, forma_pagamento: 'misto', pagamentos: cobrancas }, itens: [] },
  }));
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  const pixPronto = page.waitForResponse(r => r.url().endsWith('/api/pix/mp/status'));
  await page.goto('/pdv');
  await pixPronto;
  await page.getByRole('button', { name: /Produto integrações/i }).click();
  await page.getByRole('button', { name: 'Dividir', exact: true }).click();
  await page.getByRole('button', { name: 'Adicionar parcela', exact: true }).click();
  const partes = [['pix', '4'], ['debito', '2,50'], ['credito', '3,50']];
  for (const [i, [forma, valor]] of partes.entries()) {
    await page.getByLabel(`Forma da parcela ${i + 1}`).selectOption(forma);
    await page.getByLabel(`Valor da parcela ${i + 1}`).fill(valor);
  }
  const checkout = page.waitForRequest(r => r.url().endsWith('/api/vendas/checkout') && r.method() === 'POST');
  await page.getByRole('button', { name: /finalizar venda/i }).click();
  expect((await checkout).postDataJSON().pagamentos).toEqual([
    { forma: 'pix', valor: 4, pix_mp_id: 'pix-fixture' },
    { forma: 'debito', valor: 2.50, pagamento: { payment_id: 'debito' } },
    { forma: 'credito', valor: 3.50, pagamento: { payment_id: 'credito' } },
  ]);
  expect(cobrancas).toEqual([{ forma: 'pix', valor: 4 }, { forma: 'debito', valor: 2.50 }, { forma: 'credito', valor: 3.50 }]);
});

test('Point retoma o envio e a consulta após falhas de rede e fecha a venda uma vez', async ({ page, request }) => {
  const headers = { Authorization: `Bearer ${token}` };
  const produto = await request.post(`${api}/api/produtos`, {
    headers, data: { nome: 'Produto recuperação Point', preco_venda: 19, estoque: 6 },
  });
  expect(produto.status()).toBe(201);
  const referencias: string[] = [];
  const pagamentos: { referencia_checkout: string; pagamento: { payment_id: string } }[] = [];
  let consultas = 0;
  await page.route('**/api/maquininha/config', route => route.fulfill({
    json: { config: { habilitado: true, device_id: 'fixture' } },
  }));
  await page.route('**/api/maquininha/cobranca', route => {
    referencias.push(route.request().postDataJSON().venda_uuid);
    if (referencias.length === 1) {
      return route.fulfill({
        status: 503, json: { detail: { codigo: 'point_antes_do_envio', mensagem: 'Sem conexão' } },
      });
    }
    if (referencias.length === 2) return route.abort('connectionreset');
    return route.fulfill({ status: 201, json: { payment_intent_id: 'ORD-RECUPERACAO', state: 'OPEN' } });
  });
  await page.route('**/api/maquininha/cobranca/ORD-RECUPERACAO', route => {
    expect(route.request().method()).toBe('GET');
    consultas++;
    if (consultas === 1) return route.fulfill({ status: 503, json: { detail: 'Sem conexão' } });
    return route.fulfill({ json: { pago: true, state: 'FINISHED', payment_status: 'approved', payment_id: 'PAY-RECUPERACAO' } });
  });
  await page.route('**/api/vendas/checkout', route => {
    pagamentos.push(route.request().postDataJSON());
    if (pagamentos.length === 1) return route.abort('connectionreset');
    return route.fulfill({ status: 201, json: { venda: { id: 1, forma_pagamento: 'debito' }, itens: [] } });
  });
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  const pronta = page.waitForResponse(r => r.url().endsWith('/api/maquininha/config'));
  await page.goto('/pdv');
  await pronta;
  await page.getByRole('button', { name: 'Produto recuperação Point', exact: false }).click();
  await page.getByRole('button', { name: 'Débito', exact: true }).click();
  const finalizar = page.getByRole('button', { name: /finalizar venda/i });
  await finalizar.click();
  await expect(page.getByText('Reconectando com o Mercado Pago')).toBeVisible();
  await expect(page.getByRole('button', { name: /registrar cartão manual/i })).toHaveCount(0);
  await expect(page.getByText(/retome para registrar a mesma venda/i)).toBeVisible({ timeout: 20_000 });
  await finalizar.click();
  await expect(page.getByText(/venda finalizada/i)).toBeVisible();
  expect(referencias).toHaveLength(3);
  expect(new Set(referencias).size).toBe(1);
  expect(consultas).toBe(2);
  expect(pagamentos.map(p => p.referencia_checkout)).toEqual([referencias[0], referencias[0]]);
  expect(pagamentos.map(p => p.pagamento.payment_id)).toEqual(['PAY-RECUPERACAO', 'PAY-RECUPERACAO']);
});

test('Point só libera outra tentativa depois de confirmar o cancelamento', async ({ page, request }) => {
  const headers = { Authorization: `Bearer ${token}` };
  const produto = await request.post(`${api}/api/produtos`, {
    headers, data: { nome: 'Produto cancelamento Point', preco_venda: 8, estoque: 6 },
  });
  expect(produto.status()).toBe(201);
  let cancelamentos = 0;
  let consultasDepoisDeCancelar = 0;
  await page.route('**/api/maquininha/config', route => route.fulfill({
    json: { config: { habilitado: true, device_id: 'fixture' } },
  }));
  await page.route('**/api/maquininha/cobranca', route => route.fulfill({
    json: { payment_intent_id: 'ORD-CANCELAMENTO', state: 'ON_TERMINAL' },
  }));
  await page.route('**/api/maquininha/cobranca/ORD-CANCELAMENTO', route => {
    if (route.request().method() === 'DELETE') {
      cancelamentos++;
      return route.fulfill({ json: { cancelado: false } });
    }
    if (cancelamentos) consultasDepoisDeCancelar++;
    return route.fulfill({ json: { pago: false, state: consultasDepoisDeCancelar >= 2 ? 'CANCELED' : 'ON_TERMINAL' } });
  });
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  const pronta = page.waitForResponse(r => r.url().endsWith('/api/maquininha/config'));
  await page.goto('/pdv');
  await pronta;
  await page.getByRole('button', { name: 'Produto cancelamento Point', exact: false }).click();
  await page.getByRole('button', { name: 'Débito', exact: true }).click();
  const finalizar = page.getByRole('button', { name: /finalizar venda/i });
  await finalizar.click();
  const cancelamento = page.waitForResponse(r => r.request().method() === 'DELETE' && r.url().endsWith('/ORD-CANCELAMENTO'));
  await page.getByRole('button', { name: 'CANCELAR', exact: true }).click();
  await cancelamento;
  await expect(page.getByText('Aguardando confirmação do cancelamento')).toBeVisible();
  await expect(finalizar).toBeDisabled();
  await expect(page.getByRole('button', { name: /registrar cartão manual/i })).toHaveCount(0);
  await expect(finalizar).toBeEnabled({ timeout: 10_000 });
  expect(cancelamentos).toBe(1);
  expect(consultasDepoisDeCancelar).toBe(2);
});
