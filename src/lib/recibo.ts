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
  unidade?: string;
  codigo?: string;
}

export interface ReciboNota {
  numero?: number | null;
  serie?: number | null;
  chave?: string | null;
  protocolo?: string | null;
  qrcode_base64?: string | null;
  status?: string | null;   // "autorizada" | "contingencia" | ...
  cpf?: string | null;      // CPF/CNPJ do consumidor, se informado
  xml?: string | null;
  ambiente?: string | null;
}

export interface ReciboData {
  loja: { nome: string; cnpj?: string; endereco?: string; ie?: string };
  itens: ReciboItem[];
  subtotal: number;
  desconto: number;
  total: number;
  forma: string;
  recebido?: number;
  troco?: number;
  vendaId?: number | string;
  data?: string; // ISO; usa agora se ausente
  nota?: ReciboNota | null;  // NFC-e autorizada → imprime bloco fiscal + QR
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
  // O XML guarda o emitente/consumidor da emissão, mesmo após mudar o cadastro.
  const documento = d.nota?.xml ? new DOMParser().parseFromString(d.nota.xml, "application/xml") : null;
  const xml = documento?.getElementsByTagName("parsererror").length ? null : documento;
  const no = (nome: string, base: Document | Element | null = xml) => base?.getElementsByTagNameNS("*", nome)[0] || null;
  const texto = (nome: string, base: Document | Element | null = xml): string => no(nome, base)?.textContent?.trim() || "";
  const emit = no("emit"), endereco = no("enderEmit", emit), dest = no("dest"), prot = no("infProt");
  const nomeLoja = texto("xNome", emit) || d.loja.nome;
  const cnpjLoja = texto("CNPJ", emit) || d.loja.cnpj;
  const ieLoja = texto("IE", emit) || d.loja.ie;
  const enderecoLoja = endereco ? ['xLgr', 'nro', 'xCpl', 'xBairro', 'xMun', 'UF', 'CEP'].map(n => texto(n, endereco)).filter(Boolean).join(', ') : d.loja.endereco;
  const ambiente = texto("tpAmb") || d.nota?.ambiente;
  const homologacao = ambiente === "2" || ambiente === "homologacao";
  const protocolo = texto("nProt", prot) || d.nota?.protocolo;
  const consumidorDoc = texto("CPF", dest) || texto("CNPJ", dest) || d.nota?.cpf;
  const totalTributos = texto("vTotTrib", no("ICMSTot"));
  const complemento = texto("infCpl");
  const dt = new Date(texto("dhEmi") || d.data || Date.now()).toLocaleString("pt-BR", { timeZone: "America/Cuiaba" });
  const linhas = d.itens.map((it) => {
    const nome = esc(it.nome);
    const qtd = Number(it.qtd || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
    const calc = `${qtd} ${esc(it.unidade || "UN")} x ${moeda(it.preco)}`;
    return `<div class="item"><div class="nm">${it.codigo ? esc(it.codigo) + " — " : ""}${nome}</div><div class="ln"><span>${calc}</span><span>${moeda(it.subtotal)}</span></div></div>`;
  }).join("");

  const cnpj = cnpjLoja ? `<div class="c">CNPJ: ${esc(cnpjLoja)}</div>` : "";
  const ie = ieLoja ? `<div class="c">IE: ${esc(ieLoja)}</div>` : "";
  const end = enderecoLoja ? `<div class="c">${esc(enderecoLoja)}</div>` : "";
  const desc = d.desconto > 0 ? `<div class="ln"><span>Desconto</span><span>-${moeda(d.desconto)}</span></div>` : "";
  const dinheiro = d.forma === "dinheiro" && d.recebido !== undefined
    ? `<div class="ln"><span>Recebido</span><span>${moeda(d.recebido)}</span></div>
       <div class="ln"><span>Troco</span><span>${moeda(d.troco || 0)}</span></div>`
    : "";

  // Bloco fiscal (DANFE NFC-e): identificação, consumidor, chave, protocolo, QR
  // de consulta e tributos (Lei 12.741). Em contingência, avisa que a autorização
  // ainda será transmitida automaticamente à SEFAZ.
  const temNota = !!(d.nota && d.nota.chave);
  const contingencia = d.nota?.status === "contingencia";
  let fiscal = "";
  if (temNota && d.nota) {
    const chave = esc(d.nota.chave!).replace(/(.{4})/g, "$1 ").trim();
    const qrBase64 = d.nota.qrcode_base64 || "";
    const qr = /^iVBORw0KGgo[A-Za-z0-9+/]*={0,2}$/.test(qrBase64) && qrBase64.length % 4 === 0
      ? `<div class="c" style="margin-top:4px"><img src="data:image/png;base64,${qrBase64}" style="width:${larguraMm === 58 ? 40 : 50}mm;height:auto" /></div>`
      : "";
    const consumidor = consumidorDoc
      ? `<div class="c">CONSUMIDOR: ${esc(consumidorDoc)}</div>`
      : `<div class="c">CONSUMIDOR NAO IDENTIFICADO</div>`;
    fiscal = `<hr>
      <div class="c b">DANFE NFC-e — Documento Auxiliar da NFC-e</div>
      ${homologacao ? '<div class="c b">EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO — SEM VALOR FISCAL</div>' : ""}
      ${d.nota.status === "cancelada" ? '<div class="c b">NOTA CANCELADA</div>' : ""}
      ${contingencia ? `<div class="c b">EMITIDA EM CONTINGENCIA</div><div class="c b">Pendente de autorizacao</div>` : ""}
      <div class="c">NFC-e no ${esc(texto("nNF") || String(d.nota.numero ?? "-"))} serie ${esc(texto("serie") || String(d.nota.serie ?? "-"))}</div>
      ${consumidor}
      ${protocolo ? `<div class="c">Protocolo: ${esc(String(protocolo))}</div>` : ""}
      ${texto("dhRecbto", prot) ? `<div class="c">Autorização: ${esc(new Date(texto("dhRecbto", prot)).toLocaleString("pt-BR", { timeZone: "America/Cuiaba" }))}</div>` : ""}
      <div class="c" style="font-size:.85em;margin-top:2px">Chave de acesso</div>
      <div class="c" style="font-size:.8em;word-break:break-all">${chave}</div>
      ${qr}
      <div class="c" style="font-size:.8em;margin-top:2px;overflow-wrap:anywhere">Consulte pela chave de acesso em<br>${esc(texto("urlChave") || "www.sefaz.mt.gov.br/nfce/consultanfce")}</div>
      ${contingencia ? `<div class="c" style="font-size:.8em;margin-top:2px">Transmitir assim que a conexão voltar, até o primeiro dia útil seguinte em MT. Mantenha o programa aberto.</div>` : ""}
      <div class="c" style="font-size:.8em;margin-top:2px">${totalTributos !== "" && Number.isFinite(Number(totalTributos)) ? `Tributos aproximados: R$ ${moeda(Number(totalTributos))} (Lei 12.741/2012).` : "Tributos aproximados não informados."}</div>
      ${complemento ? `<div class="c" style="font-size:.8em">${esc(complemento)}</div>` : ""}`;
  }

  const corpo = (via: string) => `
  ${via ? `<div class="c b" style="font-size:.85em">${via}</div>` : ""}
  <div class="c b big">${esc(nomeLoja || "VendaFácil PDV")}</div>
  ${cnpj}${ie}${end}
  <hr>
  ${temNota ? "" : '<div class="c b">CUPOM NÃO FISCAL</div>'}
  <div class="ln"><span>${dt}</span><span>${d.vendaId ? "#" + esc(String(d.vendaId)) : ""}</span></div>
  <hr>
  ${linhas}
  <hr>
  <div class="ln"><span>Subtotal</span><span>${moeda(d.subtotal)}</span></div>
  ${desc}
  <div class="ln"><span>Quantidade de itens</span><span>${d.itens.length}</span></div>
  <div class="ln tot"><span>TOTAL</span><span>R$ ${moeda(d.total)}</span></div>
  <div class="ln"><span>Pagamento</span><span>${esc(String(FORMA_LABEL[d.forma] || d.forma))}</span></div>
  ${dinheiro}
  ${fiscal}
  <hr>
  <div class="rod">Obrigado pela preferência!</div>
  ${d.nota && d.nota.chave ? "" : '<div class="rod" style="font-size:.85em">*Este documento não é fiscal*</div>'}`;

  // Contingência offline: os Padrões Técnicos da NFC-e mandam imprimir o DANFE
  // em DUAS vias — uma para o consumidor, outra fica no estabelecimento até a
  // autorização ser obtida.
  const conteudo = contingencia
    ? corpo("VIA DO CONSUMIDOR") +
      '<div class="corte">--------- corte aqui ---------</div>' +
      corpo("VIA DO ESTABELECIMENTO (guardar)")
    : corpo("");

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
  .corte { text-align: center; margin: 8px 0; font-size: .8em; }
</style></head><body>${conteudo}</body></html>`;
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
