import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:3121';
// Credenciais exclusivamente da fixture, num SQLite temporário recém-criado.
const fixture = { usuario: 'e2e-carrinho', nome: 'Teste descartável', senha: 'fixture-e2e-carrinho' };

// Emitente sintético: só mede o cabeçalho impresso; nenhuma nota é emitida.
const xml = `<?xml version="1.0"?><NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe><ide><nNF>7</nNF><serie>1</serie><tpAmb>2</tpAmb></ide>
<emit><CNPJ>12345678000195</CNPJ><xNome>FULANO DE TAL</xNome><xFant>Mercearia Teste</xFant><enderEmit><xLgr>R UM</xLgr><nro>1</nro></enderEmit><IE>123</IE></emit></infNFe></NFe>`;

async function cabecalho(page: import('@playwright/test').Page, comNota: boolean) {
  await page.goto('/login');
  return page.evaluate(async ({ xml, comNota }) => {
    const { imprimirRecibo } = await import('/src/lib/recibo.ts');
    const pronto = new Promise<string[]>(resolve => {
      const anexar = Element.prototype.appendChild;
      Element.prototype.appendChild = function <T extends Node>(node: T): T {
        const inserido = anexar.call(this, node) as T;
        if (node instanceof HTMLIFrameElement) {
          const win = node.contentWindow!;
          win.print = () => {
            const linhas = Array.from(win.document.querySelectorAll('div.c')).slice(0, 3).map(d => d.textContent!.trim());
            resolve(linhas);
            win.dispatchEvent(new win.Event('afterprint'));
          };
        }
        return inserido;
      };
    });
    imprimirRecibo({
      itens: [{ nome: 'Item', qtd: 1, preco: 1, subtotal: 1, unidade: 'UN' }],
      subtotal: 1, desconto: 0, total: 1, forma: 'dinheiro', recebido: 1, troco: 0,
      loja: { nome: 'Mercearia Teste', razao: 'FULANO DE TAL', cnpj: '12345678000195' },
      nota: comNota ? { status: 'autorizada', chave: '51261112345678000195650010000000071342497391', ambiente: 'homologacao', numero: 7, serie: 1, xml } : null,
    }, 80);
    return pronto;
  }, { xml, comNota });
}

for (const comNota of [false, true]) {
  test(`comprovante ${comNota ? 'com NFC-e' : 'não fiscal'}: nome fantasia em destaque e razão social abaixo`, async ({ page }) => {
    const linhas = await cabecalho(page, comNota);
    expect(linhas[0]).toBe('Mercearia Teste');
    expect(linhas[1]).toBe('FULANO DE TAL');
    expect(linhas[2]).toContain('12345678000195');
  });
}

test('Imprimir recibo ao finalizar vem marcado ao abrir o PDV', async ({ page, request }) => {
  let registro = await request.post(`${api}/api/auth/login`, { data: fixture });
  if (registro.status() === 401) registro = await request.post(`${api}/api/auth/registro`, { data: fixture });
  const token = (await registro.json()).token;
  const codigo = `E2E-RECIBO-${Date.now()}`;
  const r = await request.post(`${api}/api/produtos`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { nome: codigo, codigo_barras: codigo, preco_venda: 5, preco_custo: 2, estoque: 5 },
  });
  expect(r.status()).toBe(201);
  await page.goto('/login');
  await page.evaluate(t => { localStorage.setItem('vf_token', t); localStorage.setItem('recibo_auto', '0'); }, token);
  await page.goto('/pdv');
  const busca = page.getByPlaceholder(/Bipe o código/);
  await busca.fill(codigo);
  await busca.press('Enter');
  await expect(page.getByRole('checkbox', { name: /Imprimir recibo ao finalizar/ })).toBeChecked();
});
