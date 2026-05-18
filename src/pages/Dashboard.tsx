import { useState, useEffect, useCallback } from "react";
import { getDashboard } from "../lib/api";
import type { DashboardData } from "../lib/api";

export default function DashboardPage() {
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const carregar = useCallback(async () => {
    try {
      const d = await getDashboard();
      setDash(d);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!dash) {
    return <p className="text-slate-400 text-center py-12">Erro ao carregar dados.</p>;
  }

  const metricas = [
    {
      titulo: "Produtos Ativos",
      valor: String(dash.total_produtos),
      cor: "from-blue-600 to-blue-500",
      icone: "📦",
    },
    {
      titulo: "Vendas Hoje",
      valor: String(dash.vendas_hoje_qtd),
      subtitulo: `R$ ${(dash.vendas_hoje_total || 0).toFixed(2)}`,
      cor: "from-green-600 to-green-500",
      icone: "💰",
    },
    {
      titulo: "Total em Vendas",
      valor: `R$ ${(dash.vendas_total || 0).toFixed(2)}`,
      cor: "from-purple-600 to-purple-500",
      icone: "📊",
    },
    {
      titulo: "Alertas Estoque",
      valor: String(dash.alertas_estoque),
      cor: dash.alertas_estoque > 0 ? "from-red-600 to-red-500" : "from-amber-600 to-amber-500",
      icone: dash.alertas_estoque > 0 ? "⚠️" : "✅",
      destaque: dash.alertas_estoque > 0,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Métricas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {metricas.map((m) => (
          <div
            key={m.titulo}
            className={`bg-slate-900 border rounded-xl p-3 sm:p-4 ${
              m.destaque ? "border-red-500/30 animate-pulse" : "border-slate-800"
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gradient-to-br ${m.cor} flex items-center justify-center text-base sm:text-lg`}
              >
                {m.icone}
              </div>
              <span className="text-slate-400 text-xs sm:text-sm">{m.titulo}</span>
            </div>
            <p className="text-white text-xl sm:text-2xl font-bold">{m.valor}</p>
            {m.subtitulo && <p className="text-slate-400 text-xs mt-0.5">{m.subtitulo}</p>}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Últimas Vendas */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <h3 className="text-white font-bold mb-3">🕐 Últimas Vendas</h3>
          {dash.ultimas_vendas.length === 0 ? (
            <p className="text-slate-500 text-sm py-4 text-center">Nenhuma venda realizada ainda.</p>
          ) : (
            <div className="space-y-2">
              {dash.ultimas_vendas.map((v) => (
                <div
                  key={v.id}
                  className="flex items-center justify-between bg-slate-800 rounded-lg p-3"
                >
                  <div>
                    <p className="text-white text-sm font-medium">Venda #{v.id}</p>
                    <p className="text-slate-400 text-xs">
                      {v.forma_pagamento === "pix"
                        ? "📱 PIX"
                        : v.forma_pagamento === "dinheiro"
                          ? "💵 Dinheiro"
                          : v.forma_pagamento === "debito"
                            ? "💳 Débito"
                            : "💳 Crédito"}
                      {" · "}
                      {new Date(v.criado_em).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                  <p className="text-brand-400 font-bold">R$ {v.total.toFixed(2)}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Estoque Baixo */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <h3 className="text-white font-bold mb-3">⚠️ Estoque Baixo</h3>
          {dash.produtos_baixo_estoque.length === 0 ? (
            <p className="text-green-400 text-sm py-4 text-center">
              ✅ Todos os produtos com estoque ok!
            </p>
          ) : (
            <div className="space-y-2">
              {dash.produtos_baixo_estoque.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between bg-slate-800 rounded-lg p-3 border border-amber-500/20"
                >
                  <div>
                    <p className="text-white text-sm font-medium">{p.nome}</p>
                    <p className="text-amber-400 text-xs">
                      Mínimo: {p.estoque_minimo} · Atual: {p.estoque}
                    </p>
                  </div>
                  <span className="text-red-400 text-xs bg-red-500/10 px-2 py-1 rounded font-medium">
                    {(p.estoque_minimo - p.estoque)} faltam
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
