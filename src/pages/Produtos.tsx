import { useState, useEffect, useCallback, useLayoutEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import {
  listarProdutos,
  criarProduto,
  atualizarProduto,
  desativarProduto,
  listarCategorias,
  importarXmlPreview,
  importarXmlConfirmar,
  entradaEstoque,
  ajustarEstoque,
  listarMovimentacoes,
} from "../lib/api";
import type {
  Produto, ProdutoInput, Categoria, CamposFiscais, PreviewXml, ItemConfirmarXml, Movimentacao,
} from "../lib/api";
import { estoqueBalcao, embalagemDoNome, textoComparacao } from "../lib/embalagem";
import { lerNumeroPtBr } from "../lib/numeros";

// Item da importação com flags editáveis na tela.
type ItemImport = ItemConfirmarXml & {
  acao: "atualizar" | "criar";
  estoque_atual: number;
  incluir: boolean;
  valor_unitario_xml?: number;
  valor_unitario_nota?: number;
  despesas_unitarias?: number;
  perguntar_embalagem?: boolean;
  fator_entrada?: number;
  // Sinais que o backend manda explicando por que este item pode ser caixa.
  embalagem_sugerida?: string;
  sinais_embalagem?: string[];
  aviso_unidade?: string;
  fator_sugerido?: number;
  // Decisão do operador para produto novo:
  // "unidade" = comprou em caixa mas vende só unidade (estoque em UN);
  // "aberta"  = vende a caixa fechada e a unidade, com preços diferentes;
  // "fechada" = só vende a embalagem fechada (estoque na unidade da nota).
  modo_venda?: "unidade" | "aberta" | "fechada";
  // Códigos como vieram na nota (cEAN e cEANTrib diferente), para redistribuir
  // entre caixa e unidade quando o operador muda a forma de venda.
  ean_nota?: string;
  ean_trib_nota?: string;
  // Quantidades de cada linha da nota que foram juntadas neste item (mesmo
  // código de barras repetido na NF, ex.: 1 + 7 da mesma batata palha).
  linhas_nota?: number[];
  // Produto simples (nota em UN): a pergunta "Como vende?" fica recolhida
  // até o operador pedir para trocar.
  mostrar_modo?: boolean;
};

/** Junta linhas da nota com o mesmo código de barras (a distribuidora repete o
 * produto quando muda o desconto). Na tela vira um item só; o custo fica a
 * média ponderada pela quantidade. Sem código válido, nada é juntado. */
function juntarRepetidos(itens: ItemImport[]): ItemImport[] {
  const saida: ItemImport[] = [];
  const posicao = new Map<string, number>();
  for (const it of itens) {
    const codigo = (it.ean_nota || "").trim();
    const chave = /^\d{8,14}$/.test(codigo)
      ? `${codigo}|${it.unidade_xml}|${it.produto_id ?? "novo"}|${it.quantidade_por_embalagem}`
      : "";
    const ja = chave ? posicao.get(chave) : undefined;
    if (ja === undefined) {
      if (chave) posicao.set(chave, saida.length);
      saida.push({ ...it });
      continue;
    }
    const a = saida[ja];
    const qa = Number(a.quantidade_xml || 0);
    const qb = Number(it.quantidade_xml || 0);
    const q = qa + qb;
    const media = (va?: number, vb?: number) =>
      va === undefined || vb === undefined || !(q > 0) ? va : Number(((va * qa + vb * qb) / q).toFixed(4));
    a.valor_unitario_xml = media(a.valor_unitario_xml, it.valor_unitario_xml);
    a.valor_unitario_nota = media(a.valor_unitario_nota, it.valor_unitario_nota);
    a.preco_custo = media(a.preco_custo, it.preco_custo) ?? a.preco_custo;
    if (a.valor_unitario_xml !== undefined && a.valor_unitario_nota !== undefined) {
      a.despesas_unitarias = Number((a.valor_unitario_xml - a.valor_unitario_nota).toFixed(4));
    }
    a.linhas_nota = [...(a.linhas_nota || [qa]), qb];
    a.quantidade_xml = q;
    a.quantidade = Number((Number(a.quantidade || 0) + Number(it.quantidade || 0)).toFixed(4));
    if (a.acao === "criar") a.preco_venda = Number((a.preco_custo * 1.3).toFixed(2));
  }
  return saida;
}

/** Caixa + unidade: quem é o código da caixa e quem é o da unidade.
 * Com dois códigos na nota, cEAN = caixa e cEANTrib = unidade (a unidade tributável
 * é UN). Com um só: nota em unidades soltas → é o da unidade; em caixas → da caixa. */
function codigosPadrao(it: ItemImport): { codigo_barras: string; codigo_barras_unidade: string } {
  const ean = it.ean_nota || "";
  const trib = it.ean_trib_nota || "";
  if (!it.confirmar_abertura || trib) return { codigo_barras: ean, codigo_barras_unidade: trib };
  return it.nota_em_embalagem ? { codigo_barras: ean, codigo_barras_unidade: "" } : { codigo_barras: "", codigo_barras_unidade: ean };
}

// Rótulos que o operador lê na tela e nas mensagens de erro (e o aria-label
// "<rótulo> do item N" de cada campo).
const CAMPOS_NUMEROS_XML = {
  quantidade_xml: "Quantidade na nota", quantidade_por_embalagem: "Unidades por embalagem",
  quantidade: "Entra no estoque", preco_custo: "Custo por unidade", preco_venda: "Preço de venda",
  preco_embalagem: "Preço da embalagem", preco_unidade: "Preço da unidade",
} as const;
type CampoNumeroXml = keyof typeof CAMPOS_NUMEROS_XML;
type Mensagem = { tipo: "ok" | "erro"; texto: string };
const CHECKBOX_IMPORTACAO = "h-5 w-5 shrink-0 cursor-pointer accent-brand-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-400 disabled:cursor-not-allowed";

function numeroXmlValido(campo: CampoNumeroXml, valor: number): boolean {
  if (!Number.isFinite(valor)) return false;
  if (campo === "quantidade_por_embalagem") return valor >= 0.0001;
  if (campo === "quantidade_xml" || campo === "quantidade") return valor > 0;
  return valor >= 0;
}

const FISCAL_VAZIO: CamposFiscais = {
  ncm: "", cest: "", cfop: "5102", origem: "0", unidade_tributavel: "",
  cst_csosn: "102", cst_pis: "07", cst_cofins: "07",
};

const UNIDADES = ["UN", "KG", "G", "LT", "ML", "CX", "FD", "PCT", "SC"];
const normUn = (v: string, fallback = "UN") => (v || fallback).trim().toUpperCase() || fallback;
const fatorSeguro = (v: number | string | undefined) => {
  if (typeof v === "number") return Number.isFinite(v) && v > 0 ? Math.max(v, 0.0001) : 1;
  if (!v) return 1;
  const parsed = lerNumeroPtBr(String(v));
  return parsed !== null && parsed > 0 ? Math.max(parsed, 0.0001) : 1;
};
const fmtQtd = (v: number) => Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
const fmtReais = (v: number) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/** O item tem cara de caixa/fardo e merece a pergunta de embalagem aberta. */
function itemDeEmbalagem(it: ItemImport): boolean {
  return (it.unidade_xml || "UN") !== "UN" || !!it.sinais_embalagem?.length
    || (it.fator_sugerido || 0) > 1 || !!it.confirmar_abertura || it.modo_venda === "fechada";
}

/** Margem sobre o custo, em %, ou null quando não dá para calcular. */
function margemSobreCusto(custo: number, venda: number): number | null {
  if (!(custo > 0) || !(venda > 0)) return null;
  return Math.round(((venda / custo) - 1) * 100);
}

/** Fator da nota para o estoque, conforme a decisão do operador.
 * "fechada" nunca multiplica; "unidade"/"aberta" multiplicam quando a nota veio
 * em embalagem (CX/FD) ou quando o operador disse que cada unidade é uma caixa. */
function fatorDoModo(it: ItemImport): number {
  const qtdEmb = fatorSeguro(it.quantidade_por_embalagem);
  if (it.modo_venda === "fechada") return 1;
  const notaEmEmbalagem = it.nota_em_embalagem === undefined || it.nota_em_embalagem === null
    ? (it.unidade_xml || "UN") !== "UN"
    : !!it.nota_em_embalagem;
  return notaEmEmbalagem ? qtdEmb : 1;
}

/** Campo numérico que a tela deixa editar — o validador só olha esses.
 * Antes ele varria também campo desabilitado e recusava a importação inteira
 * por um valor que o operador nem podia corrigir. */
function campoAtivo(it: ItemImport, campo: CampoNumeroXml): boolean {
  if (campo === "quantidade_xml") return true;
  if (campo === "preco_venda") return it.acao === "criar" && !it.confirmar_abertura;
  if (campo === "quantidade_por_embalagem") return !it.vende_por_unidade;
  if (campo === "quantidade" && it.modo_venda === "fechada") return true;
  if (campo === "quantidade") return !(it.vende_por_unidade || it.confirmar_abertura || it.unidade_xml === "UN");
  if (campo === "preco_custo") return !(it.vende_por_unidade || it.confirmar_abertura || (it.acao === "atualizar" && it.unidade === "UN"));
  if (campo === "preco_embalagem" || campo === "preco_unidade") return !!it.confirmar_abertura;
  return true;
}
const fmtData = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
};
const ORIGEM_LABEL: Record<string, string> = {
  manual: "Entrada manual", xml: "Entrada (XML)", venda: "Venda",
  perda: "Perda", quebra: "Quebra", inventario: "Inventário",
};

