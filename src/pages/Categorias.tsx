import { useState, useEffect, useCallback } from "react";
import {
  listarCategorias,
  criarCategoria,
  atualizarCategoria,
  removerCategoria,
  type Categoria,
} from "../lib/api";

export default function CategoriasPage() {
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState<Categoria | null>(null);
  const [nome, setNome] = useState("");
  const [cor, setCor] = useState("#6366f1");
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const data = await listarCategorias();
      setCategorias(data.categorias);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  function resetForm() {
    setNome("");
    setCor("#6366f1");
    setEditando(null);
  }

  function abrirEdicao(c: Categoria) {
    setNome(c.nome);
    setCor(c.cor);
    setEditando(c);
    setShowModal(true);
  }

  async function handleSalvar() {
    if (!nome.trim()) {
      setMsg({ tipo: "erro", texto: "Nome é obrigatório." });
      return;
    }
    setMsg(null);
    try {
      if (editando) {
        await atualizarCategoria(editando.id, { nome: nome.trim(), cor });
        setMsg({ tipo: "ok", texto: "Categoria atualizada!" });
      } else {
        await criarCategoria({ nome: nome.trim(), cor });
        setMsg({ tipo: "ok", texto: "Categoria criada!" });
      }
      setShowModal(false);
      resetForm();
      await carregar();
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  async function handleRemover(id: number) {
    if (!confirm("Remover esta categoria? Os produtos ficarão sem categoria.")) return;
    try {
      await removerCategoria(id);
      await carregar();
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao remover categoria." });
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
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Categorias</h1>
          <p className="text-slate-400 text-sm mt-1">{categorias.length} categoria(s)</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowModal(true); }}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Nova Categoria
        </button>
      </div>

      {msg && (
        <div className={`p-3 rounded-lg text-sm ${msg.tipo === "ok" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"}`}>
          {msg.texto}
        </div>
      )}

      {categorias.length === 0 ? (
        <div className="text-center py-12 text-slate-500">Nenhuma categoria cadastrada.</div>
      ) : (
        <div className="grid gap-2">
          {categorias.map((c) => (
            <div key={c.id} className="bg-slate-900 rounded-xl p-4 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: c.cor }} />
                <div>
                  <span className="text-white font-medium">{c.nome}</span>
                  <span className="text-slate-500 text-sm ml-2">({c.total_produtos} produtos)</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => abrirEdicao(c)} className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors">
                  Editar
                </button>
                <button onClick={() => handleRemover(c.id)} className="px-3 py-1.5 text-xs bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded-lg transition-colors">
                  Remover
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
          <div className="bg-slate-900 rounded-2xl p-6 w-full max-w-sm border border-slate-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">{editando ? "Editar Categoria" : "Nova Categoria"}</h2>
            <div className="space-y-3">
              <input
                placeholder="Nome da categoria"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <div className="flex items-center gap-3">
                <label className="text-slate-400 text-sm">Cor:</label>
                <input type="color" value={cor} onChange={(e) => setCor(e.target.value)} className="w-10 h-10 rounded cursor-pointer bg-transparent border-0" />
                <span className="text-slate-500 text-xs">{cor}</span>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => { setShowModal(false); resetForm(); }} className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                Cancelar
              </button>
              <button onClick={handleSalvar} className="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors">
                {editando ? "Atualizar" : "Criar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
