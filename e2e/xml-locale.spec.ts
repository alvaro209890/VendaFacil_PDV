import { test, expect, type Page } from '@playwright/test';

// XML comercial sintético: sem certificado, assinatura ou consulta SEFAZ.
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
  await page.addInitScript(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/produtos');
  await expect(page.getByRole('button', { name: '+ Novo', exact: true })).toBeVisible();
});

async function abrirXml(page: Page, nome: string | string[]) {
  const nomes = Array.isArray(nome) ? nome : [nome];
  const itens = nomes.map((n, i) => `<det nItem="${i + 1}"><prod><xProd>${n}</xProd><cEAN>SEM GTIN</cEAN><uCom>CX</uCom><qCom>2</qCom><vUnCom>3</vUnCom></prod></det>`).join('');
  const xml = `<NFe><infNFe><ide><mod>55</mod><nNF>1</nNF></ide><emit><xNome>Fixture local sintetica</xNome></emit>${itens}</infNFe></NFe>`;
  const resposta = page.waitForResponse(r => r.url().endsWith('/api/produtos/importar-xml/preview') && r.request().method() === 'POST');
  await page.locator('input[type="file"]').setInputFiles({ name: 'fixture-locale.xml', mimeType: 'text/xml', buffer: Buffer.from(xml) });
  expect((await resposta).status()).toBe(200);
  const tabela = page.getByRole('table').filter({ has: page.getByRole('columnheader', { name: 'Qtd XML', exact: true }) });
  await expect(tabela).toBeVisible();
  const linhas = tabela.locator('tbody tr');
  await expect(linhas).toHaveCount(nomes.length);
  const linha = linhas.first();
  const titulos = (await tabela.getByRole('columnheader').allTextContents()).map(t => t.trim());
  return { linha, campo: (rotulo: string) => {
    const indice = titulos.indexOf(rotulo);
    expect(indice).toBeGreaterThanOrEqual(0);
    return linha.getByRole('cell').nth(indice).locator('input');
  } };
}

for (const [rotulo, texto] of [
  ['Qtd XML', '0'], ['Entra', '0'], ['Qtd/emb.', '0,00001'],
  ['Custo R$', ''], ['Venda R$', 'Infinity'], ['Qtd XML', '1e3'],
  ['Custo R$', '1.2.3'], ['Entra', '-1'],
]) {
  test(`U06 XML cobertura: recusa ${rotulo}=${texto} antes da API`, async ({ page }, info) => {
    const { campo } = await abrirXml(page, `XML-limite-${info.testId}`);
    await campo(rotulo).fill(texto);
    let envios = 0;
    page.on('request', r => { if (r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.method() === 'POST') envios += 1; });
    await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
    await expect.poll(async () => envios > 0 || await page.getByRole('alert').isVisible()).toBe(true);
    expect(envios).toBe(0);
    await expect(page.getByRole('alert')).toContainText(rotulo);
  });
}

