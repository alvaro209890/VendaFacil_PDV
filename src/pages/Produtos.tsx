import { useState, useEffect, useCallback, useRef } from "react";
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
} from "../lib/api";
import type {
  Produto, ProdutoInput, Categoria, CamposFiscais, PreviewXml, ItemConfirmarXml,
} from "../lib/api";

// Item da importação com flags editáveis na tela.
type ItemImport = ItemConfirmarXml & {
  acao: "atualizar" | "criar";
  estoque_atual: number;
  incluir: boolean;
  valor_unitario_xml?: number;
};

const FISCAL_VAZIO: CamposFiscais = {
  ncm: "", cest: "", cfop: "5102", origem: "0", unidade_tributavel: "",
  cst_csosn: "102", cst_pis: "07", cst_cofins: "07",
};

const UNIDADES = ["UN", "KG", "G", "LT", "ML", "CX", "FD", "PCT", "SC"];
const normUn = (v: string, fallback = "UN") => (v || fallback).trim().toUpperCase() || fallback;
const fatorSeguro = (v: number | string | undefined) => Math.max(Number(v) || 1, 0.0001);
const fmtQtd = (v: number) => Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });

export default function ProdutosPage() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [editando, setEditando] = useState<Produto | null>(null);
  const [novo, setNovo] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

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
  const [importInfo, setImportInfo] = useState<{ emitente: string; numero: string; chave: string } | null>(null);
  const [importItens, setImportItens] = useState<ItemImport[]>([]);
  const [importBusy, setImportBusy] = useState(false);

  async function onXmlEscolhido(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // permite reimportar o mesmo arquivo
    if (!file) return;
    setImportBusy(true);
    setMsg(null);
    try {
      const prev: PreviewXml = await importarXmlPreview(file);
      setImportInfo({ emitente: prev.emitente, numero: prev.numero, chave: prev.chave });
      setImportItens(prev.itens.map((it) => ({
        produto_id: it.produto_id,
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
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setImportBusy(false);
    }
  }

  const setItem = (i: number, campo: keyof ItemImport, valor: string | number | boolean) =>
    setImportItens((arr) => arr.map((it, idx) => {
      if (idx !== i) return it;
      const next = { ...it, [campo]: valor };
      if (campo === "quantidade_por_embalagem" || campo === "quantidade_xml") {
        const fator = fatorSeguro(next.quantidade_por_embalagem);
        const qtdXml = Number(next.quantidade_xml || 0);
        next.quantidade_por_embalagem = fator;
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

  async function confirmarImportacao() {
    const sel = importItens.filter((it) => it.incluir && it.quantidade > 0);
    if (sel.length === 0) {
      setMsg({ tipo: "erro", texto: "Selecione ao menos um item para importar." });
      return;
    }
    setImportBusy(true);
    try {
      const doc = importInfo ? (importInfo.numero || importInfo.chave) : "";
      const itens: ItemConfirmarXml[] = sel.map((it) => ({
        produto_id: it.produto_id,
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
      const r = await importarXmlConfirmar(doc, itens);
      setImportInfo(null);
      setImportItens([]);
      setMsg({ tipo: "ok", texto: `Importado! ${r.atualizados} atualizado(s), ${r.criados} novo(s).` });
      carregar();
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setImportBusy(false);
    }
  }

  async function entradaRapida(p: Produto) {
    const q = prompt(`Entrada de estoque — "${p.nome}"\nQuantidade a adicionar em ${p.unidade}:`, "1");
    if (q === null) return;
    const qtd = Number(q);
    if (!qtd || qtd <= 0) { setMsg({ tipo: "erro", texto: "Quantidade inválida." }); return; }
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
    const qtd = Number(q);
    if (qtd < 0 || Number.isNaN(qtd) || (tipo !== "inventario" && qtd <= 0)) {
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

    const data: ProdutoInput = {
      nome: nome.trim(),
      categoria_id: categoriaId || undefined,
      preco_custo: Number(precoCusto) || 0,
      preco_venda: Number(precoVenda) || 0,
      estoque: Number(estoque) || 0,
      estoque_minimo: Number(estoqueMinimo) || 0,
      codigo_barras: codigoBarras.trim(),
      unidade: normUn(unidade),
      unidade_compra: normUn(unidadeCompra, unidade),
      quantidade_por_embalagem: fatorSeguro(quantidadePorEmbalagem),
      ncm: (fiscal.ncm || "").trim(),
      cest: (fiscal.cest || "").trim(),
      cfop: (fiscal.cfop || "").trim(),
      origem: fiscal.origem || "0",
      unidade_tributavel: (fiscal.unidade_tributavel || "").trim(),
      cst_csosn: (fiscal.cst_csosn || "").trim(),
      aliquota_icms: Number(fiscal.aliquota_icms) || 0,
      cst_pis: (fiscal.cst_pis || "").trim(),
      aliquota_pis: Number(fiscal.aliquota_pis) || 0,
      cst_cofins: (fiscal.cst_cofins || "").trim(),
      aliquota_cofins: Number(fiscal.aliquota_cofins) || 0,
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
                            estoque <span className={baixo ? "text-amber-400" : "text-slate-300"}>{fmtQtd(p.estoque)} {p.unidade}{baixo ? " ⚠️" : ""}</span>
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
                          <p className="text-brand-400 font-semibold">R$ {(p.preco_venda || 0).toFixed(2)}</p>
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
                        <td className="p-3 text-brand-400 font-semibold">R$ {(p.preco_venda || 0).toFixed(2)}</td>
                        <td className="p-3 hidden md:table-cell">
                          <span className={baixo ? "text-amber-400 font-medium" : "text-slate-300"}>{fmtQtd(p.estoque)} {p.unidade}{baixo && ` ⚠️`}</span>
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
                  type="number"
                  value={precoCusto}
                  onChange={(e) => setPrecoCusto(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  step="0.01"
                  min="0"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Preço Venda</label>
                <input
                  type="number"
                  value={precoVenda}
                  onChange={(e) => setPrecoVenda(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  step="0.01"
                  min="0"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Estoque</label>
                <input
                  type="number"
                  value={estoque}
                  onChange={(e) => setEstoque(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  min="0"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Estoque Mínimo</label>
                <input
                  type="number"
                  value={estoqueMinimo}
                  onChange={(e) => setEstoqueMinimo(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  min="0"
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
                <select
                  value={unidadeCompra}
                  onChange={(e) => setUnidadeCompra(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                >
                  {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
              <div>
                <label className="text-slate-400 text-xs block mb-0.5">Qtd por compra</label>
                <input
                  type="number"
                  value={quantidadePorEmbalagem}
                  onChange={(e) => setQuantidadePorEmbalagem(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500"
                  step="0.001"
                  min="0.001"
                />
              </div>
            </div>

            <div className="border border-slate-800 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => setMostrarFiscal((v) => !v)}
                className="w-full flex items-center justify-between px-3 py-2 bg-slate-800/60 text-slate-300 text-xs font-bold uppercase tracking-wide"
              >
                <span>🧾 Dados fiscais (NFC-e)</span>
                <span>{mostrarFiscal ? "−" : "+"}</span>
              </button>
              {mostrarFiscal && (
                <div className="p-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-slate-400 text-xs block mb-0.5">NCM</label>
                      <input value={fiscal.ncm} onChange={(e) => setF("ncm", e.target.value)} placeholder="8 dígitos" className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500" />
                    </div>
                    <div>
                      <label className="text-slate-400 text-xs block mb-0.5">CFOP</label>
                      <input value={fiscal.cfop} onChange={(e) => setF("cfop", e.target.value)} placeholder="5102" className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500" />
                    </div>
                    <div>
                      <label className="text-slate-400 text-xs block mb-0.5">CEST</label>
                      <input value={fiscal.cest} onChange={(e) => setF("cest", e.target.value)} placeholder="opcional" className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500" />
                    </div>
                    <div>
                      <label className="text-slate-400 text-xs block mb-0.5">Origem</label>
                      <input value={fiscal.origem} onChange={(e) => setF("origem", e.target.value)} placeholder="0" className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500" />
                    </div>
                    <div>
                      <label className="text-slate-400 text-xs block mb-0.5">CST/CSOSN</label>
                      <input value={fiscal.cst_csosn} onChange={(e) => setF("cst_csosn", e.target.value)} placeholder="102" className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500" />
                    </div>
                    <div>
                      <label className="text-slate-400 text-xs block mb-0.5">Alíq. ICMS %</label>
                      <input type="number" step="0.01" value={fiscal.aliquota_icms ?? ""} onChange={(e) => setF("aliquota_icms", e.target.value)} placeholder="0" className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500" />
                    </div>
                  </div>
                  <p className="text-slate-500 text-[11px] leading-snug">
                    No Simples Nacional use CSOSN (ex.: 102). NCM e CFOP são obrigatórios para emitir. Em dúvida, consulte seu contador.
                  </p>
                </div>
              )}
            </div>

            <button
              type="submit"
              className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors"
            >
              {editando ? "Salvar Alterações" : "Criar Produto"}
            </button>
          </form>
        </div>
      )}

      {/* ── Modal: Importar XML (NF-e) ── */}
      {importInfo && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-6xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <div>
                <h3 className="text-white font-black text-lg">📄 Importar XML — entrada de estoque</h3>
                <p className="text-slate-500 text-xs">{importInfo.emitente || "Fornecedor"} · NF {importInfo.numero || "—"}</p>
              </div>
              <button onClick={() => { setImportInfo(null); setImportItens([]); }} className="text-slate-400 hover:text-white text-2xl leading-none">×</button>
            </div>

            <div className="flex-1 overflow-auto p-3">
              <table className="w-full text-sm">
                <thead className="text-slate-500 text-xs uppercase text-left">
                  <tr>
                    <th className="p-2">Imp.</th>
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
                    <tr key={i} className={`border-t border-slate-800 ${!it.incluir ? "opacity-40" : ""}`}>
                      <td className="p-2"><input type="checkbox" checked={it.incluir} onChange={(e) => setItem(i, "incluir", e.target.checked)} className="w-4 h-4 accent-brand-500" /></td>
                      <td className="p-2">
                        <input value={it.nome} onChange={(e) => setItem(i, "nome", e.target.value)} className="w-full min-w-52 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" />
                        <div className="text-slate-500 text-2xs">{it.codigo_barras || "sem código"} · {it.unidade}</div>
                      </td>
                      <td className="p-2">
                        {it.acao === "atualizar"
                          ? <span className="text-emerald-400 text-xs">repor (tem {it.estoque_atual})</span>
                          : <span className="text-amber-400 text-xs">criar novo</span>}
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
                      <td className="p-2"><input type="number" step="0.001" value={it.quantidade_xml} onChange={(e) => setItem(i, "quantidade_xml", Number(e.target.value))} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2"><input type="number" step="0.001" value={it.quantidade_por_embalagem} onChange={(e) => setItem(i, "quantidade_por_embalagem", Number(e.target.value))} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2"><input type="number" step="0.001" value={it.quantidade} onChange={(e) => setItem(i, "quantidade", Number(e.target.value))} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2"><input type="number" step="0.01" value={it.preco_custo} onChange={(e) => setItem(i, "preco_custo", Number(e.target.value))} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" /></td>
                      <td className="p-2">
                        {it.acao === "criar"
                          ? <input type="number" step="0.01" value={it.preco_venda} onChange={(e) => setItem(i, "preco_venda", Number(e.target.value))} className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-white" />
                          : <span className="text-slate-600 text-xs">mantém</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t border-slate-800 flex items-center justify-between gap-3">
              <p className="text-slate-500 text-xs">Confira quantidades e custos. "Repor" soma ao estoque atual; "criar novo" cadastra o produto.</p>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => { setImportInfo(null); setImportItens([]); }} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-bold">Cancelar</button>
                <button onClick={confirmarImportacao} disabled={importBusy} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white rounded-lg text-sm font-bold">{importBusy ? "Importando..." : "Confirmar importação"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
