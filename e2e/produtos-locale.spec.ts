import { test, expect, type Dialog } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/produtos');
  await expect(page.getByRole('button', { name: '+ Novo', exact: true })).toBeVisible();
});

test('U01: cadastro de produto com virgula em todos os campos decimais', async ({ page, request }, info) => {
  const barcode = `789${Math.floor(1000000000 + Math.random() * 9000000000)}`;
  const nome = `Fracionado-Virgula-${info.testId}`;

  await page.getByRole('button', { name: '+ Novo', exact: true }).click();
  await page.getByPlaceholder('Ex: Arroz 5kg').fill(nome);
  await page.getByPlaceholder('789...').fill(barcode);
  await page.getByPlaceholder('UN, KG, LT').fill('KG');

  const unidadeCompra = page.getByText('Unidade da compra', { exact: true }).locator('..').locator('select');
  await unidadeCompra.selectOption('CX');

  const campoCusto = page.getByText('Preço Custo', { exact: true }).locator('..').locator('input');
  const campoVenda = page.getByText('Preço Venda', { exact: true }).locator('..').locator('input');
  const campoEstoque = page.getByText('Estoque', { exact: true }).locator('..').locator('input');
  const campoMinimo = page.getByText('Estoque Mínimo', { exact: true }).locator('..').locator('input');
  const campoFator = page.getByText('Qtd por compra', { exact: true }).locator('..').locator('input');

  await campoCusto.fill('1,50');
  await campoVenda.fill('3,50');
  await campoEstoque.fill('10,500');
  await campoMinimo.fill('2,500');
  await campoFator.fill('1,5');

  await expect(campoCusto).toHaveValue('1,50');
  await expect(campoVenda).toHaveValue('3,50');
  await expect(campoEstoque).toHaveValue('10,500');
  await expect(campoMinimo).toHaveValue('2,500');
  await expect(campoFator).toHaveValue('1,5');

  const criacaoPromise = page.waitForResponse(
    r => r.url().endsWith('/api/produtos') && r.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Criar Produto', exact: true }).click();
  const resp = await criacaoPromise;
  expect(resp.status()).toBe(201);

  const payload = resp.request().postDataJSON();
  expect(payload.preco_custo).toBe(1.5);
  expect(payload.preco_venda).toBe(3.5);
  expect(payload.estoque).toBe(10.5);
  expect(payload.estoque_minimo).toBe(2.5);
  expect(payload.quantidade_por_embalagem).toBe(1.5);

  const lista = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  expect(lista.status()).toBe(200);
  const produtos = (await lista.json()).produtos;
  const salvo = produtos.find((p: { codigo_barras: string }) => p.codigo_barras === barcode);
  expect(salvo).toBeDefined();
  expect(salvo.preco_custo).toBe(1.5);
  expect(salvo.preco_venda).toBe(3.5);
  expect(salvo.estoque).toBe(10.5);
  expect(salvo.estoque_minimo).toBe(2.5);
  expect(salvo.quantidade_por_embalagem).toBe(1.5);
});

test('U02: cadastro de produto com ponto em todos os campos decimais', async ({ page, request }, info) => {
  const barcode = `789${Math.floor(1000000000 + Math.random() * 9000000000)}`;
  const nome = `Fracionado-Ponto-${info.testId}`;

  await page.getByRole('button', { name: '+ Novo', exact: true }).click();
  await page.getByPlaceholder('Ex: Arroz 5kg').fill(nome);
  await page.getByPlaceholder('789...').fill(barcode);
  await page.getByPlaceholder('UN, KG, LT').fill('KG');

  const unidadeCompra = page.getByText('Unidade da compra', { exact: true }).locator('..').locator('select');
  await unidadeCompra.selectOption('CX');

  const campoCusto = page.getByText('Preço Custo', { exact: true }).locator('..').locator('input');
  const campoVenda = page.getByText('Preço Venda', { exact: true }).locator('..').locator('input');
  const campoEstoque = page.getByText('Estoque', { exact: true }).locator('..').locator('input');
  const campoMinimo = page.getByText('Estoque Mínimo', { exact: true }).locator('..').locator('input');
  const campoFator = page.getByText('Qtd por compra', { exact: true }).locator('..').locator('input');

  await campoCusto.fill('1.50');
  await campoVenda.fill('3.50');
  await campoEstoque.fill('10.500');
  await campoMinimo.fill('2.500');
  await campoFator.fill('1.5');

  await expect(campoCusto).toHaveValue('1.50');
  await expect(campoVenda).toHaveValue('3.50');
  await expect(campoEstoque).toHaveValue('10.500');
  await expect(campoMinimo).toHaveValue('2.500');
  await expect(campoFator).toHaveValue('1.5');

  const criacaoPromise = page.waitForResponse(
    r => r.url().endsWith('/api/produtos') && r.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Criar Produto', exact: true }).click();
  const resp = await criacaoPromise;
  expect(resp.status()).toBe(201);

  const payload = resp.request().postDataJSON();
  expect(payload.preco_custo).toBe(1.5);
  expect(payload.preco_venda).toBe(3.5);
  expect(payload.estoque).toBe(10.5);
  expect(payload.estoque_minimo).toBe(2.5);
  expect(payload.quantidade_por_embalagem).toBe(1.5);

  const lista = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  const produtos = (await lista.json()).produtos;
  const salvo = produtos.find((p: { codigo_barras: string }) => p.codigo_barras === barcode);
  expect(salvo).toBeDefined();
  expect(salvo.preco_custo).toBe(1.5);
  expect(salvo.preco_venda).toBe(3.5);
  expect(salvo.estoque).toBe(10.5);
  expect(salvo.estoque_minimo).toBe(2.5);
  expect(salvo.quantidade_por_embalagem).toBe(1.5);
});

test('U03: edicao de produto atualiza com virgula e ponto', async ({ page, request }, info) => {
  const barcode = `789${Math.floor(1000000000 + Math.random() * 9000000000)}`;
  const nome = `Editar-${info.testId}`;

  const prodRes = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      nome,
      codigo_barras: barcode,
      unidade: 'KG',
      unidade_compra: 'CX',
      preco_custo: 1.0,
      preco_venda: 2.0,
      estoque: 5.0,
      estoque_minimo: 1.0,
      quantidade_por_embalagem: 1.0,
    },
  });
  expect(prodRes.status()).toBe(201);
  const prodId = (await prodRes.json()).produto.id;

  await page.reload();
  const row = page.locator('tbody tr').filter({ hasText: nome });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: 'Editar', exact: true }).click();

  const campoCusto = page.getByText('Preço Custo', { exact: true }).locator('..').locator('input');
  const campoVenda = page.getByText('Preço Venda', { exact: true }).locator('..').locator('input');
  const campoEstoque = page.getByText('Estoque', { exact: true }).locator('..').locator('input');
  const campoMinimo = page.getByText('Estoque Mínimo', { exact: true }).locator('..').locator('input');
  const campoFator = page.getByText('Qtd por compra', { exact: true }).locator('..').locator('input');

  await campoCusto.fill('2,75');
  await campoVenda.fill('5.25');
  await campoEstoque.fill('8,25');
  await campoMinimo.fill('1.75');
  await campoFator.fill('2,5');

  const updatePromise = page.waitForResponse(
    r => r.url().includes(`/api/produtos/${prodId}`) && r.request().method() === 'PUT'
  );
  await page.getByRole('button', { name: 'Salvar Alterações', exact: true }).click();
  const resp = await updatePromise;
  expect(resp.status()).toBe(200);

  const payload = resp.request().postDataJSON();
  expect(payload.preco_custo).toBe(2.75);
  expect(payload.preco_venda).toBe(5.25);
  expect(payload.estoque).toBe(8.25);
  expect(payload.estoque_minimo).toBe(1.75);
  expect(payload.quantidade_por_embalagem).toBe(2.5);

  const getRes = await request.get(`${api}/api/produtos/${prodId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(getRes.status()).toBe(200);
  const atualizado = (await getRes.json()).produto;
  expect(atualizado.preco_custo).toBe(2.75);
  expect(atualizado.preco_venda).toBe(5.25);
  expect(atualizado.estoque).toBe(8.25);
  expect(atualizado.estoque_minimo).toBe(1.75);
  expect(atualizado.quantidade_por_embalagem).toBe(2.5);
});

test('U04: validacao impede envio de texto invalido e nao usa fallback silencioso 0/1', async ({ page }, info) => {
  const nome = `Invalido-${info.testId}`;
  await page.getByRole('button', { name: '+ Novo', exact: true }).click();
  await page.getByPlaceholder('Ex: Arroz 5kg').fill(nome);

  const campoCusto = page.getByText('Preço Custo', { exact: true }).locator('..').locator('input');
  await campoCusto.fill('invalido');

  let fezPost = false;
  page.on('request', req => {
    if (req.url().endsWith('/api/produtos') && req.method() === 'POST') fezPost = true;
  });

  await page.getByRole('button', { name: 'Criar Produto', exact: true }).click();
  await expect(page.getByText(/inválido/i)).toBeVisible();
  expect(fezPost).toBe(false);

  // Corrige custo e testa fator inválido <= 0 ou texto
  await campoCusto.fill('10');
  const campoFator = page.getByText('Qtd por compra', { exact: true }).locator('..').locator('input');
  await campoFator.fill('abc');

  await page.getByRole('button', { name: 'Criar Produto', exact: true }).click();
  await expect(page.getByText(/inválid/i)).toBeVisible();
  expect(fezPost).toBe(false);
});

test('U06: fator abaixo do minimo nao e elevado silenciosamente', async ({ page }, info) => {
  await page.getByRole('button', { name: '+ Novo', exact: true }).click();
  await page.getByPlaceholder('Ex: Arroz 5kg').fill(`Fator-minimo-${info.testId}`);
  const campo = page.getByText('Qtd por compra', { exact: true }).locator('..').locator('input');
  await campo.fill('0,00001');
  let envios = 0;
  page.on('request', r => { if (r.url().endsWith('/api/produtos') && r.method() === 'POST') envios += 1; });
  await page.getByRole('button', { name: 'Criar Produto', exact: true }).click();
  const erro = page.getByText('Quantidade por compra inválida.', { exact: true });
  await expect.poll(async () => envios > 0 || await erro.isVisible()).toBe(true);
  expect(envios).toBe(0);
  await expect(erro).toBeVisible();
});

test('U05: campos vazios conservam defaults legitimos (0 e 1 no fator)', async ({ page, request }, info) => {
  const barcode = `789${Math.floor(1000000000 + Math.random() * 9000000000)}`;
  const nome = `Vazios-${info.testId}`;

  await page.getByRole('button', { name: '+ Novo', exact: true }).click();
  await page.getByPlaceholder('Ex: Arroz 5kg').fill(nome);
  await page.getByPlaceholder('789...').fill(barcode);

  const campoCusto = page.getByText('Preço Custo', { exact: true }).locator('..').locator('input');
  const campoVenda = page.getByText('Preço Venda', { exact: true }).locator('..').locator('input');
  const campoEstoque = page.getByText('Estoque', { exact: true }).locator('..').locator('input');
  const campoMinimo = page.getByText('Estoque Mínimo', { exact: true }).locator('..').locator('input');
  const campoFator = page.getByText('Qtd por compra', { exact: true }).locator('..').locator('input');

  await campoCusto.fill('');
  await campoVenda.fill('');
  await campoEstoque.fill('');
  await campoMinimo.fill('');
  await campoFator.fill('');

  const criacaoPromise = page.waitForResponse(
    r => r.url().endsWith('/api/produtos') && r.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Criar Produto', exact: true }).click();
  const resp = await criacaoPromise;
  expect(resp.status()).toBe(201);

  const payload = resp.request().postDataJSON();
  expect(payload.preco_custo).toBe(0);
  expect(payload.preco_venda).toBe(0);
  expect(payload.estoque).toBe(0);
  expect(payload.estoque_minimo).toBe(0);
  expect(payload.quantidade_por_embalagem).toBe(1);

  const lista = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  const produtos = (await lista.json()).produtos;
  const salvo = produtos.find((p: { codigo_barras: string }) => p.codigo_barras === barcode);
  expect(salvo).toBeDefined();
  expect(salvo.preco_custo).toBe(0);
  expect(salvo.preco_venda).toBe(0);
  expect(salvo.estoque).toBe(0);
  expect(salvo.estoque_minimo).toBe(0);
  expect(salvo.quantidade_por_embalagem).toBe(1);
});

test('U06: entrada rapida de estoque aceita virgula e ponto', async ({ page, request }, info) => {
  const barcode = `789${Math.floor(1000000000 + Math.random() * 9000000000)}`;
  const nome = `EntradaRapida-${info.testId}`;

  const prodRes = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      nome,
      codigo_barras: barcode,
      unidade: 'KG',
      preco_custo: 5.0,
      preco_venda: 10.0,
      estoque: 5.0,
      estoque_minimo: 1.0,
      quantidade_por_embalagem: 1.0,
    },
  });
  expect(prodRes.status()).toBe(201);
  const prodId = (await prodRes.json()).produto.id;

  await page.reload();
  const row = page.locator('tbody tr').filter({ hasText: nome });
  await expect(row).toBeVisible();

  // Entrada com vírgula '1,5'
  page.once('dialog', async dialog => {
    await dialog.accept('1,5');
  });
  const entrada1Promise = page.waitForResponse(
    r => r.url().includes(`/api/produtos/${prodId}/entrada`) && r.request().method() === 'POST'
  );
  await row.getByRole('button', { name: '+ Estoque', exact: true }).click();
  const resp1 = await entrada1Promise;
  expect(resp1.status()).toBe(200);
  expect(resp1.request().postDataJSON().quantidade).toBe(1.5);

  const check1 = await request.get(`${api}/api/produtos/${prodId}`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await check1.json()).produto.estoque).toBe(6.5);

  // Entrada com ponto '0.75'
  page.once('dialog', async dialog => {
    await dialog.accept('0.75');
  });
  const entrada2Promise = page.waitForResponse(
    r => r.url().includes(`/api/produtos/${prodId}/entrada`) && r.request().method() === 'POST'
  );
  await row.getByRole('button', { name: '+ Estoque', exact: true }).click();
  const resp2 = await entrada2Promise;
  expect(resp2.status()).toBe(200);
  expect(resp2.request().postDataJSON().quantidade).toBe(0.75);

  const check2 = await request.get(`${api}/api/produtos/${prodId}`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await check2.json()).produto.estoque).toBe(7.25);
});

test('U07: ajuste rapido aceita perda com virgula e inventario com zero e fracionario', async ({ page, request }, info) => {
  const barcode = `789${Math.floor(1000000000 + Math.random() * 9000000000)}`;
  const nome = `AjusteRapido-${info.testId}`;

  const prodRes = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      nome,
      codigo_barras: barcode,
      unidade: 'KG',
      preco_custo: 5.0,
      preco_venda: 10.0,
      estoque: 10.0,
      estoque_minimo: 1.0,
      quantidade_por_embalagem: 1.0,
    },
  });
  expect(prodRes.status()).toBe(201);
  const prodId = (await prodRes.json()).produto.id;

  await page.reload();
  const row = page.locator('tbody tr').filter({ hasText: nome });
  await expect(row).toBeVisible();

  // 1. Ajuste perda com vírgula '1,5'
  let step = 0;
  const onDialogPerda = async (dialog: Dialog) => {
    if (step === 0) {
      step++;
      await dialog.accept('1'); // Opção 1 = Perda
    } else {
      await dialog.accept('1,5');
    }
  };
  page.on('dialog', onDialogPerda);
  const ajuste1Promise = page.waitForResponse(
    r => r.url().includes(`/api/produtos/${prodId}/ajuste`) && r.request().method() === 'POST'
  );
  await row.getByRole('button', { name: 'Ajustar', exact: true }).click();
  const resp1 = await ajuste1Promise;
  page.off('dialog', onDialogPerda);
  expect(resp1.status()).toBe(200);
  expect(resp1.request().postDataJSON().quantidade).toBe(1.5);
  expect(resp1.request().postDataJSON().tipo).toBe('perda');

  const check1 = await request.get(`${api}/api/produtos/${prodId}`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await check1.json()).produto.estoque).toBe(8.5);

  // 2. Ajuste inventário com contagem ZERO '0'
  step = 0;
  const onDialogInvZero = async (dialog: Dialog) => {
    if (step === 0) {
      step++;
      await dialog.accept('3'); // Opção 3 = Inventário
    } else {
      await dialog.accept('0');
    }
  };
  page.on('dialog', onDialogInvZero);
  const ajuste2Promise = page.waitForResponse(
    r => r.url().includes(`/api/produtos/${prodId}/ajuste`) && r.request().method() === 'POST'
  );
  await row.getByRole('button', { name: 'Ajustar', exact: true }).click();
  const resp2 = await ajuste2Promise;
  page.off('dialog', onDialogInvZero);
  expect(resp2.status()).toBe(200);
  expect(resp2.request().postDataJSON().quantidade).toBe(0);
  expect(resp2.request().postDataJSON().tipo).toBe('inventario');

  const check2 = await request.get(`${api}/api/produtos/${prodId}`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await check2.json()).produto.estoque).toBe(0);

  // 3. Ajuste inventário com contagem fracionária vírgula '2,25'
  step = 0;
  const onDialogInvFrac = async (dialog: Dialog) => {
    if (step === 0) {
      step++;
      await dialog.accept('3'); // Opção 3 = Inventário
    } else {
      await dialog.accept('2,25');
    }
  };
  page.on('dialog', onDialogInvFrac);
  const ajuste3Promise = page.waitForResponse(
    r => r.url().includes(`/api/produtos/${prodId}/ajuste`) && r.request().method() === 'POST'
  );
  await row.getByRole('button', { name: 'Ajustar', exact: true }).click();
  const resp3 = await ajuste3Promise;
  page.off('dialog', onDialogInvFrac);
  expect(resp3.status()).toBe(200);
  expect(resp3.request().postDataJSON().quantidade).toBe(2.25);
  expect(resp3.request().postDataJSON().tipo).toBe('inventario');

  const check3 = await request.get(`${api}/api/produtos/${prodId}`, { headers: { Authorization: `Bearer ${token}` } });
  expect((await check3.json()).produto.estoque).toBe(2.25);
});
