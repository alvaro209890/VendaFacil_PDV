import { test, expect } from '@playwright/test';

// A venda comercial é real (backend E2E descartável). Só o documento fiscal é
// uma fixture de navegador: nenhuma nota é emitida nem cancelada na SEFAZ.
const api = 'http://127.0.0.1:3121';
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };

test('F7.5: nota autorizada pode ser cancelada pela tela de Vendas', async ({ page, request }) => {
  let login = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (login.status() === 401) login = await request.post(`${api}/api/auth/registro`, { data: fixture });
  expect(login.status()).toBe(200);
  const token = (await login.json()).token;
  const headers = { Authorization: `Bearer ${token}` };
  const codigo = `NFCE-${Date.now()}`;
  const produto = await request.post(`${api}/api/produtos`, {
    headers, data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 3 },
  });
  expect(produto.status()).toBe(201);
  const venda = await request.post(`${api}/api/vendas/checkout`, {
    headers, data: { itens: [{ produto_id: (await produto.json()).produto.id, quantidade: 1 }], forma_pagamento: 'dinheiro' },
  });
  expect(venda.status()).toBe(201);
  const vendaId = (await venda.json()).venda.id;

  const nota = {
    id: 9001, venda_id: vendaId, ref: 'fixture-ui', modelo: '65', numero: 7, serie: 1,
    ambiente: 'homologacao', status: 'autorizada', chave: '51261112345678000195650010000000071000000070',
    protocolo: '151260000000007', mensagem: null, motivo_rejeicao: null,
    xml_url: null, danfe_url: null, qrcode_url: null,
  };
  await page.route(`**/api/fiscal/nfce/venda/${vendaId}`, route => route.fulfill({ json: { nota } }));
  const pedidos: unknown[] = [];
  await page.route('**/api/fiscal/nfce/9001/cancelar', async route => {
    pedidos.push(route.request().postDataJSON());
    await route.fulfill({ json: { nota: { ...nota, status: 'cancelada' } } });
  });

  await page.goto('/login');
  await page.evaluate(t => localStorage.setItem('vf_token', t), token);
  await page.goto('/vendas');
  await page.getByRole('row').filter({ has: page.getByRole('cell', { name: String(vendaId), exact: true }) })
    .getByRole('button', { name: 'Detalhes' }).click();
  await expect(page.getByText(nota.chave)).toBeVisible();

  const justificativa = 'Cliente desistiu da compra no balcão';
  page.once('dialog', dialog => dialog.accept(justificativa));
  await page.getByRole('button', { name: 'Cancelar NFC-e' }).click();
  await expect.poll(() => pedidos).toEqual([{ justificativa }]);
  await expect(page.getByText('cancelada', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancelar NFC-e' })).toHaveCount(0);
});
