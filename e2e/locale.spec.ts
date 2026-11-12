import { test, expect, type APIRequestContext } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
let token: string;

async function fecharDescartavel(request: APIRequestContext) {
  const headers = { Authorization: `Bearer ${token}` };
  const atual = await request.get(`${api}/api/caixa/atual`, { headers });
  expect(atual.status()).toBe(200);
  if ((await atual.json()).aberto) {
    const fim = await request.post(`${api}/api/caixa/fechar`, { headers, data: { valor_fechamento: 0 } });
    expect(fim.status()).toBe(200);
  }
}

test.beforeAll(async ({ request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  token = (await login.json()).token;
});

test.beforeEach(async ({ page, request }) => {
  await fecharDescartavel(request);
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/caixa');
});

test.afterEach(async ({ request }) => { await fecharDescartavel(request); });

for (const valor of ['1,50', '1.50']) {
  test(`U06: fechamento ${valor} persiste valor contado correto`, async ({ page, request }) => {
    const headers = { Authorization: `Bearer ${token}` };
    const abertura = await request.post(`${api}/api/caixa/abrir`, { headers, data: { valor_abertura: 1.5 } });
    expect(abertura.status()).toBe(200);
    const sessaoId = (await abertura.json()).sessao.id;
    await page.reload();
    const campo = page.getByPlaceholder('0,00', { exact: true });
    await campo.focus();
    await page.keyboard.type(valor);
    await expect(campo).toHaveValue(valor);
    page.once('dialog', d => d.accept());
    const fechamento = page.waitForResponse(r => r.url().endsWith('/api/caixa/fechar') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Fechar caixa', exact: true }).click();
    const resposta = await fechamento;
    expect(resposta.status()).toBe(200);
    const numero = Number(valor.replace(',', '.'));
    expect(resposta.request().postDataJSON().valor_fechamento).toBe(numero);
    const historico = await request.get(`${api}/api/caixa/historico`, { headers });
    expect(historico.status()).toBe(200);
    const sessoes: { id: number; valor_fechamento: number; diferenca: number }[] = (await historico.json()).sessoes;
    const salva = sessoes.find(s => s.id === sessaoId);
    expect(salva?.valor_fechamento).toBe(numero);
    expect(salva?.diferenca).toBe(0);
  });
}


for (const valor of ['1,50', '1.50']) {
  test(`U06: criar fiado ${valor} persiste decimal`, async ({ page, request }, info) => {
    await page.goto('/contas-receber');
    await page.getByRole('button', { name: '+ Nova', exact: true }).click();
    const campo = page.getByPlaceholder('Valor *', { exact: true });
    await campo.focus();
    await page.keyboard.type(valor);
    await expect(campo).toHaveValue(valor);
    const observacao = `CRIAR-${info.testId}`;
    await page.getByPlaceholder('Observação', { exact: true }).fill(observacao);
    const criada = page.waitForResponse(r => r.url().endsWith('/api/contas-receber') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Criar Conta', exact: true }).click();
    const resposta = await criada;
    expect(resposta.status()).toBe(201);
    const numero = Number(valor.replace(',', '.'));
    expect(resposta.request().postDataJSON().valor_total).toBe(numero);
    const lista = await request.get(`${api}/api/contas-receber`, { headers: { Authorization: `Bearer ${token}` } });
    expect(lista.status()).toBe(200);
    const contas: { observacao: string; valor_total: number; valor_pendente: number }[] = (await lista.json()).contas;
    const conta = contas.find(c => c.observacao === observacao);
    expect(conta?.valor_total).toBe(numero);
    expect(conta?.valor_pendente).toBe(numero);
  });

  test(`U06: receber fiado ${valor} nao trunca centavos`, async ({ page, request }, info) => {
    const headers = { Authorization: `Bearer ${token}` };
    const observacao = `PAGAR-${info.testId}`;
    const criada = await request.post(`${api}/api/contas-receber`, { headers, data: { valor_total: 10, observacao } });
    expect(criada.status()).toBe(201);
    const contaId = (await criada.json()).conta.id;
    await page.goto('/contas-receber');
    const cartao = page.getByText(observacao, { exact: true }).locator('..').locator('..').locator('..');
    page.once('dialog', d => d.accept(valor));
    const paga = page.waitForResponse(r => r.url().endsWith(`/api/contas-receber/${contaId}/pagar`));
    await cartao.getByRole('button', { name: 'Receber', exact: true }).click();
    const resposta = await paga;
    expect(resposta.status()).toBe(200);
    const numero = Number(valor.replace(',', '.'));
    expect(resposta.request().postDataJSON().valor).toBe(numero);
    const salva = await request.get(`${api}/api/contas-receber/${contaId}`, { headers });
    expect(salva.status()).toBe(200);
    const conta = (await salva.json()).conta;
    expect(conta.valor_pendente).toBe(10 - numero);
    expect(conta.pagamentos[0].valor).toBe(numero);
  });
}

for (const valor of ['0,50', '0.50']) {
  test(`U06: suprimento ${valor} persiste sem truncar`, async ({ page, request }) => {
    const headers = { Authorization: `Bearer ${token}` };
    expect((await request.post(`${api}/api/caixa/abrir`, { headers, data: { valor_abertura: 0 } })).status()).toBe(200);
    await page.reload();
    let enviado: number | null = null;
    page.on('request', r => { if (r.url().endsWith('/api/caixa/movimento')) enviado = r.postDataJSON().valor; });
    page.on('dialog', d => d.accept(d.message().includes('Motivo') ? 'Fixture local' : valor));
    await page.getByRole('button', { name: 'Suprimento', exact: true }).click();
    await expect.poll(async () => enviado !== null || await page.getByText('Valor inválido.', { exact: true }).isVisible()).toBe(true);
    const numero = Number(valor.replace(',', '.'));
    expect(enviado).toBe(numero);
    await expect.poll(async () => (await (await request.get(`${api}/api/caixa/atual`, { headers })).json()).resumo.suprimentos).toBe(numero);
  });
}

for (const valor of ['1,50', '1.50']) {
  test(`U06: abertura de caixa ${valor} preserva decimal e persiste valor`, async ({ page, request }) => {
    const campo = page.getByRole('heading', { name: 'Abrir caixa', exact: true }).locator('..').locator('input');
    await campo.focus();
    await page.keyboard.press('ControlOrMeta+A');
    await page.keyboard.type(valor);
    await expect(campo).toHaveValue(valor);
    const abertura = page.waitForResponse(r => r.url().endsWith('/api/caixa/abrir') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Abrir caixa', exact: true }).click();
    const resposta = await abertura;
    expect(resposta.status()).toBe(200);
    const numero = Number(valor.replace(',', '.'));
    expect(resposta.request().postDataJSON().valor_abertura).toBe(numero);
    const persistido = await request.get(`${api}/api/caixa/atual`, { headers: { Authorization: `Bearer ${token}` } });
    expect(persistido.status()).toBe(200);
    expect((await persistido.json()).sessao.valor_abertura).toBe(numero);
    await expect(page.getByRole('heading', { name: 'Fechar caixa', exact: true })).toBeVisible();
  });
}
