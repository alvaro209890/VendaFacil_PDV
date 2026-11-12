import { test, expect } from '@playwright/test';

// Fixture sintética de homologação: chave de 44 dígitos só para medir a quebra
// de linha do DANFE NFC-e; nenhuma nota é emitida.
const chave = '51261112345678000195650010000000021342497391';

for (const largura of [58, 80]) {
  test(`F6.9: DANFE ${largura} mm não parte bloco de 4 dígitos da chave`, async ({ page }) => {
    await page.goto('/login');
    const blocos = await page.evaluate(async ({ chave, largura }) => {
      const { imprimirRecibo } = await import('/src/lib/recibo.ts');
      const pronto = new Promise<string[][]>(resolve => {
        const anexar = Element.prototype.appendChild;
        Element.prototype.appendChild = function <T extends Node>(node: T): T {
          const inserido = anexar.call(this, node) as T;
          if (node instanceof HTMLIFrameElement) {
            const win = node.contentWindow!;
            win.print = () => {
              const div = Array.from(win.document.querySelectorAll('div'))
                .find(el => el.textContent?.replace(/\s/g, '') === chave)!;
              const texto = div.firstChild as Text;
              const linhas: string[][] = [];
              let topo = -1;
              for (let i = 0; i < texto.length; i += 5) {
                const faixa = win.document.createRange();
                faixa.setStart(texto, i);
                faixa.setEnd(texto, i + 4);
                const caixas = Array.from(faixa.getClientRects()).filter(r => r.width > 0);
                const bloco = texto.data.slice(i, i + 4);
                if (caixas.length !== 1) linhas.push([`partido:${bloco}`]);
                else if (caixas[0].top !== topo) { topo = caixas[0].top; linhas.push([bloco]); }
                else linhas[linhas.length - 1].push(bloco);
              }
              resolve(linhas);
              win.dispatchEvent(new win.Event('afterprint'));
            };
          }
          return inserido;
        };
      });
      imprimirRecibo({
        itens: [{ nome: 'Açúcar de teste', qtd: 1, preco: 10, subtotal: 10, unidade: 'UN' }],
        subtotal: 10, desconto: 0, total: 10, forma: 'dinheiro', recebido: 10, troco: 0,
        loja: { nome: 'Mercearia de teste' },
        nota: { status: 'autorizada', chave, ambiente: 'homologacao', protocolo: '151260000000001', numero: 2, serie: 1 },
      }, largura);
      return pronto;
    }, { chave, largura });
    expect(blocos.flat().filter(b => b.startsWith('partido:'))).toEqual([]);
    expect(blocos.flat().join('')).toBe(chave);
    expect(blocos.length).toBeGreaterThan(1); // a chave de 54 caracteres não cabe numa linha só
  });
}
