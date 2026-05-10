import { useState, useEffect, useCallback } from "react";
import { listarVendas, obterVenda } from "../lib/api";
import type { Venda } from "../lib/api";

export default function VendasPage() {
  const [vendas, setVendas] = useState<Venda[]>([]);
  const [loading, setLoading] = useState(true);
  const [detalhe, setDetalhe] = useState<Venda | null>(null);

  const carregar = useCallback(async () => {
    try {
      const res = await listarVendas(100);
      setVendas(res.vendas);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  async function verDetalhe(id: number) {
    try {
      const res = await obterVenda(id);
      setDetalhe(res.venda);
    } catch {
      // silent
    }
  }

  const totalHoje = vendas
    .filter((v) => {
      const hoje = new Date().toLocaleDateString("pt-BR");
      const dataVenda = new Date(v.criado_em).toLocaleDateString("pt-BR");
      return dataVenda === hoje;
    })
    .reduce((s, v) => s + v.total, 0);

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
          <h2 className="text-white font-bold text-lg">🧾 Histórico de Vendas</h2>
          <span className="text-slate-400 text-sm">Hoje: R$ {totalHoje.toFixed(2)}</span>
        </div>

        <div className="flex-1 overflow-y-auto rounded-xl bg-slate-900 border border-slate-800">
          {vendas.length === 0 ? (
            <p className="text-slate-500 text-center py-12">Nenhuma venda realizada.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-800 sticky top-0">
                <tr className="text-slate-400 text-left">
                  <th className="p-3 font-medium">#</th>
                  <th className="p-3 font-medium">Data/Hora</th>
                  <th className="p-3 font-medium hidden sm:table-cell">Pagamento</th>
                  <th className="p-3 font-medium">Total</th>
                  <th className="p-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {vendas.map((v) => (
                  <tr key={v.id} className="border-t border-slate-800 hover:bg-slate-800/50">
                    <td className="p-3 text-white font-medium">{v.id}</td>
                    <td className="p-3 text-slate-300">
                      {new Date(v.criado_em).toLocaleDateString("pt-BR")}
                      <span className="text-slate-500 text-xs block">
                        {new Date(v.criado_em).toLocaleTimeString("pt-BR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </td>
                    <td className="p-3 hidden sm:table-cell">
                      <span className="text-slate-300 text-xs bg-slate-800 px-2 py-0.5 rounded capitalize">
                        {v.forma_pagamento}
                      </span>
                    </td>
                    <td className="p-3 text-brand-400 font-bold">R$ {v.total.toFixed(2)}</td>
                    <td className="p-3">
                      <button
                        onClick={() => verDetalhe(v.id)}
                        className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-slate-700"
                      >
                        Detalhes
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Detalhe da venda */}
      {detalhe && (
        <div className="w-full lg:w-96 bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold">Venda #{detalhe.id}</h3>
            <button onClick={() => setDetalhe(null)} className="text-slate-400 hover:text-white text-lg">
              ×
            </button>
          </div>

          <div className="space-y-2 text-sm mb-4">
            <div className="flex justify-between">
              <span className="text-slate-400">Data</span>
              <span className="text-white">
                {new Date(detalhe.criado_em).toLocaleString("pt-BR")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Pagamento</span>
              <span className="text-white capitalize">{detalhe.forma_pagamento}</span>
            </div>
            {detalhe.observacao && (
              <div className="flex justify-between">
                <span className="text-slate-400">Obs</span>
                <span className="text-white">{detalhe.observacao}</span>
              </div>
            )}
          </div>

          <h4 className="text-slate-400 text-xs font-medium mb-2 uppercase">Itens</h4>
          <div className="space-y-1 mb-4">
            {(detalhe.itens || []).map((item, idx) => (
              <div key={idx} className="flex justify-between bg-slate-800 rounded p-2 text-sm">
                <div>
                  <span className="text-white">{item.nome_produto}</span>
                  <span className="text-slate-500 ml-2">×{item.quantidade}</span>
                </div>
                <span className="text-brand-400">R$ {item.subtotal.toFixed(2)}</span>
              </div>
            ))}
          </div>

          <div className="border-t border-slate-700 pt-3 space-y-1 text-sm">
            {detalhe.desconto > 0 && (
              <div className="flex justify-between text-green-400">
                <span>Desconto</span>
                <span>− R$ {detalhe.desconto.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold text-lg">
              <span className="text-white">Total</span>
              <span className="text-brand-400">R$ {detalhe.total.toFixed(2)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
