import { useState, useEffect, useCallback } from "react";
import {
  listarProdutos,
  criarProduto,
  atualizarProduto,
  desativarProduto,
  listarCategorias,
} from "../lib/api";
import type { Produto, ProdutoInput, Categoria } from "../lib/api";

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

  useEffect(() => { carregar(); }, [carregar]);

  function resetForm() {
    setNome("");
    setCategoriaId("");
    setPrecoCusto("");
    setPrecoVenda("");
    setEstoque("0");
    setEstoqueMinimo("5");
    setCodigoBarras("");
    setUnidade("UN");
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
      unidade: unidade.trim() || "UN",
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
    <div className="flex flex-col lg:flex-row gap-4 h-full">
      {/* Lista */}
      <div className="flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-white font-bold text-lg">📦 Produtos ({produtos.length})</h2>
          <button
            onClick={abrirNovo}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            + Novo Produto
          </button>
        </div>

        <div className="flex-1 overflow-y-auto rounded-xl bg-slate-900 border border-slate-800">
          {produtos.length === 0 ? (
            <p className="text-slate-500 text-center py-12">Nenhum produto cadastrado ainda.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-800 sticky top-0">
                <tr className="text-slate-400 text-left">
                  <th className="p-3 font-medium">Nome</th>
                  <th className="p-3 font-medium hidden sm:table-cell">Custo</th>
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
                    <tr
                      key={p.id}
                      className={`border-t border-slate-800 hover:bg-slate-800/50 ${
                        !p.ativo ? "opacity-40" : ""
                      }`}
                    >
                      <td className="p-3 text-white">
                        <div className="font-medium truncate max-w-40">{p.nome}</div>
                        <div className="text-slate-500 text-xs">{p.unidade}</div>
                      </td>
                      <td className="p-3 text-slate-300 hidden sm:table-cell">
                        R$ {(p.preco_custo || 0).toFixed(2)}
                      </td>
                      <td className="p-3 text-brand-400 font-semibold">
                        R$ {(p.preco_venda || 0).toFixed(2)}
                      </td>
                      <td className="p-3 hidden md:table-cell">
                        <span className={baixo ? "text-amber-400 font-medium" : "text-slate-300"}>
                          {p.estoque}
                          {baixo && ` ⚠️`}
                        </span>
                      </td>
                      <td className="p-3 hidden md:table-cell">
                        {p.ativo ? (
                          <span className="text-green-400 text-xs bg-green-500/10 px-2 py-0.5 rounded">Ativo</span>
                        ) : (
                          <span className="text-slate-500 text-xs bg-slate-800 px-2 py-0.5 rounded">Inativo</span>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          <button
                            onClick={() => abrirEdicao(p)}
                            className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-slate-700"
                          >
                            Editar
                          </button>
                          {p.ativo ? (
                            <button
                              onClick={() => handleDesativar(p.id)}
                              className="text-red-400 hover:text-red-300 text-xs px-2 py-1 rounded hover:bg-slate-700"
                            >
                              Desativar
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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

            <button
              type="submit"
              className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-lg transition-colors"
            >
              {editando ? "Salvar Alterações" : "Criar Produto"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
