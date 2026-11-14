import { useState, useEffect, useCallback, useLayoutEffect, useRef } from "react";
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
import { estoqueBalcao } from "../lib/embalagem";
import { lerNumeroPtBr } from "../lib/numeros";

// Item da importação com flags editáveis na tela.
type ItemImport = ItemConfirmarXml & {
  acao: "atualizar" | "criar";
  estoque_atual: number;
  incluir: boolean;
  valor_unitario_xml?: number;
  perguntar_embalagem?: boolean;
  fator_entrada?: number;
};

const CAMPOS_NUMEROS_XML = {
  quantidade_xml: "Qtd XML", quantidade_por_embalagem: "Qtd/emb.",
  quantidade: "Entra", preco_custo: "Custo R$", preco_venda: "Venda R$",
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
const fmtData = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
};
const ORIGEM_LABEL: Record<string, string> = {
  manual: "Entrada manual", xml: "Entrada (XML)", venda: "Venda",
  perda: "Perda", quebra: "Quebra", inventario: "Inventário",
};

export default function ProdutosPage() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [editando, setEditando] = useState<Produto | null>(null);
  const [novo, setNovo] = useState(false);
  const [msg, setMsg] = useState<Mensagem | null>(null);

  const [vendePorUnidade, setVendePorUnidade] = useState(false);
  const [precoEmbalagem, setPrecoEmbalagem] = useState("");
  const [precoUnidade, setPrecoUnidade] = useState("");
  const [codigoUnidade, setCodigoUnidade] = useState("");

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
  const itensSelecionados = importItens.filter((item) => item.incluir);
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
      setImportItens(prev.itens.map((it) => ({
        produto_id: it.produto_id,
        vende_por_unidade: !!it.vende_por_unidade,
        preco_embalagem: it.preco_embalagem || 0,
        preco_unidade: it.preco_unidade || 0,
        unidade_xml: it.unidade_xml,
        fator_entrada: it.fator_entrada,
        perguntar_embalagem: it.perguntar_embalagem,
        nome: it.nome,
        codigo_barras: it.codigo_barras,
        unidade: it.unidade,
        unidade_compra: it.unidade_compra || it.unidade_xml || it.unidade,
        quantidade_por_embalagem: fatorSeguro(it.quantidade_por_embalagem),
        quantidade: it.quantidade,
        quantidade_xml: it.quantidade_xml ?? it.quantidade,
        preco_custo: it.valor_unitario,
        valor_unitario_xml: it.valor_unitario_xml ?? it.valor_unitario,
        preco_venda: it.preco_venda_atual ?? Number((it.valor_unitario * 1.3).toFixed(2)),
        atualizar_custo: true,
        ncm: it.ncm,
        cfop: it.cfop,
        acao: it.acao,
        estoque_atual: it.estoque_atual,
        incluir: true,
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
      if (["quantidade_por_embalagem", "quantidade_xml", "confirmar_abertura", "unidade_compra"].includes(campo)) {
        const fator = next.confirmar_abertura ? fatorSeguro(next.quantidade_por_embalagem)
          : next.vende_por_unidade ? (next.unidade_xml === next.unidade_compra ? fatorSeguro(next.quantidade_por_embalagem) : 1)
          : next.unidade_xml === 'UN' ? 1 : fatorSeguro(next.quantidade_por_embalagem);
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

  function fecharImportacao() {
    importDialogRef.current?.close();
    setImportInfo(null);
    setImportItens([]);
    setImportTextos({});
    setImportMsg(null);
  }

  const textoImport = (i: number, campo: CampoNumeroXml) =>
    importTextos[`${i}:${campo}`] ?? String(importItens[i]?.[campo] ?? 0);

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
      for (const campo of Object.keys(CAMPOS_NUMEROS_XML) as CampoNumeroXml[]) {
        if ((campo === 'preco_embalagem' || campo === 'preco_unidade') && !it.confirmar_abertura) continue;
        const numero = lerNumeroPtBr(textoImport(i, campo));
        if (numero === null || !numeroXmlValido(campo, numero)) {
          setImportMsg({ tipo: "erro", texto: `Item ${i + 1}: valor inválido em ${CAMPOS_NUMEROS_XML[campo]}.` });
          return;
        }
      }
      if (it.confirmar_abertura && (!(Number(it.preco_embalagem) > 0) || !(Number(it.preco_unidade) > 0) || !Number.isInteger(it.quantidade_por_embalagem) || !it.unidade_compra || it.unidade_compra === 'UN')) {
        setImportMsg({tipo:'erro',texto:`Item ${i + 1}: informe embalagem, quantidade inteira e os dois preços maiores que zero.`}); return;
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
    const q = prompt(`Entrada de estoque — "${p.nome}"\nQuantidade a adicionar em ${p.unidade}:`, "1");
    if (q === null) return;
    const qtd = lerNumeroPtBr(q);
    if (qtd === null || qtd <= 0) { setMsg({ tipo: "erro", texto: "Quantidade inválida." }); return; }
    try {
      await entradaEstoque(p.id, qtd);
      setMsg({ tipo: "ok", texto: `+${fmtQtd(qtd)} ${p.unidade} em "${p.nome}".` });
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

  async function handleSalvar(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
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
    if (precoVenda.trim() !== "") {
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
      preco_venda: valVenda,
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
          <h2 className="text-white font-bold text-base sm:text-lg">📦 Produtos ({produtos.length})</h2>
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
          {produtos.length === 0 ? (
            <p className="text-slate-500 text-center py-12 text-sm">Nenhum produto cadastrado ainda.</p>
          ) : (
            <>
              {/* Cards mobile: evita tabela espremida em telas pequenas */}
              <div className="sm:hidden grid gap-2 p-2">
                {produtos.map((p) => {
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
                  {produtos.map((p) => {
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
            <label className="flex items-center gap-3 rounded-xl border border-brand-500/40 bg-brand-500/10 p-3 text-white">
              <input type="checkbox" checked={vendePorUnidade} onChange={e => {
                setVendePorUnidade(e.target.checked);
                if (e.target.checked && !editando?.vende_por_unidade) {setPrecoEmbalagem(""); setPrecoUnidade("");}
              }} className="h-5 w-5 accent-brand-500" />Também vende por unidade
            </label>
            {vendePorUnidade && <fieldset className="space-y-3 rounded-xl border border-brand-500/30 p-3">
              <legend className="text-brand-300 text-sm">Dois preços independentes</legend>
              <label className="block text-slate-300 text-sm">Preço da embalagem fechada (R$)
                <input aria-label="Preço da embalagem fechada" value={precoEmbalagem} onChange={e=>setPrecoEmbalagem(e.target.value)} inputMode="decimal" className="w-full rounded-lg bg-slate-800 p-2 text-white" required />
              </label>
              <label className="block text-slate-300 text-sm">Preço da unidade (R$)
                <input aria-label="Preço da unidade" value={precoUnidade} onChange={e=>setPrecoUnidade(e.target.value)} inputMode="decimal" className="w-full rounded-lg bg-slate-800 p-2 text-white" required />
              </label>
              <label className="block text-slate-300 text-sm">Código da unidade (opcional)
                <input aria-label="Código da unidade" value={codigoUnidade} onChange={e=>setCodigoUnidade(e.target.value)} className="w-full rounded-lg bg-slate-800 p-2 text-white" />
              </label>
              <p className="text-xs text-slate-400">Estoque e custo sempre por unidade. O código principal lança a embalagem fechada no caixa.</p>
            </fieldset>}

            <div>
              <label className="text-slate-400 text-xs block mb-0.5">Nome *</label>
              <input
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                placeholder="Ex: Arroz 5kg"
                autoFocus
              />
            </div>

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
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Preço Venda</label>
                <input
                  type="text"
                  inputMode="decimal"
                  value={precoVenda}
                  onChange={(e) => setPrecoVenda(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  placeholder="0,00"
                />
              </div>
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
                <label className="text-slate-400 text-xs block mb-0.5">Código Barras</label>
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
                <label className="text-slate-400 text-xs block mb-0.5">Unidade da compra</label>
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
              </div>
            </div>

            {vendePorUnidade && editando && editando.estoque > 0 && Number(quantidadePorEmbalagem) !== editando.quantidade_por_embalagem && <p role="status" className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-300">Alterar a quantidade por embalagem não reconta o estoque: continuam {fmtQtd(editando.estoque)} unidades.</p>}
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
          className="fixed inset-0 m-auto w-[calc(100%-1.5rem)] max-w-6xl max-h-[90dvh] open:flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 text-slate-100 backdrop:bg-black/80 backdrop:backdrop-blur-sm"
        >
          <div className="flex shrink-0 items-start justify-between gap-3 p-4 border-b border-slate-800">
            <div>
              <h3 id="importar-xml-titulo" className="text-white font-black text-base sm:text-lg">📄 Importar XML — entrada de estoque</h3>
              <p className="text-slate-400 text-xs">{importInfo.emitente || "Fornecedor"} · NF {importInfo.numero || "—"}</p>
            </div>
            <button type="button" aria-label="Fechar prévia do XML" onClick={fecharImportacao} disabled={importBusy} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-60 text-2xl leading-none">×</button>
          </div>

          {importMsg?.tipo === "erro" && (
            <p role="alert" className="mx-4 mt-3 shrink-0 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{importMsg.texto}</p>
          )}

          <div className="min-h-0 flex-1 overflow-auto px-3">
            <fieldset disabled={importBusy} className="min-w-0">
              <legend className="sr-only">Itens do XML</legend>
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-slate-900 text-slate-300 text-xs uppercase text-left">
                  <tr>
                    <th scope="col" className="p-2">
                      <label className="flex w-fit cursor-pointer items-center gap-2 whitespace-nowrap py-2 normal-case">
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
                        Todos
                      </label>
                    </th>
                    <th className="p-2">Produto</th>
                    <th className="p-2">Ação</th>
                    <th className="p-2 w-24">Un. venda</th>
                    <th className="p-2 w-24">Un. XML</th>
                    <th className="p-2 w-24">Qtd XML</th>
                    <th className="p-2 w-24">Qtd/emb.</th>
                    <th className="p-2 w-24">Entra</th>
                    <th className="p-2 w-24">Custo R$</th>
                    <th className="p-2 w-24">Venda R$</th>
                  </tr>
                </thead>
                <tbody>
                  {importItens.map((it, i) => (
                    <tr key={i} className={`border-t border-slate-800 ${it.incluir ? "bg-brand-500/5" : "bg-slate-950/40"}`}>
                      <td className="p-2">
                        <label className="flex w-fit cursor-pointer items-center rounded-lg px-2 py-2 hover:bg-slate-800">
                          <input type="checkbox" checked={it.incluir} onChange={(e) => setItem(i, "incluir", e.target.checked)} className={CHECKBOX_IMPORTACAO} />
                          <span className="sr-only">Incluir {it.nome || `item ${i + 1}`}</span>
                        </label>
                      </td>
                      <td className="p-2">
                        <input value={it.nome} onChange={(e) => setItem(i, "nome", e.target.value)} className="w-full min-w-52 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" />
                        <div className="text-slate-500 text-2xs">{it.codigo_barras || "sem código"} · {it.unidade}</div>
                        <p className="mt-2 text-xs text-emerald-300">{fmtQtd(it.quantidade_xml || it.quantidade)} {it.unidade_xml || it.unidade_compra} viram {fmtQtd(it.quantidade)} {it.confirmar_abertura ? 'UN' : it.unidade}; custo de cada unidade R$ {it.preco_custo.toFixed(4)}.{it.acao === 'atualizar' ? ' Preços de venda mantidos.' : ''}</p>
                        {it.acao === 'criar' && (it.perguntar_embalagem || it.unidade_xml !== 'UN') && <div className="mt-3 space-y-2 rounded-lg border border-brand-500/30 bg-brand-500/10 p-3">
                          <label className="flex gap-2 text-sm text-white"><input type="checkbox" className={CHECKBOX_IMPORTACAO} checked={!!it.confirmar_abertura} onChange={e=>setItem(i,'confirmar_abertura',e.target.checked)} />Isto é embalagem fechada que também vende por unidade?</label>
                          <p className="text-xs text-slate-400">O número no nome não altera a quantidade. Sem confirmação, UN entra unidade a unidade.</p>
                          {it.confirmar_abertura && <>
                            <label className="block text-xs text-slate-300">Nome da embalagem<input aria-label={`Embalagem do item ${i+1}`} value={it.unidade_compra} onChange={e=>setItem(i,'unidade_compra',e.target.value.toUpperCase())} className="mt-1 w-full rounded bg-slate-950 p-2 text-white" /></label>
                            {(['preco_embalagem','preco_unidade'] as const).map(campo=><label key={campo} className="block text-xs text-slate-300">{CAMPOS_NUMEROS_XML[campo]} (R$)<input aria-label={`${CAMPOS_NUMEROS_XML[campo]} do item ${i+1}`} inputMode="decimal" value={textoImport(i,campo)} onChange={e=>editarNumeroImport(i,campo,e.target.value)} className="mt-1 w-full rounded bg-slate-950 p-2 text-white" /></label>)}
                          </>}
                        </div>}
                      </td>
                      <td className="p-2">
                        {it.acao === "atualizar"
                          ? <span className="block whitespace-nowrap text-emerald-300 text-xs font-medium">Repor estoque <span className="block font-normal text-slate-400">Atual: {fmtQtd(it.estoque_atual)}</span></span>
                          : <span className="whitespace-nowrap text-amber-300 text-xs font-medium">Criar produto</span>}
                      </td>
                      <td className="p-2">
                        <select value={it.unidade} onChange={(e) => setItem(i, "unidade", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white">
                          {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
                        </select>
                      </td>
                      <td className="p-2">
                        <select value={it.unidade_compra} onChange={(e) => setItem(i, "unidade_compra", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white">
                          {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
                        </select>
                      </td>
                      <td className="p-2"><input type="text" inputMode="decimal" value={textoImport(i, "quantidade_xml")} onChange={(e) => editarNumeroImport(i, "quantidade_xml", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2"><input type="text" inputMode="decimal" value={textoImport(i, "quantidade_por_embalagem")} onChange={(e) => editarNumeroImport(i, "quantidade_por_embalagem", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2"><input type="text" inputMode="decimal" value={textoImport(i, "quantidade")} onChange={(e) => editarNumeroImport(i, "quantidade", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2"><input type="text" inputMode="decimal" value={textoImport(i, "preco_custo")} onChange={(e) => editarNumeroImport(i, "preco_custo", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2">
                        {it.acao === "criar"
                          ? <input type="text" inputMode="decimal" value={textoImport(i, "preco_venda")} onChange={(e) => editarNumeroImport(i, "preco_venda", e.target.value)} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" />
                          : <span className="text-slate-600 text-xs">mantém</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </fieldset>
          </div>

          <div className="p-3 sm:p-4 border-t border-slate-800 flex shrink-0 flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div role="status" aria-atomic="true" className="space-y-1">
              <p className="text-white text-sm font-semibold">{totalSelecionados} de {importItens.length} itens selecionados</p>
              <p className="text-slate-400 text-xs">
                {totalSelecionados > 0
                  ? `${totalNovos} para criar · ${totalSelecionados - totalNovos} para repor`
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
