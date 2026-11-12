import { test, expect } from '@playwright/test';

test('F5.11 copia o diagnóstico autenticado para o suporte', async ({ page, context, request }) => {
  const api = 'http://127.0.0.1:3121';
  const data = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };
  let r = await request.post(`${api}/api/auth/login`, { data });
  if (r.status() === 401) r = await request.post(`${api}/api/auth/registro`, { data });
  expect(r.status()).toBe(200);
  const token = (await r.json()).token;
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.addInitScript(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/diagnostico');
  await expect(page.getByRole('heading', { name: 'Diagnóstico' })).toBeVisible();
  await page.getByRole('button', { name: 'Copiar diagnóstico' }).click();
  await expect(page.getByRole('status')).toHaveText('Diagnóstico copiado.');
  const copiado = await page.evaluate(() => navigator.clipboard.readText());
  expect(copiado).toContain('Integridade do banco: Íntegro');
  expect(copiado).toContain('Ambiente fiscal: homologacao');
  expect(copiado.includes(token)).toBe(false);
});
