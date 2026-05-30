import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { 
  Package,
  AlertTriangle,
  CheckCircle2, 
  History, 
  ArrowUpRight,
  ShoppingBag,
  DollarSign
} from "lucide-react";
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

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <div className="w-12 h-12 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
        <p className="text-slate-500 font-bold uppercase tracking-widest text-xs animate-pulse">Carregando painel...</p>
      </div>
    );
  }

  if (!dash) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <AlertTriangle className="text-red-500" size={48} />
        <p className="text-slate-400 font-bold">Não foi possível carregar os dados.</p>
        <button onClick={() => carregar()} className="px-4 py-2 bg-slate-800 rounded-lg text-white text-sm">Tentar novamente</button>
      </div>
    );
  }

  const metricas = [
    {
      titulo: "Produtos Ativos",
      valor: String(dash.total_produtos),
      cor: "from-blue-600 to-indigo-600",
      icon: <Package size={20} />,
      id: "produtos"
    },
    {
      titulo: "Vendas Hoje",
      valor: String(dash.vendas_hoje_qtd),
      subtitulo: `R$ ${(dash.vendas_hoje_total || 0).toFixed(2)}`,
      cor: "from-emerald-600 to-teal-600",
      icon: <ShoppingBag size={20} />,
      id: "vendas-hoje"
    },
    {
      titulo: "Total em Vendas",
      valor: `R$ ${(dash.vendas_total || 0).toFixed(2)}`,
      cor: "from-violet-600 to-purple-600",
      icon: <DollarSign size={20} />,
      id: "vendas-total"
    },
    {
      titulo: "Alertas Estoque",
      valor: String(dash.alertas_estoque),
      cor: dash.alertas_estoque > 0 ? "from-rose-600 to-red-600" : "from-amber-600 to-orange-600",
      icon: dash.alertas_estoque > 0 ? <AlertTriangle size={20} /> : <CheckCircle2 size={20} />,
      destaque: dash.alertas_estoque > 0,
      id: "alertas"
    },
  ];

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <div className="space-y-8 pb-10">
      <header>
        <h1 className="text-3xl font-black text-white tracking-tight">DASHBOARD</h1>
        <p className="text-slate-500 font-bold text-xs uppercase tracking-[0.3em] mt-1">Visão geral do seu negócio</p>
      </header>

      {/* Métricas */}
      <motion.div 
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6"
      >
        {metricas.map((m) => (
          <motion.div
            key={m.id}
            variants={item}
            whileHover={{ y: -5 }}
            className={`relative overflow-hidden bg-slate-900/50 backdrop-blur-xl border rounded-3xl p-6 transition-all shadow-2xl ${
              m.destaque ? "border-red-500/50 shadow-red-900/10" : "border-slate-800/50"
            }`}
          >
            {/* Background Glow */}
            <div className={`absolute -right-10 -top-10 w-24 h-24 bg-gradient-to-br ${m.cor} opacity-10 blur-2xl rounded-full`} />
            
            <div className="flex items-center justify-between mb-4">
              <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${m.cor} flex items-center justify-center text-white shadow-lg shadow-black/20`}>
                {m.icon}
              </div>
              <ArrowUpRight className="text-slate-700" size={18} />
            </div>
            
            <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest block mb-1">{m.titulo}</span>
            <p className="text-white text-3xl font-black tracking-tighter">{m.valor}</p>
            {m.subtitulo && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-emerald-400 text-xs font-bold">{m.subtitulo}</span>
                <span className="text-slate-600 text-[10px] font-bold uppercase">Volume hoje</span>
              </div>
            )}
          </motion.div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Últimas Vendas */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-3xl p-6 shadow-2xl flex flex-col"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-violet-600/10 flex items-center justify-center text-violet-400">
              <History size={20} />
            </div>
            <h3 className="text-white font-black tracking-tight">ÚLTIMAS VENDAS</h3>
          </div>

          {dash.ultimas_vendas.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center py-10 text-center">
              <div className="w-16 h-16 rounded-full bg-slate-800/50 flex items-center justify-center text-slate-600 mb-4">
                <ShoppingBag size={32} />
              </div>
              <p className="text-slate-500 text-sm font-bold">Nenhuma venda hoje.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {dash.ultimas_vendas.map((v) => (
                <div
                  key={v.id}
                  className="flex items-center justify-between bg-slate-800/30 hover:bg-slate-800/60 border border-slate-700/30 rounded-2xl p-4 transition-colors group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-700/50 flex items-center justify-center text-xs font-black text-brand-400">
                      #{v.id}
                    </div>
                    <div>
                      <p className="text-white text-sm font-bold">Venda Confirmada</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{v.forma_pagamento}</span>
                        <span className="w-1 h-1 rounded-full bg-slate-700" />
                        <span className="text-[10px] font-bold text-slate-500">
                          {new Date(v.criado_em).toLocaleTimeString("pt-BR", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-emerald-400 font-black tracking-tight">R$ {v.total.toFixed(2)}</p>
                    <ArrowUpRight className="text-slate-700 group-hover:text-brand-500 ml-auto transition-colors" size={14} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Estoque Baixo */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-3xl p-6 shadow-2xl flex flex-col"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-rose-600/10 flex items-center justify-center text-rose-400">
              <AlertTriangle size={20} />
            </div>
            <h3 className="text-white font-black tracking-tight uppercase">Estoque em Alerta</h3>
          </div>

          {dash.produtos_baixo_estoque.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center py-10 text-center text-emerald-400">
              <CheckCircle2 size={48} className="mb-4 opacity-20" />
              <p className="text-sm font-black uppercase tracking-widest">Tudo em ordem!</p>
              <p className="text-slate-500 text-xs mt-1">Seu estoque está abastecido.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {dash.produtos_baixo_estoque.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/20 rounded-2xl p-4 transition-colors"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="text-white text-sm font-bold truncate">{p.nome}</p>
                    <p className="text-rose-400/80 text-[10px] font-black uppercase tracking-widest mt-0.5">
                      Atual: {p.estoque} <span className="text-slate-600 mx-1">|</span> Mínimo: {p.estoque_minimo}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="bg-rose-500 text-white text-[10px] font-black px-3 py-1.5 rounded-full shadow-lg shadow-rose-900/20 uppercase tracking-widest">
                      repor {(p.estoque_minimo - p.estoque)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

