// Exportação do extrato do cliente: PDF A4 (gerador próprio, sem dependência)
// e CSV para abrir no Excel / LibreOffice.
//
// O PDF é montado com a fonte base-14 Courier (largura fixa): isso permite
// alinhar valores por coluna sem medir texto, e mantém o arquivo pequeno.

import type { CompraExtrato, ExtratoCliente } from "./api";
import { rotuloForma } from "./rotulos";

export interface LojaExtrato {
  nome?: string;
  razao?: string;
  cnpj?: string;
  endereco?: string;
  ie?: string;
}

export interface PdfLinha {
  texto: string;
  negrito?: boolean;
  tamanho?: number;
}

const MOEDA = (v: number | null | undefined) =>
  (v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Data e hora no fuso da loja (America/Cuiaba). */
export function dataHora(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    timeZone: "America/Cuiaba",
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/** AAAA-MM-DD do dia de hoje no fuso da loja. */
export function hojeCuiaba(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Cuiaba", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date());
}

/** Soma (ou subtrai) dias de uma data AAAA-MM-DD. */
export function somaDias(iso: string, dias: number): string {
  const [a, m, d] = iso.split("-").map(Number);
  const base = new Date(Date.UTC(a, m - 1, d));
  base.setUTCDate(base.getUTCDate() + dias);
  return base.toISOString().slice(0, 10);
}

/** AAAA-MM-DD -> DD/MM/AAAA. */
export function dataBr(iso: string): string {
  const [a, m, d] = iso.split("-");
  return d && m && a ? `${d}/${m}/${a}` : iso;
}

function arquivo(nome: string): string {
  const limpo = (nome || "cliente")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase();
  return limpo || "cliente";
}

function baixar(nomeArquivo: string, conteudo: string | Uint8Array, tipo: string) {
  const dados: BlobPart = typeof conteudo === "string"
    ? conteudo
    : (conteudo.buffer.slice(conteudo.byteOffset, conteudo.byteOffset + conteudo.byteLength) as ArrayBuffer);
  const blob = new Blob([dados], { type: tipo });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeArquivo;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

// ── CSV ──────────────────────────────────────────────────────────────────────

function campoCsv(valor: string | number | null | undefined): string {
  const texto = valor === null || valor === undefined ? "" : String(valor);
  return /[";\n\r]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

/** CSV com ; e vírgula decimal (padrão do Excel em português), uma linha por item. */
export function extratoParaCsv(extrato: ExtratoCliente): string {
  const linhas: string[] = [];
  linhas.push([
    "Data", "Hora", "Venda", "Situação da venda", "Forma", "Produto", "Qtd", "Unidade",
    "Preço unitário", "Subtotal", "Total da venda", "Fiado (situação)", "Fiado em aberto",
  ].join(";"));

  for (const compra of extrato.compras) {
    const data = new Date(compra.criado_em);
    const dia = data.toLocaleDateString("pt-BR", { timeZone: "America/Cuiaba" });
    const hora = data.toLocaleTimeString("pt-BR", {
      timeZone: "America/Cuiaba", hour: "2-digit", minute: "2-digit",
    });
    const itens = compra.itens?.length ? compra.itens : [null];
    for (const item of itens) {
      linhas.push([
        campoCsv(dia), campoCsv(hora), campoCsv(compra.id), campoCsv(compra.status),
        campoCsv(rotuloForma(compra.forma_pagamento)),
        campoCsv(item?.nome_produto || "(sem itens)"),
        campoCsv(item ? Number(item.quantidade || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 }) : ""),
        campoCsv(item?.unidade_venda || ""),
        campoCsv(item ? MOEDA(item.preco_unitario) : ""),
        campoCsv(item ? MOEDA(item.subtotal) : ""),
        campoCsv(MOEDA(compra.total)),
        campoCsv(compra.conta ? compra.conta.status : ""),
        campoCsv(compra.conta ? MOEDA(compra.conta.valor_pendente) : ""),
      ].join(";"));
    }
  }

  // \uFEFF = BOM: o Excel abre em UTF-8 e mostra os acentos direito.
  return "\uFEFF" + linhas.join("\r\n") + "\r\n";
}

export function baixarCsvExtrato(extrato: ExtratoCliente) {
  const csv = extratoParaCsv(extrato);
  baixar(`extrato-${arquivo(extrato.cliente.nome)}-${hojeCuiaba()}.csv`, csv, "text/csv;charset=utf-8");
}

// ── PDF ──────────────────────────────────────────────────────────────────────

const LARGURA_A4 = 595.28;
const ALTURA_A4 = 841.89;
const MARGEM = 36;
const LARGURA_LINHA = 92; // Courier 9pt: 92 * 5.4pt = 497pt (cabe nos 523pt úteis)

function escaparPdf(texto: string): string {
  let saida = "";
  for (const ch of texto) {
    const codigo = ch.charCodeAt(0);
    if (codigo < 32) saida += " ";
    else if (codigo <= 255) saida += ch;
    else saida += "?";
  }
  return saida.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function bytesLatin1(texto: string): Uint8Array {
  const bytes = new Uint8Array(texto.length);
  for (let i = 0; i < texto.length; i += 1) bytes[i] = texto.charCodeAt(i) & 0xff;
  return bytes;
}

function corta(texto: string, limite: number): string {
  const limpo = String(texto || "").replace(/\s+/g, " ").trim();
  return limpo.length > limite ? limpo.slice(0, limite - 3) + "..." : limpo.padEnd(limite);
}

function linhasDoExtrato(extrato: ExtratoCliente, loja: LojaExtrato): PdfLinha[] {
  const linhas: PdfLinha[] = [];
  const push = (texto = "", extra: Omit<PdfLinha, "texto"> = {}) => linhas.push({ texto, ...extra });
  const regra = "-".repeat(LARGURA_LINHA);

  push("EXTRATO DE COMPRAS", { negrito: true, tamanho: 12 });
  if (loja.nome || loja.razao) push(loja.nome || loja.razao || "", { negrito: true, tamanho: 10 });
  const documento = [loja.cnpj ? `CNPJ ${loja.cnpj}` : "", loja.ie ? `IE ${loja.ie}` : ""].filter(Boolean).join("   ");
  if (documento) push(documento, { tamanho: 8.5 });
  if (loja.endereco) push(loja.endereco, { tamanho: 8.5 });
  push("");
  push(regra, { tamanho: 8.5 });
  push(`Cliente: ${extrato.cliente.nome}`);
  if (extrato.cliente.documento) push(`CPF/CNPJ: ${extrato.cliente.documento}`);
  if (extrato.cliente.telefone) push(`Telefone: ${extrato.cliente.telefone}`);
  const periodo = extrato.inicio || extrato.fim
    ? `${extrato.inicio ? dataBr(extrato.inicio) : "início"} a ${extrato.fim ? dataBr(extrato.fim) : dataBr(hojeCuiaba())}`
    : `todas as compras (até ${dataBr(hojeCuiaba())})`;
  push(`Período: ${periodo}`);
  push(`Emitido em: ${dataHora(new Date().toISOString())}`);
  push(regra, { tamanho: 8.5 });
  push(
    `Compras: ${extrato.resumo.compras}   Total: R$ ${MOEDA(extrato.resumo.total)}   ` +
    `Fiado: R$ ${MOEDA(extrato.resumo.fiado_total)}   Em aberto: R$ ${MOEDA(extrato.resumo.fiado_pendente)}`,
    { negrito: true },
  );
  push("=".repeat(LARGURA_LINHA), { tamanho: 8.5 });

  if (!extrato.compras.length) {
    push("");
    push("Nenhuma compra registrada para este cliente no periodo.", { tamanho: 9 });
  }

  for (const compra of extrato.compras) {
    const situacao = compra.status && compra.status !== "concluida" ? `  [${compra.status.toUpperCase()}]` : "";
    push(
      `${dataHora(compra.criado_em)}  Venda #${compra.id}  ${rotuloForma(compra.forma_pagamento)}${situacao}  R$ ${MOEDA(compra.total)}`,
      { negrito: true },
    );
    for (const item of compra.itens || []) {
      const quantidade = Number(item.quantidade || 0);
      const qtd = quantidade.toLocaleString("pt-BR", { maximumFractionDigits: 3 });
      const nome = corta(item.nome_produto, 36);
      push(
        `   ${qtd.padStart(6)} x ${nome} ${MOEDA(item.preco_unitario).padStart(10)} ${MOEDA(item.subtotal).padStart(10)}`,
        { tamanho: 8.5 },
      );
    }
    if (!(compra.itens || []).length) push("   (itens não registrados nesta venda)", { tamanho: 8.5 });
    if (compra.desconto) push(`   Desconto: R$ ${MOEDA(compra.desconto)}`, { tamanho: 8.5 });
    if (compra.conta) {
      push(
        `   Fiado: ${compra.conta.status}   total R$ ${MOEDA(compra.conta.valor_total)}   em aberto R$ ${MOEDA(compra.conta.valor_pendente)}`,
        { tamanho: 8.5 },
      );
    }
    if (compra.nota) {
      push(`   NFC-e ${compra.nota.numero ?? "-"}  ${compra.nota.status || ""}`.trimEnd(), { tamanho: 8.5 });
    }
    push(regra, { tamanho: 8.5 });
  }

  push("");
  push("Documento gerado pelo VendaFacil PDV.", { tamanho: 8 });
  return linhas;
}

/** Gera os bytes de um PDF A4 com o extrato. */
export function gerarPdfExtrato(extrato: ExtratoCliente, loja: LojaExtrato = {}): Uint8Array {
  const linhas = linhasDoExtrato(extrato, loja);

  // Paginação: cada linha ocupa tamanho * 1.45pt; página nova quando falta espaço.
  const paginas: string[][] = [];
  let atual: string[] = [];
  let y = ALTURA_A4 - MARGEM;
  for (const linha of linhas) {
    const tamanho = linha.tamanho ?? 9;
    const altura = tamanho * 1.45;
    if (y - altura < MARGEM) {
      paginas.push(atual);
      atual = [];
      y = ALTURA_A4 - MARGEM;
    }
    atual.push(
      `BT /${linha.negrito ? "F2" : "F1"} ${tamanho} Tf ${MARGEM} ${(y - tamanho).toFixed(2)} Td (${escaparPdf(linha.texto)}) Tj ET`,
    );
    y -= altura;
  }
  paginas.push(atual);

  const objetos: (string | null)[] = [null];
  const filhos: string[] = [];
  const paginasConteudo: { idPagina: number; idConteudo: number; conteudo: string }[] = [];
  let proximo = 5;
  for (const conteudo of paginas) {
    const idPagina = proximo++;
    const idConteudo = proximo++;
    filhos.push(`${idPagina} 0 R`);
    paginasConteudo.push({ idPagina, idConteudo, conteudo: conteudo.join("\n") });
  }

  objetos[1] = "<< /Type /Catalog /Pages 2 0 R >>";
  objetos[2] = `<< /Type /Pages /Kids [${filhos.join(" ")}] /Count ${paginas.length} >>`;
  objetos[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>";
  objetos[4] = "<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>";
  for (const pagina of paginasConteudo) {
    objetos[pagina.idPagina] =
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${LARGURA_A4} ${ALTURA_A4}] ` +
      `/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${pagina.idConteudo} 0 R >>`;
    const corpo = pagina.conteudo + "\n";
    objetos[pagina.idConteudo] =
      `<< /Length ${bytesLatin1(corpo).length} >>\nstream\n${corpo}endstream`;
  }

  const pedacos: Uint8Array[] = [];
  let total = 0;
  const escrever = (valor: string) => {
    const bytes = bytesLatin1(valor);
    pedacos.push(bytes);
    total += bytes.length;
  };

  escrever("%PDF-1.4\n%\u00e2\u00e3\u00cf\u00d3\n");
  const offsets: number[] = [];
  for (let id = 1; id < objetos.length; id += 1) {
    offsets[id] = total;
    escrever(`${id} 0 obj\n${objetos[id] ?? "<< >>"}\nendobj\n`);
  }
  const inicioXref = total;
  let xref = `xref\n0 ${objetos.length}\n0000000000 65535 f \n`;
  for (let id = 1; id < objetos.length; id += 1) {
    xref += `${String(offsets[id]).padStart(10, "0")} 00000 n \n`;
  }
  escrever(xref);
  escrever(`trailer\n<< /Size ${objetos.length} /Root 1 0 R >>\nstartxref\n${inicioXref}\n%%EOF\n`);

  const pdf = new Uint8Array(total);
  let posicao = 0;
  for (const pedaco of pedacos) {
    pdf.set(pedaco, posicao);
    posicao += pedaco.length;
  }
  return pdf;
}

export function baixarPdfExtrato(extrato: ExtratoCliente, loja: LojaExtrato = {}) {
  const pdf = gerarPdfExtrato(extrato, loja);
  baixar(`extrato-${arquivo(extrato.cliente.nome)}-${hojeCuiaba()}.pdf`, pdf, "application/pdf");
}

/** Resumo curto para a tela: "3 compras · Fiado R$ 40,00 em aberto". */
export function resumoCurto(extrato: ExtratoCliente): string {
  const partes = [`${extrato.resumo.compras} ${extrato.resumo.compras === 1 ? "compra" : "compras"}`];
  if (extrato.resumo.fiado_pendente > 0) partes.push(`Fiado em aberto: R$ ${MOEDA(extrato.resumo.fiado_pendente)}`);
  return partes.join(" · ");
}

export type { CompraExtrato };
