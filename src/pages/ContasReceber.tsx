import { useState, useEffect, useCallback } from "react";
import {
  listarContasReceber,
  criarContaReceber,
  pagarContaReceber,
  cancelarContaReceber,
  listarClientes,
  type ContaReceber,
  type Cliente,
} from "../lib/api";

const STATUS_LABELS: Record<string, string> = {
  pendente: "Pendente",
  parcial: "Parcial",
  pago: "Pago",
  cancelado: "Cancelado",
};

const STATUS_COLORS: Record<string, string> = {
  pendente: "bg-yellow-900/30 text-yellow-400 border-yellow-800",
  parcial: "bg-blue-900/30 text-blue-400 border-blue-800",
  pago: "bg-green-900/30 text-green-400 border-green-800",
  cancelado: "bg-slate-800 text-slate-500 border-slate-700",
};

export default function ContasReceber() {
  const [contas, setContas] = useState<ContaReceber[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState<string>("pendente");
  const [showModal, setShowModal] = useState(false);
  const [formClienteId, setFormClienteId] = useState<number | "">("");
  const [formValor, setFormValor] = useState("");
  const [formVencimento, setFormVencimento] = useState("");
  const [formObs, setFormObs] = useState("");
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [data, cli] = await Promise.all([
        listarContasReceber(filtro || undefined),
        listarClientes(),
      ]);
      setContas(data.contas);
      setClientes(cli.clientes);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [filtro]);

  useEffect(() => { carregar(); }, [carregar]);

  function resetForm() {
    setFormClienteId("");
    setFormValor("");
    setFormVencimento("");
    setFormObs("");
  }

  async function handleCriar() {
    if (!formValor || parseFloat(formValor) <= 0) {
      setMsg({ tipo: "erro", texto: "Valor inválido." });
      return;
    }
    setMsg(null);
    try {
      await criarContaReceber({
        cliente_id: formClienteId || null,
        valor_total: parseFloat(formValor),
        data_vencimento: formVencimento || null,
        observacao: formObs,
      });
      setShowModal(false);
      resetForm();
      await carregar();
      setMsg({ tipo: "ok", texto: "Conta criada!" });
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  async function handlePagar(conta: ContaReceber) {
    const valorStr = prompt(`Valor a receber (R$ ${conta.valor_pendente.toFixed(2)}):`, conta.valor_pendente.toFixed(2));
    if (!valorStr) return;
    const valor = parseFloat(valorStr);
    if (valor <= 0 || valor > conta.valor_pendente) {
      setMsg({ tipo: "erro", texto: "Valor inválido." });
      return;
    }
    try {
      await pagarContaReceber(conta.id, { valor });
      await carregar();
      setMsg({ tipo: "ok", texto: "Pagamento registrado!" });
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    }
  }

  async function handleCancelar(id: number) {
    if (!confirm("Cancelar esta conta?")) return;
    try {
      await cancelarContaReceber(id);
      await carregar();
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao cancelar." });
    }
  }

  const totalPendente = contas
    .filter((c) => c.status === "pendente" || c.status === "parcial")
    .reduce((acc, c) => acc + c.valor_pendente, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Contas a Receber</h1>
          <p className="text-slate-400 text-sm mt-1">
            Total pendente: <span className="text-brand-400 font-medium">R$ {totalPendente.toFixed(2)}</span>
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setShowModal(true); }}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Nova Conta
        </button>
      </div>

      {msg && (
        <div className={`p-3 rounded-lg text-sm ${msg.tipo === "ok" ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"}`}>
          {msg.texto}
        </div>
      )}

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap">
        {["", "pendente", "parcial", "pago", "cancelado"].map((s) => (
          <button
            key={s}
            onClick={() => setFiltro(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filtro === s
                ? "bg-brand-600/20 text-brand-400 border border-brand-600/30"
                : "bg-slate-800 text-slate-400 hover:text-white border border-slate-700"
            }`}
          >
            {s ? STATUS_LABELS[s] : "Todas"}
          </button>
        ))}
      </div>

      {/* Lista */}
      {contas.length === 0 ? (
        <div className="text-center py-12 text-slate-500">Nenhuma conta encontrada.</div>
      ) : (
        <div className="grid gap-3">
          {contas.map((c) => (
            <div key={c.id} className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-white font-medium">{c.cliente_nome || "Sem cliente"}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs border ${STATUS_COLORS[c.status] || ""}`}>
                      {STATUS_LABELS[c.status] || c.status}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm">
                    <span className="text-brand-400 font-semibold">
                      R$ {c.valor_total.toFixed(2)}
                      {c.valor_pendente < c.valor_total && (
                        <span className="text-slate-400 font-normal ml-1">
                          (R$ {c.valor_pendente.toFixed(2)} pendente)
                        </span>
                      )}
                    </span>
                    {c.data_vencimento && <span className="text-slate-400">Vence: {c.data_vencimento}</span>}
                    {c.observacao && <span className="text-slate-500 text-xs">{c.observacao}</span>}
                  </div>
                </div>
                {(c.status === "pendente" || c.status === "parcial") && (
                  <div className="flex gap-2 ml-4 shrink-0">
                    <button
                      onClick={() => handlePagar(c)}
                      className="px-3 py-1.5 text-xs bg-green-900/30 hover:bg-green-900/50 text-green-400 rounded-lg transition-colors"
                    >
                      Receber
                    </button>
                    <button
                      onClick={() => handleCancelar(c.id)}
                      className="px-3 py-1.5 text-xs bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded-lg transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowModal(false)}>
          <div className="bg-slate-900 rounded-2xl p-6 w-full max-w-md border border-slate-800 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-white mb-4">Nova Conta a Receber</h2>
            <div className="space-y-3">
              <select
                value={formClienteId}
                onChange={(e) => setFormClienteId(e.target.value ? parseInt(e.target.value) : "")}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              >
                <option value="">Sem cliente (avulso)</option>
                {clientes.map((cl) => (
                  <option key={cl.id} value={cl.id}>{cl.nome}</option>
                ))}
              </select>
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="Valor *"
                value={formValor}
                onChange={(e) => setFormValor(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <input
                type="date"
                value={formVencimento}
                onChange={(e) => setFormVencimento(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
              <input
                placeholder="Observação"
                value={formObs}
                onChange={(e) => setFormObs(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-brand-500 outline-none text-sm"
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => { setShowModal(false); resetForm(); }} className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                Cancelar
              </button>
              <button onClick={handleCriar} className="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors">
                Criar Conta
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