test('U06 XML cobertura: zero selecionado bloqueia lote, exclusao explicita permite o outro', async ({ page, request }, info) => {
  const nomes = [`XML-zero-${info.testId}`, `XML-incluido-${info.testId}`];
  const { linha, campo } = await abrirXml(page, nomes);
  await campo('Entra').fill('0');
  let envios = 0;
  page.on('request', r => { if (r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.method() === 'POST') envios += 1; });
  await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
  await expect.poll(async () => envios > 0 || await page.getByRole('alert').isVisible()).toBe(true);
  expect(envios).toBe(0);
  await expect(page.getByRole('alert')).toContainText('Entra');
  await linha.getByRole('checkbox', {name:/^Incluir /}).uncheck();
  const resposta = page.waitForResponse(r => r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
  const confirmacao = await resposta;
  expect(confirmacao.status()).toBe(200);
  expect(confirmacao.request().postDataJSON().itens).toHaveLength(1);
  expect(confirmacao.request().postDataJSON().itens[0].nome).toBe(nomes[1]);
  const consulta = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  expect(consulta.status()).toBe(200);
  const produtos = (await consulta.json()).produtos as Array<{ nome: string; estoque: number }>;
  expect(produtos.filter(p => p.nome === nomes[0])).toHaveLength(0);
  expect(produtos.find(p => p.nome === nomes[1])?.estoque).toBe(2);
});

test('U06 XML: cancelar e reabrir nao herda textos da previa anterior', async ({ page }, info) => {
  const anterior = await abrirXml(page, `XML-anterior-${info.testId}`);
  await anterior.campo('Qtd XML').fill('1,5');
  await anterior.campo('Custo R$').fill('9,5');
  await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
  const novo = await abrirXml(page, `XML-novo-${info.testId}`);
  await expect(novo.campo('Qtd XML')).toHaveValue('2');
  await expect(novo.campo('Custo R$')).toHaveValue('3');
});

test('U06 XML: recalculo de fator descarta textos derivados antigos', async ({ page }, info) => {
  const { linha, campo } = await abrirXml(page, `XML-recalculo-${info.testId}`);
  await linha.locator('select').first().selectOption('KG');
  await campo('Entra').fill('7,5');
  await campo('Custo R$').fill('9,5');
  await campo('Qtd/emb.').fill('2');
  await expect(campo('Entra')).toHaveValue(String(2 * 2));
  await expect(campo('Custo R$')).toHaveValue(String(3 / 2));
  await campo('Qtd XML').fill('3,5');
  await expect(campo('Entra')).toHaveValue(String(3.5 * 2));
  const resposta = page.waitForResponse(r => r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
  const r = await resposta;
  expect(r.status()).toBe(200);
  expect(r.request().postDataJSON().itens[0]).toMatchObject({ quantidade: 3.5 * 2, preco_custo: 3 / 2 });
});

test('U06 XML: texto invalido nao importa o custo anterior escondido', async ({ page, request }, info) => {
  const nome = `XML-invalido-${info.testId}`;
  const { campo } = await abrirXml(page, nome);
  await campo('Custo R$').fill('3,25x');
  let envios = 0;
  page.on('request', r => { if (r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.method() === 'POST') envios += 1; });
  await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
  await expect.poll(async () => envios > 0 || await page.getByRole('alert').isVisible()).toBe(true);
  expect(envios).toBe(0);
  await expect(page.getByRole('alert')).toContainText('Custo R$');
  const resposta = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  expect(resposta.status()).toBe(200);
  const salvos = (await resposta.json()).produtos as Array<{ nome: string }>;
  expect(salvos.filter(p => p.nome === nome)).toHaveLength(0);
});

for (const separador of [',', '.']) {
test(`U06 XML: ${separador} nos cinco campos preserva texto, payload e estoque`, async ({ page, request }, info) => {
  const nome = `XML-locale-${info.testId}-${info.repeatEachIndex}`;
  const { linha, campo } = await abrirXml(page, nome);
  await linha.locator('select').first().selectOption('KG');
  await campo('Qtd XML').fill('');
  await campo('Qtd XML').pressSequentially(`1${separador}5`);
  await expect(campo('Qtd XML')).toHaveValue(`1${separador}5`);
  await campo('Qtd/emb.').fill(`1${separador}5`);
  await expect(campo('Qtd/emb.')).toHaveValue(`1${separador}5`);
  await expect(campo('Entra')).toHaveValue(String(1.5 * 1.5));
  await expect(campo('Custo R$')).toHaveValue(String(3 / 1.5));
  await campo('Entra').fill(`2${separador}50`);
  await campo('Custo R$').fill(`3${separador}25`);
  await campo('Venda R$').fill(`5${separador}50`);
  const resposta = page.waitForResponse(r => r.url().endsWith('/api/produtos/importar-xml/confirmar') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Confirmar importação', exact: true }).click();
  const confirmacao = await resposta;
  expect(confirmacao.status()).toBe(200);
  expect(confirmacao.request().postDataJSON().itens[0]).toMatchObject({ quantidade_xml: 1.5, quantidade_por_embalagem: 1.5, quantidade: 2.5, preco_custo: 3.25, preco_venda: 5.5 });
  const consulta = await request.get(`${api}/api/produtos`, { headers: { Authorization: ['Bearer', token].join(' ') } });
  expect(consulta.status()).toBe(200);
  const produtos = (await consulta.json()).produtos as Array<{ nome: string; estoque: number }>;
  const salvos = produtos.filter(p => p.nome === nome);
  expect(salvos).toHaveLength(1);
  expect(salvos[0]).toMatchObject({ estoque: 2.5, preco_custo: 3.25, preco_venda: 5.5, quantidade_por_embalagem: 1.5, unidade: 'KG' });
});
}
