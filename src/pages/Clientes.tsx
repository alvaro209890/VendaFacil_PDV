import { useState, useEffect, useCallback } from "react";
import {
  listarClientes,
  criarCliente,
  atualizarCliente,
  removerCliente,
  type Cliente,
  type ClienteInput,
} from "../lib/api";

export default function Clientes() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState<Cliente | null>(null);
  const [form, setForm] = useState<ClienteInput>({ nome: "", telefone: "", email: "", endereco: "", observacao: "" });
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const data = await listarClientes();
      setClientes(data.clientes);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  function resetForm() {
    setForm({ nome: "", telefone: "", email: "", endereco: "", observacao: "" });
    setEditando(null);
  }

  function abrirEdicao(c: Cliente) {
    setForm({ nome: c.nome, telefone: c.telefone, email: c.email, endereco: c.endereco, observacao: c.observacao });
    setEditando(c);
    setShowModal(true);
  }

  async function handleSalvar() {
    if (!form.nome.trim()) {
      setMsg({ tipo: "erro", texto: "Nome é obrigatório." });
      return;
    }
    setMsg(null);
    try {
      if (editando) {
        await atualizarCliente(editando.id, form);
        setMsg({ tipo: "ok", texto: "Cliente atualizado!" });
      } else {
        await criarCliente(form);
        setMsg({ tipo: "ok", texto: "Cliente cadastrado!" });
      }
      setShowModal(false);
      resetForm();
      await carregar();
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  async function handleRemover(id: number) {
    if (!confirm("Remover este cliente?")) return;
    try {
      await removerCliente(id);
      await carregar();
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao remover cliente." });
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
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Clientes</h1>
          <p className="text-slate-400 text-sm mt-1">{clientes.length} cliente(s) cadastrado(s)</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowModal(true); }}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Novo Cliente
        </button>
      </div>

      {msg && (
        <div className={`p-3 rounded-lg text-sm ${msg.tipo === "ok" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"}`}>
          {msg.texto}
        </div>
      )}

      {/* Lista */}
      {clientes.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          Nenhum cliente cadastrado ainda.
        </div>
      ) : (
        <div className="grid gap-3">
          {clientes.map((c) => (
            <div key={c.id} className="bg-slate-900 rounded-xl p-4 border border-slate-800 flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <h3 className="text-white font-medium">{c.nome}</h3>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-sm text-slate-400">
                  {c.telefone && <span>📞 {c.telefone}</span>}
                  {c.email && <span>✉️ {c.email}</span>}
                  {c.endereco && <span>📍 {c.endereco}</span>}
                </div>
                {c.observacao && <p className="text-xs text-slate-500 mt-1">{c.observacao}</p>}
              </div>
              <div className="flex gap-2 ml-4 shrink-0">
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

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
          <div className="bg-slate-900 rounded-2xl p-6 w-full max-w-md border border-slate-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">{editando ? "Editar Cliente" : "Novo Cliente"}</h2>
            <div className="space-y-3">
              <input
                placeholder="Nome *"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <input
                placeholder="Telefone"
                value={form.telefone}
                onChange={(e) => setForm({ ...form, telefone: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <input
                placeholder="Email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <input
                placeholder="Endereço"
                value={form.endereco}
                onChange={(e) => setForm({ ...form, endereco: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <textarea
                placeholder="Observação"
                value={form.observacao}
                onChange={(e) => setForm({ ...form, observacao: e.target.value })}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm resize-none"
                rows={2}
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => { setShowModal(false); resetForm(); }} className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                Cancelar
              </button>
              <button onClick={handleSalvar} className="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors">
                {editando ? "Atualizar" : "Cadastrar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
