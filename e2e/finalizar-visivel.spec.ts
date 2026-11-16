import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
// Credenciais exclusivamente da fixture, num SQLite temporário recém-criado.
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
const prefixo = 'E2E-MUITOS';
let token: string;

test.beforeAll(async ({ request }) => {
  let registro = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (registro.status() === 401) {
    registro = await request.post(`${api}/api/auth/registro`, { data: fixture });
  }
  expect(registro.status()).toBe(200);
  token = (await registro.json()).token;
  // Loja real tem ~240 produtos; a grade fica muito mais alta que a janela.
  const lista = await request.get(`${api}/api/produtos`, { headers: { Authorization: `Bearer ${token}` } });
  const ja = (await lista.json()).produtos.filter((p: { nome: string }) => p.nome.startsWith(prefixo)).length;
  for (let i = ja; i < 240; i++) {
    const r = await request.post(`${api}/api/produtos`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { nome: `${prefixo} ${String(i).padStart(3, '0')}`, codigo_barras: `${prefixo}-${i}`, preco_venda: 5, preco_custo: 2, estoque: 50 },
    });
    expect(r.status()).toBe(201);
  }
});

// 1440x900 do PC do James menos barra do Windows e do navegador, e telas menores.
for (const [w, h] of [[1440, 780], [1366, 650], [1280, 600]]) {
  test(`FINALIZAR VENDA visível sem rolar a página com 240 produtos (${w}x${h})`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await page.goto('/login');
    await page.evaluate(t => localStorage.setItem('vf_token', t), token);
    await page.goto('/pdv');
    const busca = page.getByPlaceholder(/Bipe o código/);
    for (const i of [1, 2, 3, 4, 5, 6]) {
      await busca.fill(`${prefixo}-${i}`);
      await busca.press('Enter');
    }
    await expect(page.getByText('Total a Pagar', { exact: true })).toBeVisible();
    await page.getByRole('button', { name: /dinheiro/i }).first().click();
    await expect(page.getByLabel('Dinheiro recebido')).toBeInViewport();

    const botao = page.getByRole('button', { name: /finalizar venda/i });
    await expect(botao).toBeVisible();
    const caixa = (await botao.boundingBox())!;
    expect(caixa.y).toBeGreaterThanOrEqual(0);
    expect(caixa.y + caixa.height).toBeLessThanOrEqual(h);

    // A página não rola: quem rola é a grade de produtos.
    const rolagem = await page.evaluate(() => {
      const main = document.querySelector('main')!;
      return main.scrollHeight - main.clientHeight;
    });
    expect(rolagem).toBeLessThanOrEqual(1);

    // A grade continua alcançável até o último produto.
    const ultimo = page.getByRole('button', { name: new RegExp(`${prefixo} 239`) });
    await ultimo.scrollIntoViewIfNeeded();
    await expect(ultimo).toBeInViewport();
    await expect(botao).toBeInViewport();
  });
}

// Janela estreita (ou zoom alto): carrinho empilha embaixo da grade, que rola
// por dentro. O pagamento fica a pouca rolagem, não depois dos 240 produtos.
test('janela estreita: pagamento logo abaixo da grade, sem rolar 240 produtos', async ({ page }) => {
  await page.setViewportSize({ width: 1000, height: 700 });
  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/pdv');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(`${prefixo}-1`);
  await busca.press('Enter');
  const grade = page.getByTestId('grade-produtos');
  const alturaGrade = (await grade.boundingBox())!.height;
  expect(alturaGrade).toBeLessThanOrEqual(700 * 0.5 + 1);
  const pagamento = page.getByText('Forma de Pagamento', { exact: true });
  const topo = (await pagamento.boundingBox())!.y;
  expect(topo).toBeLessThan(1400); // antes ficava depois de ~16 mil px de produtos
  await page.getByRole('button', { name: /finalizar venda/i }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('button', { name: /finalizar venda/i })).toBeInViewport();
});
