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
  const codigo = `DEC-${info.testId}`;
  const cadastro = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 10, preco_custo: 4, estoque: 10, unidade: 'KG' },
  });
  expect(cadastro.status()).toBe(201);
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  await page.getByRole('button', { name: new RegExp(codigo) }).click();
});

for (const valor of ['0,50', '0.50']) {
  test(`U03: desconto ${valor} preserva digitacao e valor enviado`, async ({ page }) => {
    const desconto = page.getByLabel('Desconto', { exact: true });
    await desconto.focus();
    await page.keyboard.type(valor);
    await expect(desconto).toHaveValue(valor);
    const numero = Number(valor.replace(',', '.'));
    await expect(page.getByText(`Falta R$ ${(10 - numero).toFixed(2)}`, { exact: true })).toBeVisible();
    await page.getByPlaceholder('0,00', { exact: true }).fill('10');
    const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
    await page.keyboard.press('Enter');
    const resposta = await checkout;
    expect(resposta.status()).toBe(201);
    expect(resposta.request().postDataJSON().desconto).toBe(numero);
    expect((await resposta.json()).venda.total).toBe(10 - numero);
  });
}

for (const caso of [
  { campo: 'quantidade', valor: '0' },
  { campo: 'quantidade', valor: '' },
  { campo: 'quantidade', valor: '11' },
  { campo: 'quantidade', valor: '0,00001' },
  { campo: 'desconto', valor: 'abc' },
  { campo: 'desconto', valor: '-1' },
  { campo: 'desconto', valor: '0,001' },
]) {
  for (const acao of ['F2', 'botao']) {
    test(`U03: ${caso.campo} invalido ${JSON.stringify(caso.valor)} nao vende por ${acao}`, async ({ page }) => {
      let envios = 0;
      page.on('request', r => { if (r.url().endsWith('/api/vendas/checkout')) envios += 1; });
      await page.getByPlaceholder('0,00', { exact: true }).fill('1000');
      const campo = caso.campo === 'desconto' ? page.getByLabel('Desconto', { exact: true }) : page.getByLabel(/^Quantidade de DEC-/);
      await campo.fill(caso.valor);
      if (acao === 'F2') await page.keyboard.press('F2');
      else await page.getByRole('button', { name: /finalizar venda/i }).click();
      await expect.poll(async () => envios > 0 || await page.getByText(/^Corrija /).isVisible()).toBe(true);
      expect(envios).toBe(0);
      await expect(page.getByText(/^Corrija /)).toBeVisible();
    });
  }
}

for (const valor of ['0,5', '0.5', '0,125']) {
  test(`U03: quantidade ${valor} preserva etapas e valor enviado`, async ({ page }) => {
    const quantidade = page.getByLabel(/^Quantidade de DEC-/);
    await quantidade.focus();
    await page.keyboard.press('ControlOrMeta+A');
    let prefixo = '';
    for (const caractere of valor) {
      prefixo += caractere;
      await page.keyboard.type(caractere);
      await expect(quantidade).toHaveValue(prefixo);
    }
    const numero = Number(valor.replace(',', '.'));
    await expect(page.getByText(`Falta R$ ${(10 * numero).toFixed(2)}`, { exact: true })).toBeVisible();
    await page.getByPlaceholder('0,00', { exact: true }).fill('10');
    const checkout = page.waitForResponse(r => r.url().endsWith('/api/vendas/checkout') && r.request().method() === 'POST');
    await page.keyboard.press('Enter');
    const resposta = await checkout;
    expect(resposta.status()).toBe(201);
    expect(resposta.request().postDataJSON().itens[0].quantidade).toBe(numero);
    expect((await resposta.json()).venda.total).toBe(10 * numero);
  });
}
