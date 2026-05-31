// Impressão de cupom (recibo não-fiscal) para impressoras térmicas (58/80mm).
//
// Abordagem: monta um HTML estreito (largura do rolo) com fonte monoespaçada e
// chama print() num iframe oculto. O driver da impressora térmica instalado no
// Windows recebe pelo diálogo de impressão normal — funciona no .exe (navegador).

export interface ReciboItem {
  nome: string;
  qtd: number;
  preco: number;
  subtotal: number;
}

export interface ReciboData {
  loja: { nome: string; cnpj?: string; endereco?: string };
  itens: ReciboItem[];
  subtotal: number;
  desconto: number;
  total: number;
  forma: string;
  vendaId?: number | string;
  data?: string; // ISO; usa agora se ausente
}

const FORMA_LABEL: Record<string, string> = {
  dinheiro: "Dinheiro", pix: "PIX", debito: "Débito", credito: "Crédito", fiado: "Fiado",
};

const moeda = (v: number) => (v || 0).toFixed(2).replace(".", ",");

function esc(s: string): string {
  return (s || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c] as string));
}

/** Largura preferida do rolo em mm (58 ou 80), guardada no navegador. */
export function getLarguraRecibo(): 58 | 80 {
  return localStorage.getItem("recibo_largura") === "58" ? 58 : 80;
}
export function setLarguraRecibo(mm: 58 | 80) {
  localStorage.setItem("recibo_largura", String(mm));
}

function montarHtml(d: ReciboData, larguraMm: number): string {
  const dt = new Date(d.data || Date.now()).toLocaleString("pt-BR");
  const linhas = d.itens.map((it) => {
    const nome = esc(it.nome);
    const calc = `${it.qtd} x ${moeda(it.preco)}`;
    return `<div class="item"><div class="nm">${nome}</div><div class="ln"><span>${calc}</span><span>${moeda(it.subtotal)}</span></div></div>`;
  }).join("");

  const cnpj = d.loja.cnpj ? `<div class="c">CNPJ: ${esc(d.loja.cnpj)}</div>` : "";
  const end = d.loja.endereco ? `<div class="c">${esc(d.loja.endereco)}</div>` : "";
  const desc = d.desconto > 0 ? `<div class="ln"><span>Desconto</span><span>-${moeda(d.desconto)}</span></div>` : "";

  return `<!doctype html><html><head><meta charset="utf-8"><title>Recibo</title>
<style>
  @page { size: ${larguraMm}mm auto; margin: 0; }
  * { box-sizing: border-box; }
  body { width: ${larguraMm}mm; margin: 0; padding: 3mm; font-family: 'Courier New', monospace;
         font-size: ${larguraMm === 58 ? "10px" : "12px"}; color: #000; line-height: 1.35; }
  .c { text-align: center; }
  .b { font-weight: bold; }
  .big { font-size: 1.2em; }
  hr { border: none; border-top: 1px dashed #000; margin: 4px 0; }
  .ln { display: flex; justify-content: space-between; gap: 6px; }
  .item { margin: 2px 0; }
  .item .nm { word-break: break-word; }
  .item .ln span:first-child { color: #000; }
  .tot { font-weight: bold; font-size: 1.25em; }
  .rod { text-align: center; margin-top: 6px; }
</style></head><body>
  <div class="c b big">${esc(d.loja.nome || "VendaFácil PDV")}</div>
  ${cnpj}${end}
  <hr>
  <div class="c b">CUPOM NÃO FISCAL</div>
  <div class="ln"><span>${dt}</span><span>${d.vendaId ? "#" + d.vendaId : ""}</span></div>
  <hr>
  ${linhas}
  <hr>
  <div class="ln"><span>Subtotal</span><span>${moeda(d.subtotal)}</span></div>
  ${desc}
  <div class="ln tot"><span>TOTAL</span><span>R$ ${moeda(d.total)}</span></div>
  <div class="ln"><span>Pagamento</span><span>${FORMA_LABEL[d.forma] || d.forma}</span></div>
  <hr>
  <div class="rod">Obrigado pela preferência!</div>
  <div class="rod" style="font-size:.85em">*Este documento não é fiscal*</div>
</body></html>`;
}

/** Monta o cupom e dispara a impressão num iframe oculto. */
export function imprimirRecibo(d: ReciboData, larguraMm: number = getLarguraRecibo()): void {
  const html = montarHtml(d, larguraMm);
  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  document.body.appendChild(iframe);
  const doc = iframe.contentWindow?.document;
  if (!doc) { document.body.removeChild(iframe); return; }
  doc.open();
  doc.write(html);
  doc.close();
  const win = iframe.contentWindow!;
  const limpar = () => setTimeout(() => { try { document.body.removeChild(iframe); } catch { /* ok */ } }, 1000);
  win.onafterprint = limpar;
  // pequeno atraso para o layout assentar antes de imprimir
  setTimeout(() => { win.focus(); win.print(); limpar(); }, 250);
}