export default function ProdutosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const apenasAlerta = searchParams.get("estoque") === "alerta";
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const produtosExibidos = apenasAlerta
    ? produtos.filter((p) => p.ativo && p.estoque <= p.estoque_minimo)
    : produtos;
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [editando, setEditando] = useState<Produto | null>(null);
  const [novo, setNovo] = useState(false);
  const [msg, setMsg] = useState<Mensagem | null>(null);

  const [vendePorUnidade, setVendePorUnidade] = useState(false);
  const [precoEmbalagem, setPrecoEmbalagem] = useState("");
  const [precoUnidade, setPrecoUnidade] = useState("");
  const [codigoUnidade, setCodigoUnidade] = useState("");
  const [formatoSimples, setFormatoSimples] = useState<"unidade" | "fechada">("unidade");
  const [conversaoConferida, setConversaoConferida] = useState(false);

  // Form state
  const [nome, setNome] = useState("");
  const [categoriaId, setCategoriaId] = useState<number | "">("");
  const [precoCusto, setPrecoCusto] = useState("");
  const [precoVenda, setPrecoVenda] = useState("");
  const [estoque, setEstoque] = useState("0");
  const [estoqueMinimo, setEstoqueMinimo] = useState("5");
  const [codigoBarras, setCodigoBarras] = useState("");
  const [unidade, setUnidade] = useState("UN");
  const [unidadeCompra, setUnidadeCompra] = useState("UN");
  const [quantidadePorEmbalagem, setQuantidadePorEmbalagem] = useState("1");
  const [fiscal, setFiscal] = useState<CamposFiscais>({ ...FISCAL_VAZIO });
  const [mostrarFiscal, setMostrarFiscal] = useState(false);

  // Importação de XML (NF-e)
  const fileRef = useRef<HTMLInputElement>(null);
  const importDialogRef = useRef<HTMLDialogElement>(null);
  const fiscalDialogRef = useRef<HTMLDialogElement>(null);
  const [importInfo, setImportInfo] = useState<{ emitente: string; numero: string; chave: string } | null>(null);
  const [importItens, setImportItens] = useState<ItemImport[]>([]);
  const [importTextos, setImportTextos] = useState<Record<string, string>>({});
  const [importBusy, setImportBusy] = useState(false);
  const [importMsg, setImportMsg] = useState<Mensagem | null>(null);
  const [margemPadrao, setMargemPadrao] = useState("30");
  const itensSelecionados = importItens.filter((item) => item.incluir);
  const custoSelecionado = itensSelecionados.reduce((s, it) => s + Number(it.quantidade || 0) * Number(it.preco_custo || 0), 0);
  const totalAtencao = importItens.filter((it) => it.acao === "criar" && itemDeEmbalagem(it)).length;
  const totalSelecionados = itensSelecionados.length;
  const totalNovos = itensSelecionados.filter((item) => item.acao === "criar").length;
  const todosSelecionados = totalSelecionados > 0 && totalSelecionados === importItens.length;
  const selecaoParcial = totalSelecionados > 0 && !todosSelecionados;

  useLayoutEffect(() => {
    const dialog = importDialogRef.current;
    if (!importInfo || !dialog) return;
    if (!dialog.open) dialog.showModal();
    return () => {
      if (dialog.open) dialog.close();
    };
  }, [importInfo]);

  useLayoutEffect(() => {
    const dialog = fiscalDialogRef.current;
    if (!mostrarFiscal || !dialog) return;
    if (!dialog.open) dialog.showModal();
    return () => {
      if (dialog.open) dialog.close();
    };
  }, [mostrarFiscal]);

  // Histórico de movimentações de um produto
  const [histProduto, setHistProduto] = useState<Produto | null>(null);
  const [histMovs, setHistMovs] = useState<Movimentacao[]>([]);
  const [histBusy, setHistBusy] = useState(false);

  async function abrirHistorico(p: Produto) {
    setHistProduto(p);
    setHistMovs([]);
    setHistBusy(true);
    try {
      const r = await listarMovimentacoes(p.id);
      setHistMovs(r.movimentacoes);
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setHistBusy(false);
    }
  }

  async function onXmlEscolhido(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // permite reimportar o mesmo arquivo
    if (!file) return;
    setImportBusy(true);
    setImportMsg(null);
    try {
      const prev: PreviewXml = await importarXmlPreview(file);
      setImportTextos({});
      setImportInfo({ emitente: prev.emitente, numero: prev.numero, chave: prev.chave });
      setImportItens(juntarRepetidos(prev.itens.map((it) => {
        const item: ItemImport = {
          produto_id: it.produto_id,
          vende_por_unidade: !!it.vende_por_unidade,
          preco_embalagem: it.preco_embalagem || 0,
          preco_unidade: it.preco_unidade || 0,
          unidade_xml: it.unidade_xml,
          fator_entrada: it.fator_entrada,
          perguntar_embalagem: it.perguntar_embalagem,
          nota_em_embalagem: (it.unidade_xml || "UN") !== "UN",
          nome: it.nome,
          codigo_barras: it.codigo_barras,
          codigo_barras_unidade: it.codigo_barras_unidade || "",
          ean_nota: it.codigo_barras,
          ean_trib_nota: it.acao === "criar" ? (it.codigo_barras_unidade || "") : "",
          unidade: it.unidade,
          unidade_compra: it.unidade_compra || it.unidade_xml || it.unidade,
          quantidade_por_embalagem: fatorSeguro(it.quantidade_por_embalagem),
          quantidade: it.quantidade,
          quantidade_xml: it.quantidade_xml ?? it.quantidade,
          preco_custo: it.valor_unitario,
          valor_unitario_xml: it.valor_unitario_xml ?? it.valor_unitario,
          valor_unitario_nota: it.valor_unitario_nota,
          despesas_unitarias: it.despesas_unitarias,
          preco_venda: it.preco_venda_atual ?? Number((it.valor_unitario * 1.3).toFixed(2)),
          atualizar_custo: true,
          ncm: it.ncm,
          cfop: it.cfop,
          acao: it.acao,
          estoque_atual: it.estoque_atual,
          incluir: true,
          embalagem_sugerida: it.embalagem_sugerida || "",
          sinais_embalagem: it.sinais_embalagem || [],
          aviso_unidade: it.aviso_unidade || "",
          fator_sugerido: it.fator_sugerido || 0,
          // Decisão inicial: produto novo entra por unidade (estoque na menor).
          // Nota em UN entra 1 para 1; nota em CX/FD multiplica pelo Qtd/emb.
          // Nada multiplica pelo número do nome sem o operador ver.
          modo_venda: it.acao === "criar" ? "unidade" : undefined,
        };
        if (item.modo_venda === "unidade") item.unidade = "UN";
        // Nota em caixa que diz quantas unidades vêm dentro (qTrib ÷ qCom):
        // produto novo já nasce vendendo a unidade, com a conta pronta.
        const sugerido = it.fator_sugerido || 0;
        if (it.acao === "criar" && sugerido > 1 && item.nota_em_embalagem) {
          item.unidade = "UN";
          item.quantidade_por_embalagem = sugerido;
          item.fator_entrada = sugerido;
          item.quantidade = Number((item.quantidade_xml! * sugerido).toFixed(4));
          item.preco_custo = Number((item.valor_unitario_xml! / sugerido).toFixed(4));
          item.preco_venda = Number((item.preco_custo * 1.3).toFixed(2));
        }
        return item;
      })));
    } catch (err) {
      setImportMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setImportBusy(false);
    }
  }

  const setItem = (i: number, campo: keyof ItemImport, valor: string | number | boolean) =>
    setImportItens((arr) => arr.map((it, idx) => {
      if (idx !== i) return it;
      const next = { ...it, [campo]: valor };
      if (campo === "confirmar_abertura") {
        next.modo_venda = valor ? "aberta" : (it.modo_venda === "aberta" ? "unidade" : it.modo_venda);
        if (valor) {
          // vende_por_unidade continua false aqui de propósito: é o payload que
          // liga as duas formas. Setar agora desabilitaria Qtd/emb. na tela.
          next.unidade = "UN";
          if (!next.unidade_compra || next.unidade_compra === "UN") {
            next.unidade_compra = next.embalagem_sugerida || embalagemDoNome(next.nome)
              || (next.unidade_xml && next.unidade_xml !== "UN" ? next.unidade_xml : "CX");
          }
        }
      }
      if (campo === "confirmar_abertura" || campo === "nota_em_embalagem") {
        Object.assign(next, codigosPadrao(next));
      }
      if (["quantidade_por_embalagem", "quantidade_xml", "confirmar_abertura", "nota_em_embalagem", "unidade_compra", "modo_venda"].includes(String(campo))) {
        // Um só cálculo manda: o modo escolhido + a forma como a nota conta.
        const fator = fatorDoModo(next);
        const qtdXml = Number(next.quantidade_xml || 0);
        next.fator_entrada = fator;
        next.quantidade = Number((qtdXml * fator).toFixed(4));
        if (next.valor_unitario_xml) {
          next.preco_custo = Number((next.valor_unitario_xml / fator).toFixed(4));
        }
      }
      if (campo === "unidade" || campo === "unidade_compra") {
        next[campo] = normUn(String(valor));
      }
      return next;
    }));

  /** Troca a decisão do produto novo: só unidade, caixa+unidade ou só caixa. */
  function setModo(i: number, modo: "unidade" | "aberta" | "fechada") {
    setImportItens((arr) => arr.map((it, idx) => {
      if (idx !== i) return it;
      const next: ItemImport = { ...it, modo_venda: modo };
      if (modo === "aberta") {
        next.confirmar_abertura = true;
        next.unidade = "UN";
        if (!next.unidade_compra || next.unidade_compra === "UN") {
          next.unidade_compra = next.embalagem_sugerida || embalagemDoNome(next.nome)
            || (next.unidade_xml && next.unidade_xml !== "UN" ? next.unidade_xml : "CX");
        }
      } else {
        next.confirmar_abertura = false;
        next.vende_por_unidade = false;
        next.unidade = modo === "unidade" ? "UN" : (next.unidade_xml && next.unidade_xml !== "UN" ? next.unidade_xml : next.embalagem_sugerida || "CX");
        next.unidade_compra = modo === "unidade"
          ? (next.unidade_xml && next.unidade_xml !== "UN"
              ? next.unidade_xml
              : (next.embalagem_sugerida || next.unidade_compra))
          : next.unidade;
      }
      // O rádio é a única pergunta agora: redistribui os códigos da caixa e da
      // unidade como o antigo checkbox "vende a embalagem fechada" fazia.
      Object.assign(next, codigosPadrao(next));
      const fator = fatorDoModo(next);
      const qtdXml = Number(next.quantidade_xml || 0);
      next.fator_entrada = fator;
      next.quantidade = Number((qtdXml * fator).toFixed(4));
      if (next.valor_unitario_xml) {
        next.preco_custo = Number((next.valor_unitario_xml / fator).toFixed(4));
      }
      return next;
    }));
  }

  /** Aplica a mesma margem sobre o custo a todos os produtos novos de preço único. */
  function aplicarMargemNovos() {
    const m = lerNumeroPtBr(margemPadrao);
    if (m === null || !Number.isFinite(m) || m < 0) {
      setImportMsg({ tipo: "erro", texto: `Margem inválida — “${margemPadrao}”. Use um número, por exemplo 30.` });
      return;
    }
    setImportMsg(null);
    setImportTextos((ant) => {
      const next = { ...ant };
      importItens.forEach((it, i) => { if (it.acao === "criar" && !it.confirmar_abertura) delete next[`${i}:preco_venda`]; });
      return next;
    });
    setImportItens((arr) => arr.map((it) => it.acao === "criar" && !it.confirmar_abertura
      ? { ...it, preco_venda: Number((it.preco_custo * (1 + m / 100)).toFixed(2)) }
      : it));
  }

  function fecharImportacao() {
    importDialogRef.current?.close();
    setImportInfo(null);
    setImportItens([]);
    setImportTextos({});
    setImportMsg(null);
  }

  const textoImport = (i: number, campo: CampoNumeroXml) => {
    const digitado = importTextos[`${i}:${campo}`];
    if (digitado !== undefined) return digitado;
    const valor = Number(importItens[i]?.[campo] ?? 0);
    // Custo calculado (divisão da caixa, desconto rateado) vem com 4 casas;
    // na tela basta o centavo. O valor exato continua no item enviado.
    return campo === "preco_custo" ? String(Number(valor.toFixed(2))) : String(importItens[i]?.[campo] ?? 0);
  };

  function editarNumeroImport(i: number, campo: CampoNumeroXml, texto: string) {
    const numero = lerNumeroPtBr(texto);
    const valido = numero !== null && numeroXmlValido(campo, numero);
    setImportTextos((ant) => {
      const next = { ...ant, [`${i}:${campo}`]: texto };
      if (valido && (campo === "quantidade_xml" || campo === "quantidade_por_embalagem")) {
        delete next[`${i}:quantidade`];
        delete next[`${i}:preco_custo`];
      }
      return next;
    });
    if (valido) setItem(i, campo, numero);
  }

  async function confirmarImportacao() {
    if (importBusy || !importInfo || totalSelecionados === 0) return;
    setImportMsg(null);
    for (const [i, it] of importItens.entries()) {
      if (!it.incluir) continue;
      const rotuloItem = `Item ${i + 1}${it.nome ? ` (${it.nome})` : ""}`;
      for (const campo of Object.keys(CAMPOS_NUMEROS_XML) as CampoNumeroXml[]) {
        // Só valida campo que o operador consegue ver e corrigir.
        if (!campoAtivo(it, campo)) continue;
        const numero = lerNumeroPtBr(textoImport(i, campo));
        if (numero === null || !numeroXmlValido(campo, numero)) {
          setImportMsg({ tipo: "erro", texto: `${rotuloItem}: valor inválido em ${CAMPOS_NUMEROS_XML[campo]} — “${textoImport(i, campo)}”.` });
          return;
        }
      }
      if (it.confirmar_abertura && (!(Number(it.preco_embalagem) > 0) || !(Number(it.preco_unidade) > 0) || !Number.isInteger(it.quantidade_por_embalagem) || !it.unidade_compra || it.unidade_compra === 'UN')) {
        setImportMsg({tipo:'erro',texto:`${rotuloItem}: informe a embalagem, quantas unidades vêm dentro (número inteiro) e os dois preços maiores que zero.`}); return;
      }
    }
    setImportBusy(true);
    try {
      const doc = importInfo.numero || importInfo.chave;
      const itens: ItemConfirmarXml[] = itensSelecionados.map((it) => ({
        produto_id: it.produto_id,
        vende_por_unidade: !!it.confirmar_abertura || !!it.vende_por_unidade,
        preco_embalagem: it.preco_embalagem || 0, preco_unidade: it.preco_unidade || 0,
        confirmar_abertura: it.confirmar_abertura,
        // Só manda o modo quando o estoque fica em UN; se o operador trocou a
        // unidade na mão (KG, LT…), a escolha dele manda.
        modo_entrada: it.acao === "criar"
          ? (it.confirmar_abertura ? "embalagem" : it.modo_venda === "fechada" ? "fechada" : it.unidade === "UN" ? "unidade" : undefined)
          : undefined,
        nota_em_embalagem: it.unidade === "UN" ? !!it.nota_em_embalagem : undefined,
        codigo_barras_unidade: it.codigo_barras_unidade || "",
        unidade_xml: it.unidade_xml, valor_unitario_xml: it.valor_unitario_xml,
        nome: it.nome,
        codigo_barras: it.codigo_barras,
        unidade: it.unidade,
        unidade_compra: it.unidade_compra,
        quantidade_por_embalagem: it.quantidade_por_embalagem,
        quantidade: it.quantidade,
        quantidade_xml: it.quantidade_xml,
        preco_custo: it.preco_custo,
        preco_venda: it.preco_venda,
        atualizar_custo: it.atualizar_custo,
        ncm: it.ncm,
        cfop: it.cfop,
      }));
      const r = await importarXmlConfirmar(doc, itens, importInfo.chave);
      fecharImportacao();
      setImportMsg({ tipo: "ok", texto: `Importado! ${r.atualizados} atualizado(s), ${r.criados} novo(s).` });
      carregar();
    } catch (err) {
      setImportMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setImportBusy(false);
    }
  }

  async function entradaRapida(p: Produto) {
    let modo: 'unidade' | 'embalagem' = 'unidade';
    if (p.vende_por_unidade) {
      const escolha = prompt(`Entrada de "${p.nome}"\n1 = unidades avulsas\n2 = ${p.unidade_compra} fechada(s) com ${p.quantidade_por_embalagem} unidades`, '1');
      if (escolha === null) return;
      if (!['1','2'].includes(escolha.trim())) {setMsg({tipo:'erro',texto:'Escolha 1 ou 2.'});return;}
      modo = escolha.trim() === '2' ? 'embalagem' : 'unidade';
    }
    const unEntrada = modo === 'embalagem' ? p.unidade_compra : p.unidade;
    const q = prompt(`Entrada de estoque — "${p.nome}"\nQuantidade a adicionar em ${unEntrada}:`, "1");
    if (q === null) return;
    const qtd = lerNumeroPtBr(q);
    if (qtd === null || qtd <= 0) { setMsg({ tipo: "erro", texto: "Quantidade inválida." }); return; }
    try {
      await entradaEstoque(p.id, qtd, undefined, undefined, modo);
      setMsg({ tipo: "ok", texto: `+${fmtQtd(qtd * (modo === 'embalagem' ? p.quantidade_por_embalagem : 1))} unidades em "${p.nome}".` });
      carregar();
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  async function ajusteRapido(p: Produto) {
    const op = prompt(
      `Ajustar estoque — "${p.nome}" (atual: ${fmtQtd(p.estoque)} ${p.unidade})\n\n` +
      "1 = Perda (vencido/avaria)\n2 = Quebra\n3 = Inventário (informar contagem real)\n\nDigite 1, 2 ou 3:",
      "1",
    );
    if (op === null) return;
    const tipo = ({ "1": "perda", "2": "quebra", "3": "inventario" } as const)[op.trim()];
    if (!tipo) { setMsg({ tipo: "erro", texto: "Opção inválida." }); return; }
    const rotulo = tipo === "inventario"
      ? `Contagem real em ${p.unidade}:`
      : `Quantidade a baixar (${tipo}) em ${p.unidade}:`;
    const q = prompt(rotulo, tipo === "inventario" ? String(p.estoque) : "1");
    if (q === null) return;
    const qtd = lerNumeroPtBr(q);
    if (qtd === null || qtd < 0 || (tipo !== "inventario" && qtd <= 0)) {
      setMsg({ tipo: "erro", texto: "Quantidade inválida." }); return;
    }
    try {
      const r = await ajustarEstoque(p.id, tipo, qtd);
      setMsg({ tipo: "ok", texto: `Estoque de "${p.nome}" ajustado para ${fmtQtd(r.produto.estoque)} ${p.unidade}.` });
      carregar();
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  const setF = (campo: keyof CamposFiscais, valor: string) =>
    setFiscal((f) => ({ ...f, [campo]: valor }));

  const carregar = useCallback(async () => {
    try {
      const [res, catRes] = await Promise.all([
        listarProdutos(false),
        listarCategorias(),
      ]);
      setProdutos(res.produtos);
      setCategorias(catRes.categorias);
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao carregar dados." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  function resetForm() {
    setFormatoSimples("unidade"); setConversaoConferida(false);
    setVendePorUnidade(false); setPrecoEmbalagem(""); setPrecoUnidade(""); setCodigoUnidade("");
    setNome("");
    setCategoriaId("");
    setPrecoCusto("");
    setPrecoVenda("");
    setEstoque("0");
    setEstoqueMinimo("5");
    setCodigoBarras("");
    setUnidade("UN");
    setUnidadeCompra("UN");
    setQuantidadePorEmbalagem("1");
    setFiscal({ ...FISCAL_VAZIO });
    setMostrarFiscal(false);
    setEditando(null);
    setNovo(false);
  }

  function abrirEdicao(p: Produto) {
    setFormatoSimples(["UN", "KG", "G", "LT", "ML"].includes(p.unidade) ? "unidade" : "fechada");
    setConversaoConferida(false);
    setVendePorUnidade(!!p.vende_por_unidade);
    setPrecoEmbalagem(p.vende_por_unidade ? String(p.preco_embalagem) : "");
    setPrecoUnidade(p.vende_por_unidade ? String(p.preco_unidade) : "");
    setCodigoUnidade(p.codigo_barras_unidade || "");
    setEditando(p);
    setNovo(false);
    setNome(p.nome);
    setCategoriaId(p.categoria_id || "");
    setPrecoCusto(String(p.preco_custo || ""));
    setPrecoVenda(String(p.preco_venda || ""));
    setEstoque(String(p.estoque));
    setEstoqueMinimo(String(p.estoque_minimo));
    setCodigoBarras(p.codigo_barras || "");
    setUnidade(p.unidade);
    setUnidadeCompra(p.unidade_compra || p.unidade || "UN");
    setQuantidadePorEmbalagem(String(p.quantidade_por_embalagem || 1));
    setFiscal({
      ncm: p.ncm || "", cest: p.cest || "", cfop: p.cfop || "5102",
      origem: p.origem || "0", unidade_tributavel: p.unidade_tributavel || "",
      cst_csosn: p.cst_csosn || "102", aliquota_icms: p.aliquota_icms,
      cst_pis: p.cst_pis || "07", aliquota_pis: p.aliquota_pis,
      cst_cofins: p.cst_cofins || "07", aliquota_cofins: p.aliquota_cofins,
    });
    setMsg(null);
  }

  function abrirNovo() {
    resetForm();
    setNovo(true);
    setMsg(null);
  }

  function trocarFormato(modo: "unidade" | "fechada" | "ambos") {
    setConversaoConferida(false);
    if (modo === "ambos") {
      setVendePorUnidade(true);
      setUnidade("UN");
      if (!unidadeCompra || unidadeCompra === "UN") setUnidadeCompra("CX");
      if (!vendePorUnidade) {
        setPrecoUnidade(unidade === "UN" ? precoVenda : "");
        setPrecoEmbalagem(unidade !== "UN" ? precoVenda : "");
        // Um código que já vendia a unidade continua vendendo a unidade.
        if (editando && unidade === "UN" && codigoBarras && !codigoUnidade) {
          setCodigoUnidade(codigoBarras); setCodigoBarras("");
        }
      }
    } else {
      if (vendePorUnidade) {
        setPrecoVenda(modo === "unidade" ? precoUnidade : precoEmbalagem);
        if (modo === "unidade") setCodigoBarras(codigoUnidade);
        setCodigoUnidade("");
      }
      setVendePorUnidade(false); setFormatoSimples(modo);
      const un = modo === "unidade" ? "UN" : (unidadeCompra !== "UN" ? unidadeCompra : "CX");
      setUnidade(un);
      if (modo === "fechada") {setUnidadeCompra(un); setQuantidadePorEmbalagem("1");}
    }
  }

  const mudouUnidade = !!editando && normUn(unidade) !== normUn(editando.unidade);
  function converterSaldo() {
    if (!editando) return;
    const paraUnidade = unidade === "UN";
    const fator = paraUnidade ? lerNumeroPtBr(quantidadePorEmbalagem) : editando.quantidade_por_embalagem;
    if (!fator || fator <= 1 || !Number.isInteger(fator)) {
      setMsg({tipo: "erro", texto: "Informe quantas unidades vêm em cada embalagem antes de converter."}); return;
    }
    const saldo = paraUnidade ? editando.estoque * fator : editando.estoque / fator;
    if (!paraUnidade && !Number.isInteger(saldo)) {
      setMsg({tipo: "erro", texto: "Há unidades soltas. Mantenha a venda por unidade ou confira a contagem de embalagens antes de salvar."}); return;
    }
    setEstoque(String(Number(saldo.toFixed(4))));
    setPrecoCusto(String(Number((paraUnidade ? editando.preco_custo / fator : editando.preco_custo * fator).toFixed(4))));
    setConversaoConferida(true); setMsg(null);
  }

  async function handleSalvar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    if (mudouUnidade && !conversaoConferida) {
      setMsg({tipo: "erro", texto: "Confira o estoque e o custo na nova unidade e marque a confirmação antes de salvar."}); return;
    }
    if (!nome.trim()) {
      setMsg({ tipo: "erro", texto: "Nome do produto é obrigatório." });
      return;
    }

    let valCusto = 0;
    if (precoCusto.trim() !== "") {
      const parsed = lerNumeroPtBr(precoCusto);
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Preço de custo inválido." });
        return;
      }
      valCusto = parsed;
    }

    let valVenda = 0;
    if (!vendePorUnidade && precoVenda.trim() !== "") {
      const parsed = lerNumeroPtBr(precoVenda);
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Preço de venda inválido." });
        return;
      }
      valVenda = parsed;
    }

    let valEstoque = 0;
    if (estoque.trim() !== "") {
      const parsed = lerNumeroPtBr(estoque);
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Estoque inválido." });
        return;
      }
      valEstoque = parsed;
    }

    let valMinimo = 0;
    if (estoqueMinimo.trim() !== "") {
      const parsed = lerNumeroPtBr(estoqueMinimo);
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Estoque mínimo inválido." });
        return;
      }
      valMinimo = parsed;
    }

    let valFator = 1;
    if (quantidadePorEmbalagem.trim() !== "") {
      const parsed = lerNumeroPtBr(quantidadePorEmbalagem);
      if (parsed === null || parsed < 0.0001) {
        setMsg({ tipo: "erro", texto: "Quantidade por compra inválida." });
        return;
      }
      valFator = parsed;
    }

    let valIcms = 0;
    if (fiscal.aliquota_icms !== undefined && String(fiscal.aliquota_icms).trim() !== "") {
      const parsed = lerNumeroPtBr(String(fiscal.aliquota_icms));
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Alíquota ICMS inválida." });
        return;
      }
      valIcms = parsed;
    }

    let valPis = 0;
    if (fiscal.aliquota_pis !== undefined && String(fiscal.aliquota_pis).trim() !== "") {
      const parsed = lerNumeroPtBr(String(fiscal.aliquota_pis));
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Alíquota PIS inválida." });
        return;
      }
      valPis = parsed;
    }

    let valCofins = 0;
    if (fiscal.aliquota_cofins !== undefined && String(fiscal.aliquota_cofins).trim() !== "") {
      const parsed = lerNumeroPtBr(String(fiscal.aliquota_cofins));
      if (parsed === null) {
        setMsg({ tipo: "erro", texto: "Alíquota COFINS inválida." });
        return;
      }
      valCofins = parsed;
    }

    const emb = lerNumeroPtBr(precoEmbalagem);
    const un = lerNumeroPtBr(precoUnidade);
    if (vendePorUnidade && (!(emb && emb > 0) || !(un && un > 0) || !unidadeCompra.trim() || !Number.isInteger(valFator) || normUn(unidade) !== "UN")) {
      setMsg({tipo:"erro", texto:"Informe a embalagem, quantidade inteira, os dois preços maiores que zero e unidade UN."}); return;
    }
    const data: ProdutoInput = {
      vende_por_unidade: vendePorUnidade, preco_embalagem: emb || 0, preco_unidade: un || 0, codigo_barras_unidade: codigoUnidade.trim(),
      nome: nome.trim(),
      categoria_id: categoriaId || undefined,
      preco_custo: valCusto,
      preco_venda: vendePorUnidade ? un! : valVenda,
      estoque: valEstoque,
      estoque_minimo: valMinimo,
      codigo_barras: codigoBarras.trim(),
      unidade: normUn(unidade),
      unidade_compra: normUn(unidadeCompra, unidade),
      quantidade_por_embalagem: valFator,
      ncm: (fiscal.ncm || "").trim(),
      cest: (fiscal.cest || "").trim(),
      cfop: (fiscal.cfop || "").trim(),
      origem: fiscal.origem || "0",
      unidade_tributavel: (fiscal.unidade_tributavel || "").trim(),
      cst_csosn: (fiscal.cst_csosn || "").trim(),
      aliquota_icms: valIcms,
      cst_pis: (fiscal.cst_pis || "").trim(),
      aliquota_pis: valPis,
      cst_cofins: (fiscal.cst_cofins || "").trim(),
      aliquota_cofins: valCofins,
    };

    try {
      if (editando) {
        await atualizarProduto(editando.id, data);
        setMsg({ tipo: "ok", texto: "Produto atualizado!" });
      } else {
        await criarProduto(data);
        setMsg({ tipo: "ok", texto: "Produto criado!" });
      }
      resetForm();
      carregar();
    } catch (err: unknown) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  async function handleDesativar(id: number) {
    if (!confirm("Desativar este produto?")) return;
    try {
      await desativarProduto(id);
      carregar();
    } catch (err: unknown) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row gap-3 lg:gap-4 h-full">
      {/* Lista */}
      <div className="flex-1 min-h-0 flex flex-col">
        {msg && !novo && !editando && <div role="status" className={`mb-3 rounded-lg border p-3 text-sm ${msg.tipo === 'ok' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>{msg.texto}</div>}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-white font-bold text-base sm:text-lg">📦 Produtos ({produtosExibidos.length})</h2>
          <div className="flex gap-2">
            <input ref={fileRef} type="file" accept=".xml,text/xml,application/xml" onChange={onXmlEscolhido} className="hidden" />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={importBusy}
              className="px-3 sm:px-4 py-1.5 sm:py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-60 text-white text-xs sm:text-sm font-medium rounded-lg transition-colors active:scale-95"
              title="Importar produtos/estoque de um XML de NF-e"
            >
              {importBusy ? "Lendo..." : "📄 Importar XML"}
            </button>
            <button
              onClick={abrirNovo}
              className="px-3 sm:px-4 py-1.5 sm:py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs sm:text-sm font-medium rounded-lg transition-colors active:scale-95"
            >
              + Novo
            </button>
          </div>
        </div>

        <label className="mb-3 flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={apenasAlerta}
            onChange={(e) => {
              const marcado = e.currentTarget.checked;
              setSearchParams((atual) => {
                const next = new URLSearchParams(atual);
                if (marcado) next.set("estoque", "alerta");
                else next.delete("estoque");
                return next;
              });
            }}
            className="h-4 w-4 accent-brand-500"
          />
          Somente produtos em alerta de estoque
        </label>

        {!importInfo && importMsg && (
          <p
            role={importMsg.tipo === "erro" ? "alert" : "status"}
            className={`mb-3 rounded-lg border p-3 text-sm ${importMsg.tipo === "erro"
              ? "border-red-500/30 bg-red-500/10 text-red-300"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"}`}
          >
            {importMsg.tipo === "erro" && <strong>Não foi possível ler o XML. </strong>}
            {importMsg.texto}
          </p>
        )}

        <div className="flex-1 overflow-y-auto rounded-xl bg-slate-900 border border-slate-800">
          {produtosExibidos.length === 0 ? (
            <p className="text-slate-500 text-center py-12 text-sm">{apenasAlerta ? "Nenhum produto em alerta de estoque." : "Nenhum produto cadastrado ainda."}</p>
          ) : (
            <>
              {/* Cards mobile: evita tabela espremida em telas pequenas */}
              <div className="sm:hidden grid gap-2 p-2">
                {produtosExibidos.map((p) => {
                  const baixo = p.estoque <= p.estoque_minimo;
                  return (
                    <article
                      key={p.id}
                      className={`rounded-xl border border-slate-800 bg-slate-950/50 p-3 ${!p.ativo ? "opacity-50" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <h3 className="text-white font-medium truncate">{p.nome}</h3>
                          <p className="text-slate-500 text-xs mt-0.5">
                            estoque <span className={baixo ? "text-amber-400" : "text-slate-300"}>{p.vende_por_unidade ? estoqueBalcao(p) : `${fmtQtd(p.estoque)} ${p.unidade}`}{baixo ? " ⚠️" : ""}</span>
                          </p>
                        </div>
                        {p.ativo ? (
                          <span className="text-green-400 text-2xs bg-green-500/10 px-2 py-1 rounded-full shrink-0">Ativo</span>
                        ) : (
                          <span className="text-slate-500 text-2xs bg-slate-800 px-2 py-1 rounded-full shrink-0">Inativo</span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2 my-3 text-sm">
                        <div className="rounded-lg bg-slate-800 p-2">
                          <p className="text-slate-500 text-2xs uppercase">Custo</p>
                          <p className="text-slate-300">R$ {(p.preco_custo || 0).toFixed(2)}</p>
                        </div>
                        <div className="rounded-lg bg-slate-800 p-2">
                          <p className="text-slate-500 text-2xs uppercase">Venda</p>
                          <p className="text-brand-400 font-semibold">{p.vende_por_unidade ? `${p.unidade_compra}: R$ ${Number(p.preco_embalagem).toFixed(2)} · Unidade: R$ ${Number(p.preco_unidade).toFixed(2)}` : `R$ ${(p.preco_venda || 0).toFixed(2)}`}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {!!p.ativo && <>
                          <button onClick={()=>entradaRapida(p)} className="touch-target rounded-lg bg-emerald-500/10 text-emerald-300 text-sm">+ Estoque</button>
                          <button onClick={()=>ajusteRapido(p)} className="touch-target rounded-lg bg-amber-500/10 text-amber-300 text-sm">Ajustar</button>
                        </>}
                        <button onClick={()=>abrirHistorico(p)} className="touch-target rounded-lg bg-sky-500/10 text-sky-300 text-sm">Histórico</button>
                        <button
                          onClick={() => abrirEdicao(p)}
                          className="touch-target rounded-lg bg-slate-800 text-slate-200 text-sm active:scale-95"
                        >
                          Editar
                        </button>
                        {p.ativo ? (
                          <button
                            onClick={() => handleDesativar(p.id)}
                            className="touch-target rounded-lg bg-red-900/30 text-red-400 text-sm active:scale-95"
                          >
                            Desativar
                          </button>
                        ) : <span />}
                      </div>
                    </article>
                  );
                })}
              </div>

              {/* Tabela tablet/desktop */}
              <table className="hidden sm:table w-full text-sm">
                <thead className="bg-slate-800 sticky top-0">
                  <tr className="text-slate-400 text-left">
                    <th className="p-3 font-medium">Nome</th>
                    <th className="p-3 font-medium">Custo</th>
                    <th className="p-3 font-medium">Venda</th>
                    <th className="p-3 font-medium hidden md:table-cell">Estoque</th>
                    <th className="p-3 font-medium hidden md:table-cell">Status</th>
                    <th className="p-3 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {produtosExibidos.map((p) => {
                    const baixo = p.estoque <= p.estoque_minimo;
                    return (
                      <tr key={p.id} className={`border-t border-slate-800 hover:bg-slate-800/50 ${!p.ativo ? "opacity-40" : ""}`}>
                        <td className="p-3 text-white">
                          <div className="font-medium truncate max-w-40">{p.nome}</div>
                          <div className="text-slate-500 text-xs">
                            {p.unidade_compra || p.unidade} x {fmtQtd(p.quantidade_por_embalagem || 1)} {p.unidade}
                          </div>
                        </td>
                        <td className="p-3 text-slate-300">R$ {(p.preco_custo || 0).toFixed(2)}</td>
                        <td className="p-3 text-brand-400 font-semibold">{p.vende_por_unidade ? `${p.unidade_compra}: R$ ${Number(p.preco_embalagem).toFixed(2)} · Unidade: R$ ${Number(p.preco_unidade).toFixed(2)}` : `R$ ${(p.preco_venda || 0).toFixed(2)}`}</td>
                        <td className="p-3 hidden md:table-cell">
                          <span className={baixo ? "text-amber-400 font-medium" : "text-slate-300"}>{p.vende_por_unidade ? estoqueBalcao(p) : `${fmtQtd(p.estoque)} ${p.unidade}`}{baixo && ` ⚠️`}</span>
                        </td>
                        <td className="p-3 hidden md:table-cell">
                          {p.ativo ? (
                            <span className="text-green-400 text-xs bg-green-500/10 px-2 py-0.5 rounded">Ativo</span>
                          ) : (
                            <span className="text-slate-500 text-xs bg-slate-800 px-2 py-0.5 rounded">Inativo</span>
                          )}
                        </td>
                        <td className="p-3">
                          <div className="flex gap-1 justify-end">
                            {p.ativo ? <button onClick={() => entradaRapida(p)} className="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1 rounded hover:bg-slate-700 active:scale-95" title="Dar entrada no estoque">+ Estoque</button> : null}
                            {p.ativo ? <button onClick={() => ajusteRapido(p)} className="text-amber-400 hover:text-amber-300 text-xs px-2 py-1 rounded hover:bg-slate-700 active:scale-95" title="Perda, quebra ou inventário">Ajustar</button> : null}
                            <button onClick={() => abrirHistorico(p)} className="text-sky-400 hover:text-sky-300 text-xs px-2 py-1 rounded hover:bg-slate-700 active:scale-95" title="Histórico de movimentações">Histórico</button>
                            <button onClick={() => abrirEdicao(p)} className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-slate-700 active:scale-95">Editar</button>
                            {p.ativo ? <button onClick={() => handleDesativar(p.id)} className="text-red-400 hover:text-red-300 text-xs px-2 py-1 rounded hover:bg-slate-700 active:scale-95">Desativar</button> : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>

      {/* Formulário */}
      {(novo || editando) && (
        <div className="w-full lg:w-96 bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold">
              {editando ? "✏️ Editar Produto" : "➕ Novo Produto"}
            </h3>
            <button onClick={resetForm} className="text-slate-400 hover:text-white text-lg">
              ×
            </button>
          </div>

          {msg && (
            <div
              className={`p-3 rounded-lg text-sm mb-3 ${
                msg.tipo === "ok"
                  ? "bg-green-500/10 border border-green-500/30 text-green-400"
                  : "bg-red-500/10 border border-red-500/30 text-red-400"
              }`}
            >
              {msg.texto}
            </div>
          )}

          <form onSubmit={handleSalvar} className="space-y-3">
            <div>
              <label className="text-slate-400 text-xs block mb-0.5">Nome *</label>
              <input type="text" value={nome} onChange={(e) => setNome(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                placeholder="Ex: Arroz 5kg" autoFocus />
            </div>
            <fieldset className="space-y-2 rounded-xl border border-brand-500/40 bg-brand-500/10 p-3 text-white">
              <legend className="text-sm font-semibold">Como o cliente compra?</legend>
              {([
                ["unidade", "Somente unidade", "Ex.: bebida láctea, lata ou palheiro solto. Também serve para KG/LT."],
                ["ambos", "Caixa e unidade", "Dois preços: a embalagem inteira e cada unidade avulsa."],
                ["fechada", "Somente embalagem fechada", "Ex.: uma carteira ou caixa inteira, sem vender o conteúdo solto."],
              ] as const).map(([modo, titulo, ajuda]) => <label key={modo} className="flex cursor-pointer items-start gap-2 text-sm">
                <input type="radio" aria-label={titulo} name="formato-cadastro" className="mt-1 accent-brand-500" checked={vendePorUnidade ? modo === "ambos" : modo === formatoSimples} onChange={() => trocarFormato(modo)} />
                <span>{titulo}<small className="block text-xs text-slate-400">{ajuda}</small></span>
              </label>)}
              <p className="text-xs text-slate-300">A forma de entrega do fornecedor é separada da forma de venda. Uma caixa entregue pode já estar contada em unidades na nota.</p>
            </fieldset>
            {vendePorUnidade && <fieldset className="space-y-3 rounded-xl border border-brand-500/30 p-3">
              <legend className="text-brand-300 text-sm">Dois preços independentes</legend>
              <label className="block text-slate-300 text-sm">Preço da embalagem fechada (R$)
                <input aria-label="Preço da embalagem fechada" value={precoEmbalagem} onChange={e=>setPrecoEmbalagem(e.target.value)} inputMode="decimal" className="w-full rounded-lg bg-slate-800 p-2 text-white" required />
              </label>
              <label className="block text-slate-300 text-sm">Preço da unidade (R$)
                <input aria-label="Preço da unidade" value={precoUnidade} onChange={e=>setPrecoUnidade(e.target.value)} inputMode="decimal" className="w-full rounded-lg bg-slate-800 p-2 text-white" required />
              </label>
              <p className="text-xs text-slate-400">Estoque e custo sempre por unidade. O código principal lança a embalagem fechada no caixa; o código da unidade lança 1 avulsa.</p>
              <ul aria-label="Comparação de preços" className="space-y-0.5 rounded-lg bg-slate-900/60 p-2 text-xs text-slate-200">
                {textoComparacao({custo: lerNumeroPtBr(precoCusto) || 0, fator: lerNumeroPtBr(quantidadePorEmbalagem) || 0, precoEmbalagem: lerNumeroPtBr(precoEmbalagem) || 0, precoUnidade: lerNumeroPtBr(precoUnidade) || 0, embalagem: unidadeCompra}).map(t => <li key={t} className={t.startsWith('⚠️') ? 'text-amber-300' : ''}>{t}</li>)}
              </ul>
            </fieldset>}
            <label className="block text-slate-300 text-sm">{vendePorUnidade ? "Código da unidade (opcional)" : "Segundo código de barras (opcional)"}
              <input aria-label="Código da unidade" value={codigoUnidade} onChange={e=>setCodigoUnidade(e.target.value)} className="w-full rounded-lg bg-slate-800 p-2 text-white" placeholder={vendePorUnidade ? "o da lata/unidade avulsa" : "outro código do mesmo produto"} />
            </label>

            <div>
              <label className="text-slate-400 text-xs block mb-0.5">Categoria</label>
              <select
                value={categoriaId}
                onChange={(e) => setCategoriaId(e.target.value ? Number(e.target.value) : "")}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
              >
                <option value="">Sem categoria</option>
                {categorias.map((cat) => (
                  <option key={cat.id} value={cat.id}>{cat.nome}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Preço Custo</label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={precoCusto}
                  onChange={(e) => setPrecoCusto(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="0,00"
                />
              </div>
              {!vendePorUnidade && <div>
                <label className="text-slate-400 text-xs block mb-0.5">Preço Venda</label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={precoVenda}
                  onChange={(e) => setPrecoVenda(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="0,00"
                />
              </div>}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Estoque</label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={estoque}
                  onChange={(e) => setEstoque(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="0"
                />
                <p className="mt-1 text-xs text-slate-500">Contado em {unidade || "UN"}. {vendePorUnidade ? "Some todas as unidades, inclusive as caixas fechadas." : "Informe a quantidade pronta para vender."}</p>
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Estoque Mínimo</label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={estoqueMinimo}
                  onChange={(e) => setEstoqueMinimo(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="0"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">{vendePorUnidade ? "Código da embalagem (opcional)" : "Código Barras"}</label>
                <input
                  type="text"
                  value={codigoBarras}
                  onChange={(e) => setCodigoBarras(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="789..."
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Unidade</label>
                <input
                  type="text"
                  value={unidade}
                  onChange={(e) => setUnidade(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="UN, KG, LT"
                />
              </div>
            </div>

            {/* ── Dados fiscais (NFC-e) ── */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">{vendePorUnidade ? "Nome da embalagem" : "Unidade da compra"}</label>
                {vendePorUnidade ? <input aria-label="Nome da embalagem" list="unidades-compra"
                  value={unidadeCompra}
                  onChange={(e) => setUnidadeCompra(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                /> : <select value={unidadeCompra} onChange={e=>setUnidadeCompra(e.target.value)} className="w-full rounded-lg bg-slate-800 p-2 text-white">{UNIDADES.map(u=><option key={u} value={u}>{u}</option>)}</select>}
                <datalist id="unidades-compra">{UNIDADES.map((u) => <option key={u} value={u} />)}<option value="CARTEIRA" /><option value="DISPLAY" /></datalist>
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Qtd por compra</label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={quantidadePorEmbalagem}
                  onChange={(e) => setQuantidadePorEmbalagem(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="1"
                />
                <p className="mt-1 text-xs text-slate-500">{vendePorUnidade ? "Quantas unidades vêm dentro? Ex.: 12 latas ou 20 palheiros." : "Só converte uma compra em embalagem. Não multiplica uma nota que já conta unidades."}</p>
              </div>
            </div>

            {vendePorUnidade && editando && editando.estoque > 0 && lerNumeroPtBr(quantidadePorEmbalagem) !== editando.quantidade_por_embalagem && <p role="status" className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-300">Alterar a quantidade por embalagem não reconta o estoque: continuam {fmtQtd(editando.estoque)} unidades.</p>}
            {mudouUnidade && <div className="space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
              <p>Você está mudando o estoque de {editando!.unidade} para {unidade}. Antes: {fmtQtd(editando!.estoque)} {editando!.unidade}, custo {fmtReais(editando!.preco_custo)} por {editando!.unidade}. Ao salvar: {estoque || "0"} {unidade}, custo {precoCusto || "0"} por {unidade}.</p>
              <button type="button" onClick={converterSaldo} className="rounded-lg border border-amber-500/50 px-2 py-2 font-semibold">Converter estoque e custo pela embalagem</button>
              <label className="flex items-start gap-2"><input type="checkbox" checked={conversaoConferida} onChange={e => setConversaoConferida(e.target.checked)} />Conferi o estoque e o custo na nova unidade</label>
            </div>}
            {editando && <p className="text-xs text-slate-400">Alterar o preço vale para as próximas vendas. Para trocar só o preço, mantenha o formato e o estoque atuais.</p>}
            <button
              type="button"
              onClick={() => setMostrarFiscal(true)}
              className="w-full flex items-center justify-between gap-3 rounded-lg border border-slate-700 bg-slate-800/70 px-3 py-2.5 text-left hover:border-slate-600"
            >
              <span className="min-w-0">
                <span className="block text-xs font-bold uppercase tracking-wide text-slate-200">Dados fiscais (NFC-e)</span>
                <span className="mt-0.5 block truncate text-[11px] text-slate-400">
                  {[fiscal.ncm && `NCM ${fiscal.ncm}`, fiscal.cfop && `CFOP ${fiscal.cfop}`, fiscal.cst_csosn && `CSOSN ${fiscal.cst_csosn}`].filter(Boolean).join(" · ") || "Toque para preencher NCM, CFOP e CSOSN"}
                </span>
              </span>
              <span className="shrink-0 text-xs font-semibold text-brand-300">Abrir</span>
            </button>

            <button
              type="submit"
              className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors"
            >
              {editando ? "Salvar Alterações" : "Criar Produto"}
            </button>
          </form>
        </div>
      )}

      {mostrarFiscal && (
        <dialog
          ref={fiscalDialogRef}
          aria-labelledby="dados-fiscais-titulo"
          onCancel={(event) => {
            event.preventDefault();
            setMostrarFiscal(false);
          }}
          className="fixed left-1/2 top-1/2 m-0 w-[min(32rem,calc(100%-1.5rem))] max-h-[min(34rem,calc(100dvh-7rem))] -translate-x-1/2 -translate-y-1/2 open:flex flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 p-0 text-slate-100 shadow-2xl backdrop:bg-black/75"
        >
          <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-800 px-4 py-3">
            <div>
              <h3 id="dados-fiscais-titulo" className="text-base font-bold text-white">Dados fiscais (NFC-e)</h3>
              <p className="text-[11px] text-slate-400">Simples Nacional · os valores ficam no produto ao fechar</p>
            </div>
            <button type="button" aria-label="Fechar dados fiscais" onClick={() => setMostrarFiscal(false)} className="grid h-8 w-8 place-items-center rounded-lg text-xl leading-none text-slate-400 hover:bg-slate-800 hover:text-white">×</button>
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-2 gap-3 overflow-y-auto p-4">
            <label className="block min-w-0">
              <span className="mb-1 block text-xs text-slate-400">NCM</span>
              <input value={fiscal.ncm} inputMode="numeric" maxLength={8} onChange={(e) => setF("ncm", e.target.value.replace(/\D/g, "").slice(0, 8))} placeholder="8 dígitos" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-brand-500" />
            </label>
            <label className="block min-w-0">
              <span className="mb-1 block text-xs text-slate-400">CFOP</span>
              <input value={fiscal.cfop} inputMode="numeric" maxLength={4} onChange={(e) => setF("cfop", e.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="5102" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-brand-500" />
            </label>
            <label className="block min-w-0">
              <span className="mb-1 block text-xs text-slate-400">CEST</span>
              <input value={fiscal.cest} inputMode="numeric" maxLength={7} onChange={(e) => setF("cest", e.target.value.replace(/\D/g, "").slice(0, 7))} placeholder="Opcional" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-brand-500" />
            </label>
            <label className="block min-w-0">
              <span className="mb-1 block text-xs text-slate-400">Origem</span>
              <input value={fiscal.origem} inputMode="numeric" maxLength={1} onChange={(e) => setF("origem", e.target.value.replace(/\D/g, "").slice(0, 1))} placeholder="0" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-brand-500" />
            </label>
            <label className="block min-w-0">
              <span className="mb-1 block text-xs text-slate-400">CST/CSOSN</span>
              <input value={fiscal.cst_csosn} inputMode="numeric" maxLength={3} onChange={(e) => setF("cst_csosn", e.target.value.replace(/\D/g, "").slice(0, 3))} placeholder="102" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-brand-500" />
            </label>
            <label className="block min-w-0">
              <span className="mb-1 block text-xs text-slate-400">Alíquota ICMS %</span>
              <input type="text" inputMode="decimal" value={fiscal.aliquota_icms ?? ""} onChange={(e) => setF("aliquota_icms", e.target.value)} placeholder="0" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-brand-500" />
            </label>
            <p className="col-span-2 text-xs leading-relaxed text-slate-400">
              No Simples Nacional use CSOSN, por exemplo 102. NCM e CFOP são obrigatórios para emitir a nota. Em dúvida, confirme com o contador.
            </p>
          </div>
          <div className="shrink-0 border-t border-slate-800 px-4 py-3">
            <button type="button" onClick={() => setMostrarFiscal(false)} className="w-full rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-500">Concluir</button>
          </div>
        </dialog>
      )}

      {/* ── Modal: Importar XML (NF-e) ── */}
      {importInfo && (
        <dialog
          ref={importDialogRef}
          aria-labelledby="importar-xml-titulo"
          onCancel={(event) => {
            event.preventDefault();
            if (!importBusy) fecharImportacao();
          }}
          className="fixed inset-0 m-auto w-[calc(100%-1.5rem)] max-w-5xl max-h-[92dvh] open:flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 text-slate-100 backdrop:bg-black/80 backdrop:backdrop-blur-sm"
        >
          <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-800 p-4">
            <div className="min-w-0">
              <h3 id="importar-xml-titulo" className="text-white font-black text-base sm:text-lg">📄 Importar XML — entrada de estoque</h3>
              <p className="truncate text-sm text-slate-300">{importInfo.emitente || "Fornecedor"} · NF {importInfo.numero || "—"}</p>
              <p className="text-xs text-slate-400">
                {importItens.length} produto(s): {importItens.filter((it) => it.acao === "criar").length} novo(s) para cadastrar · {importItens.filter((it) => it.acao === "atualizar").length} já cadastrado(s), só soma no estoque
              </p>
            </div>
            <button type="button" aria-label="Fechar prévia do XML" onClick={fecharImportacao} disabled={importBusy} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-60 text-2xl leading-none">×</button>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-slate-800 bg-slate-950/40 px-4 py-2 text-xs text-slate-300">
            <p className="flex-1 basis-72">Confira <strong className="text-white">nome</strong>, <strong className="text-white">quantidade</strong> e o <strong className="text-white">preço de venda</strong> de cada produto e clique em <strong className="text-white">Confirmar importação</strong>.</p>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5">Margem dos novos
                <input aria-label="Margem padrão dos produtos novos" inputMode="decimal" value={margemPadrao} onChange={(e) => setMargemPadrao(e.target.value)} className="w-14 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-right text-white" />%
              </label>
              <button type="button" onClick={aplicarMargemNovos} disabled={importBusy} className="rounded-lg bg-slate-800 px-3 py-1.5 font-semibold text-white hover:bg-slate-700 disabled:opacity-60">Aplicar aos novos</button>
            </div>
          </div>

          {totalAtencao > 0 && (
            <p className="mx-4 mt-3 shrink-0 rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-200">
              📦 {totalAtencao} produto(s) novo(s) parecem vir em caixa, fardo ou pacote. Estão destacados em amarelo: confira quantas unidades vêm dentro e como você vende.
            </p>
          )}
          {importMsg?.tipo === "erro" && (
            <p role="alert" className="mx-4 mt-3 shrink-0 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{importMsg.texto}</p>
          )}

          <div className="min-h-0 flex-1 overflow-auto px-3 py-3">
            <fieldset disabled={importBusy} className="min-w-0">
              <legend className="sr-only">Itens do XML</legend>
              <label className="mb-2 flex w-fit cursor-pointer items-center gap-2 px-1 text-xs text-slate-300">
                <input
                  type="checkbox"
                  aria-label="Selecionar todos os itens"
                  checked={todosSelecionados}
                  disabled={importItens.length === 0}
                  ref={(input) => { if (input) input.indeterminate = selecaoParcial; }}
                  onChange={(event) => {
                    const incluir = event.target.checked;
                    setImportItens((itens) => itens.map((item) => ({ ...item, incluir })));
                  }}
                  className={CHECKBOX_IMPORTACAO}
                />
                Marcar todos
              </label>
              <ul className="space-y-2">
                {importItens.map((it, i) => {
                  const novo = it.acao === "criar";
                  const embalagem = novo && itemDeEmbalagem(it);
                  const modo = it.modo_venda || "unidade";
                  const unEstoque = it.confirmar_abertura ? "UN" : it.unidade;
                  const unNota = it.unidade_xml || it.unidade_compra || "UN";
                  const nomeEmbalagem = it.unidade_compra && it.unidade_compra !== "UN" ? it.unidade_compra : (unNota !== "UN" ? unNota : "embalagem");
                  const despesas = Number(it.despesas_unitarias || 0);
                  const margem = margemSobreCusto(Number(it.preco_custo), Number(it.preco_venda));
                  const mostraFator = !!it.confirmar_abertura || (unEstoque === "UN" && !!it.nota_em_embalagem)
                    || (!it.vende_por_unidade && modo !== "fechada" && (unNota !== "UN" || (it.fator_sugerido || 0) > 1));
                  const campo = (nome: CampoNumeroXml, rotulo: string, extra?: React.ReactNode) => (
                    <label className="block text-2xs text-slate-400">{rotulo}
                      <input
                        type="text"
                        inputMode="decimal"
                        aria-label={`${CAMPOS_NUMEROS_XML[nome]} do item ${i + 1}`}
                        value={textoImport(i, nome)}
                        onChange={(e) => editarNumeroImport(i, nome, e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-white"
                      />
                      {extra}
                    </label>
                  );
                  const leitura = (rotulo: string, valor: string, campoXml?: CampoNumeroXml) => (
                    <div className="text-2xs text-slate-400">{rotulo}
                      <p aria-label={campoXml ? `${CAMPOS_NUMEROS_XML[campoXml]} do item ${i + 1}` : undefined} className="mt-1 rounded-lg border border-transparent px-1 py-1.5 text-sm font-semibold text-white">{valor}</p>
                    </div>
                  );
                  return (
                     <li
                      key={i}
                      data-item-xml
                      className={`rounded-xl border px-3 py-2.5 ${!it.incluir ? "border-slate-800 bg-slate-950/30 opacity-60" : embalagem ? "border-amber-500/40 bg-amber-500/5" : "border-slate-700 bg-slate-950/40"}`}
                    >
                      <div className="flex items-start gap-3">
                        <label className="mt-1 flex cursor-pointer items-center">
                          <input type="checkbox" checked={it.incluir} onChange={(e) => setItem(i, "incluir", e.target.checked)} className={CHECKBOX_IMPORTACAO} />
                          <span className="sr-only">Incluir {it.nome || `item ${i + 1}`}</span>
                        </label>
                        <div className="min-w-0 flex-1 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <input aria-label={`Nome do item ${i + 1}`} value={it.nome} onChange={(e) => setItem(i, "nome", e.target.value)} className="min-w-0 flex-1 basis-64 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm font-semibold text-white" />
                            {novo
                              ? <span className="whitespace-nowrap rounded-full bg-amber-500/15 px-2 py-0.5 text-2xs font-bold text-amber-300">NOVO · será cadastrado</span>
                              : <span className="whitespace-nowrap rounded-full bg-emerald-500/15 px-2 py-0.5 text-2xs font-bold text-emerald-300">JÁ CADASTRADO · tem {fmtQtd(it.estoque_atual)} {it.unidade}</span>}
                          </div>
                          <p className="text-2xs text-slate-400">
                            {it.codigo_barras || "sem código de barras"} · Nota: {fmtQtd(it.quantidade_xml || 0)} {unNota} × {fmtReais(Number(it.valor_unitario_nota ?? it.valor_unitario_xml ?? 0))}
                            {despesas < 0 ? ` − desconto ${fmtReais(-despesas)}` : despesas > 0 ? ` + frete/impostos ${fmtReais(despesas)}` : ""}
                            {despesas !== 0 ? ` = ${fmtReais(Number(it.valor_unitario_xml || 0))} por ${unNota}` : ""}
                            {it.linhas_nota && it.linhas_nota.length > 1 ? ` · veio em ${it.linhas_nota.length} linhas na nota (${it.linhas_nota.map(fmtQtd).join(" + ")}), juntadas aqui` : ""}
                          </p>

                          {unEstoque === "UN" && <fieldset className="space-y-1 rounded-lg border border-sky-500/30 bg-sky-500/5 p-2 text-xs text-slate-200">
                            <legend className="px-1 font-semibold text-sky-300">1. Como a nota conta esta compra?</legend>
                            <p className="text-slate-400">Confira o preço da nota: {fmtReais(Number(it.valor_unitario_nota || 0))} é por unidade ou pela embalagem inteira? A entrega em caixas não muda essa resposta.</p>
                            <label className="flex items-start gap-2"><input type="radio" name={`conta-${i}`} className="mt-0.5 accent-brand-500" checked={!it.nota_em_embalagem} onChange={() => setItem(i, "nota_em_embalagem", false)} />Em unidades soltas: {fmtQtd(it.quantidade_xml || 0)} {it.unidade_xml} = {fmtQtd(it.quantidade_xml || 0)} unidades</label>
                            <label className="flex items-start gap-2"><input type="radio" name={`conta-${i}`} className="mt-0.5 accent-brand-500" checked={!!it.nota_em_embalagem} onChange={() => setItem(i, "nota_em_embalagem", true)} />Em {it.unidade_compra && it.unidade_compra !== "UN" ? it.unidade_compra : "embalagem"} fechada: {fmtQtd(it.quantidade_xml || 0)} {it.unidade_xml} × {fmtQtd(it.quantidade_por_embalagem)} = {fmtQtd((it.quantidade_xml || 0) * it.quantidade_por_embalagem)} unidades</label>
                            {!it.nota_em_embalagem && <p className="text-sky-200">Ex.: bebida láctea com 54 UN na nota entra como 54 unidades, mesmo chegando em caixas.</p>}
                          </fieldset>}

                          {novo && !(embalagem || it.mostrar_modo || modo !== "unidade") && (
                            <p className="text-2xs text-slate-400">Vende só por unidade.{" "}
                              <button type="button" onClick={() => setItem(i, "mostrar_modo", true)} className="font-semibold text-brand-300 underline-offset-2 hover:underline">Vende em caixa também? Trocar</button>
                            </p>
                          )}
                          {novo && (embalagem || it.mostrar_modo || modo !== "unidade") && (
                            <fieldset className="flex flex-wrap items-center gap-1.5">
                              <legend className="float-left mr-1 py-1 text-xs font-semibold text-slate-200">2. Como vende?</legend>
                              {([
                                ["unidade", "Só por unidade"],
                                ["aberta", "Caixa fechada e unidade"],
                                ["fechada", "Só a embalagem fechada"],
                              ] as const).map(([valor, titulo]) => (
                                <label key={valor} className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${modo === valor ? "border-brand-500 bg-brand-500/15 text-white" : "border-slate-700 text-slate-300 hover:border-slate-500"}`}>
                                  <input type="radio" name={`modo-${i}`} className="accent-brand-500" checked={modo === valor} onChange={() => setModo(i, valor)} />
                                  {titulo}
                                </label>
                              ))}
                              {!it.confirmar_abertura && (
                                <label className="ml-auto flex items-center gap-1.5 text-xs text-slate-400">Estoque em
                                  <select aria-label={`Unidade de estoque do item ${i + 1}`} value={it.unidade} onChange={(e) => setItem(i, "unidade", e.target.value)} className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1 text-white">
                                    {Array.from(new Set([...UNIDADES, it.unidade, it.unidade_compra])).map((u) => <option key={u} value={u}>{u}</option>)}
                                  </select>
                                </label>
                              )}
                            </fieldset>
                          )}

                          {!novo && <p className="rounded-lg bg-emerald-500/5 p-2 text-xs text-emerald-200">Formato atual: {it.vende_por_unidade ? `${it.unidade_compra} com ${fmtQtd(it.quantidade_por_embalagem)} unidades e unidade avulsa` : `venda por ${it.unidade}`}. Esta entrada mantém os preços e o formato. Para alterá-los, feche a prévia e use Editar no produto.</p>}

                          {embalagem && !!it.sinais_embalagem?.length && modo !== "aberta" && (
                            <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-2xs text-amber-200">
                              📦 Pode ser caixa: {it.sinais_embalagem.join("; ")}. Confira pelo preço da nota. Se você vende a caixa e também a unidade, escolha “Caixa fechada e unidade”.
                            </p>
                          )}

                          <div className="grid grid-cols-2 gap-x-2 gap-y-1 sm:grid-cols-5">
                            {campo("quantidade_xml", `Na nota (${unNota})`)}
                            {mostraFator && (campoAtivo(it, "quantidade_por_embalagem")
                              ? campo("quantidade_por_embalagem", `Unidades em cada ${nomeEmbalagem}`)
                              : leitura(`Unidades em cada ${nomeEmbalagem} (cadastro)`, fmtQtd(it.quantidade_por_embalagem), "quantidade_por_embalagem"))}
                            {campoAtivo(it, "quantidade")
                              ? campo("quantidade", `Entra no estoque (${unEstoque})`)
                              : leitura("Entra no estoque", `${fmtQtd(it.quantidade)} ${unEstoque}`, "quantidade")}
                            {campoAtivo(it, "preco_custo")
                              ? campo("preco_custo", `Custo por ${unEstoque} (R$)`)
                              : leitura("Custo por unidade", fmtReais(Number(it.preco_custo)), "preco_custo")}
                            {novo && !it.confirmar_abertura
                              ? campo("preco_venda", `Preço de venda (R$)`, <span className={`mt-0.5 block ${margem !== null && margem < 0 ? "text-red-300" : "text-slate-500"}`}>{margem === null ? "—" : margem < 0 ? `prejuízo ${-margem}%` : `lucro ${margem}%`}</span>)
                              : novo
                                ? leitura("Preço de venda", "nos dois preços abaixo")
                                : leitura("Preço de venda", it.vende_por_unidade ? "mantém os dois preços" : `mantém ${fmtReais(Number(it.preco_venda))}`)}
                          </div>

                          {it.confirmar_abertura && (
                            <div className="space-y-2 rounded-lg border border-brand-500/30 bg-brand-500/5 p-3">
                              <p className="text-xs font-semibold text-white">Caixa fechada e unidade: dois preços no caixa</p>
                              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                                <label className="block text-2xs text-slate-400">Nome da embalagem (CX, FD, PCT…)
                                  <input aria-label={`Embalagem do item ${i + 1}`} value={it.unidade_compra} onChange={(e) => setItem(i, "unidade_compra", e.target.value.toUpperCase())} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-white" />
                                </label>
                                {campo("preco_embalagem", `Preço da ${nomeEmbalagem} fechada (R$)`)}
                                {campo("preco_unidade", "Preço da unidade avulsa (R$)")}
                              </div>
                              <div className="grid grid-cols-2 gap-2">
                                <label className="block text-2xs text-slate-400">Código de barras da {nomeEmbalagem}<input aria-label={`Código da embalagem do item ${i + 1}`} value={it.codigo_barras} onChange={(e) => setItem(i, "codigo_barras", e.target.value.trim())} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-white" placeholder="opcional" /></label>
                                <label className="block text-2xs text-slate-400">Código de barras da unidade<input aria-label={`Código da unidade do item ${i + 1}`} value={it.codigo_barras_unidade || ""} onChange={(e) => setItem(i, "codigo_barras_unidade", e.target.value.trim())} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-white" placeholder="opcional — bipe uma unidade" /></label>
                              </div>
                              <ul aria-label={`Comparação de preços do item ${i + 1}`} className="space-y-0.5 text-xs text-slate-200">
                                {textoComparacao({ custo: it.preco_custo, fator: it.quantidade_por_embalagem, precoEmbalagem: Number(it.preco_embalagem) || 0, precoUnidade: Number(it.preco_unidade) || 0, embalagem: it.unidade_compra }).map((t) => <li key={t} className={t.startsWith("⚠️") ? "text-amber-300" : ""}>{t}</li>)}
                              </ul>
                            </div>
                          )}
                          {novo && modo === "fechada" && (
                            <p className="text-2xs text-slate-400">No caixa vende só por {it.unidade}; a unidade avulsa não é vendida. Confira quantas embalagens entram e o custo de cada embalagem. Se a nota já contou o conteúdo em UN, informe aqui a contagem de embalagens fechadas.</p>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </fieldset>
          </div>

          <div className="flex shrink-0 flex-col justify-between gap-3 border-t border-slate-800 p-3 sm:flex-row sm:items-center sm:p-4">
            <div role="status" aria-atomic="true" className="space-y-1">
              <p className="text-white text-sm font-semibold">{totalSelecionados} de {importItens.length} itens selecionados</p>
              <p className="text-slate-400 text-xs">
                {totalSelecionados > 0
                  ? `${totalNovos} para criar · ${totalSelecionados - totalNovos} para repor · custo total ${fmtReais(custoSelecionado)}`
                  : "Selecione pelo menos um item para importar."}
              </p>
            </div>
            <div className="flex flex-wrap justify-end gap-2 sm:shrink-0">
              <button type="button" onClick={fecharImportacao} disabled={importBusy} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-60 text-slate-300 rounded-lg text-sm font-bold">Cancelar</button>
              <button type="button" onClick={confirmarImportacao} disabled={importBusy || totalSelecionados === 0} className="px-4 sm:px-5 py-2 bg-emerald-600 enabled:hover:bg-emerald-500 disabled:opacity-60 text-white rounded-lg text-sm font-bold">{importBusy ? "Importando..." : "Confirmar importação"}</button>
            </div>
          </div>
        </dialog>
      )}

      {/* ── Modal: Histórico de movimentações ── */}
      {histProduto && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div>
                <h3 className="text-white font-black text-lg">📊 Movimentações — {histProduto.nome}</h3>
                <p className="text-slate-500 text-xs">Estoque atual: {fmtQtd(histProduto.estoque)} {histProduto.unidade}</p>
              </div>
              <button onClick={() => { setHistProduto(null); setHistMovs([]); }} className="text-slate-400 hover:text-white text-2xl leading-none">×</button>
            </div>

            <div className="flex-1 overflow-auto p-3">
              {histBusy ? (
                <p className="text-slate-500 text-sm text-center py-8">Carregando...</p>
              ) : histMovs.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-8">Nenhuma movimentação registrada.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-slate-500 text-xs uppercase text-left">
                    <tr>
                      <th className="p-2">Data</th>
                      <th className="p-2">Tipo</th>
                      <th className="p-2 text-right">Qtd</th>
                      <th className="p-2">Detalhe</th>
                    </tr>
                  </thead>
                  <tbody>
                    {histMovs.map((m) => {
                      const entrada = m.tipo === "entrada";
                      return (
                        <tr key={m.id} className="border-t border-slate-800">
                          <td className="p-2 text-slate-400 whitespace-nowrap">{fmtData(m.criado_em)}</td>
                          <td className="p-2">
                            <span className={`text-2xs font-black uppercase px-2 py-0.5 rounded ${entrada ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                              {ORIGEM_LABEL[m.origem] || m.origem || (entrada ? "Entrada" : "Saída")}
                            </span>
                          </td>
                          <td className={`p-2 text-right font-bold ${entrada ? "text-emerald-400" : "text-red-400"}`}>
                            {entrada ? "+" : "−"}{fmtQtd(m.quantidade)}
                          </td>
                          <td className="p-2 text-slate-400">
                            {m.observacao || "—"}
                            {m.documento ? <span className="text-slate-600"> · doc {m.documento}</span> : null}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
