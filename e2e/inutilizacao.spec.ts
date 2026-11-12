import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
let token: string;
test.beforeAll(async ({ request }) => {
  const data = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
  let r = await request.post(`${api}/api/auth/login`, { data });
  if (r.status() === 401) r = await request.post(`${api}/api/auth/registro`, { data });
  expect(r.status()).toBe(200);
  token = (await r.json()).token;
});

for (const status of ['inutilizada', 'processando', 'rejeitada', 'conflito']) {
  test(`F4.18: faixa e resultado ${status} na tela (transporte simulado)`, async ({ page }) => {
    let envios = 0;
    let registros: unknown[] = [];
    await page.route('**/api/fiscal/servicos/inutilizacoes', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: { inutilizacoes: registros } });
        return;
      }
      envios++;
      const pedido = route.request().postDataJSON();
      expect(pedido.inicio).toBe(4);
      expect(pedido.fim).toBe(8);
      expect(pedido.justificativa).toBe('Intervalo de teste sem uso anterior');
      if (status === 'conflito') {
        await route.fulfill({ status: 409, json: { detail: 'Faixa contém nota ativa.' } });
        return;
      }
      const registro = { ...pedido, id: 1, status, cstat: status === 'inutilizada' ? '102' : '',
        protocolo: status === 'inutilizada' ? '151260000000010' : '', mensagem: 'Resultado simulado da interface.' };
      registros = [registro];
      await route.fulfill({ json: { inutilizacao: registro } });
    });
    await page.goto('/login');
    await page.evaluate(t => localStorage.setItem('vf_token', t), token);
    await page.goto('/fiscal');
    await page.getByText('Inutilizar numeração sem uso', { exact: true }).click();
    await page.getByLabel('Número inicial da inutilização').fill('4');
    await page.getByLabel('Número final da inutilização').fill('8');
    await page.getByLabel('Justificativa da inutilização').fill('Intervalo de teste sem uso anterior');
    await page.getByRole('button', { name: 'Solicitar inutilização da faixa', exact: true }).click();
    if (status === 'conflito') {
      await expect(page.getByText('Faixa contém nota ativa.', { exact: true })).toBeVisible();
      await expect(page.getByLabel('Histórico de inutilizações')).toHaveCount(0);
    } else {
      await expect(page.getByLabel('Histórico de inutilizações')).toContainText(status);
      await expect(page.getByText(`${status}: Resultado simulado da interface.`, { exact: false })).toBeVisible();
    }
    expect(envios).toBe(1);
  });
}
