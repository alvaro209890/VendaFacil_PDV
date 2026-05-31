import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { BarChart3, TrendingUp, Receipt, DollarSign, Trophy } from "lucide-react";
import { relatorioVendas } from "../lib/api";
import type { RelatorioVendas } from "../lib/api";

const moeda = (v: number) => `R$ ${(v || 0).toFixed(2)}`;
const LABEL: Record<string, string> = { dinheiro: "Dinheiro", pix: "PIX", debito: "Débito", credito: "Crédito", fiado: "Fiado" };

function hoje() { return new Date().toISOString().slice(0, 10); }
function inicioMes() { return hoje().slice(0, 8) + "01"; }

export default function RelatoriosPage() {
  const [inicio, setInicio] = useState(inicioMes());
  const [fim, setFim] = useState(hoje());
  const [dados, setDados] = useState<RelatorioVendas | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setLoading(true); setErro("");
    try { setDados(await relatorioVendas(inicio, fim)); }
    catch (e) { setErro((e as Error).message); }
    finally { setLoading(false); }
  }, [inicio, fim]);
  useEffect(() => { void carregar(); }, [carregar]);

  const atalho = (dias: number) => {
    const f = new Date();
    const i = new Date(); i.setDate(i.getDate() - dias + 1);
    setInicio(i.toISOString().slice(0, 10)); setFim(f.toISOString().slice(0, 10));
  };

  const inputCls = "px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500";
  const card = (icon: React.ReactNode, titulo: string, valor: string, cor?: string) => (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
      <div className="flex items-center gap-2 text-slate-500 text-xs uppercase tracking-wide">{icon}{titulo}</div>
      <div className={`text-2xl font-black mt-1 ${cor || "text-white"}`}>{valor}</div>
    </div>
  );

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><BarChart3 size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">Relatórios de vendas</h1>
          <p className="text-slate-500 text-xs">Faturamento, formas de pagamento e produtos mais vendidos.</p>
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-2 mb-5">
        <div><label className="block text-xs text-slate-500 mb-1">De</label><input type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} className={inputCls} /></div>
        <div><label className="block text-xs text-slate-500 mb-1">Até</label><input type="date" value={fim} onChange={(e) => setFim(e.target.value)} className={inputCls} /></div>
        <div className="flex gap-1">
          <button onClick={() => atalho(1)} className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs text-slate-300">Hoje</button>
          <button onClick={() => atalho(7)} className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs text-slate-300">7 dias</button>
          <button onClick={() => atalho(30)} className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs text-slate-300">30 dias</button>
          <button onClick={() => { setInicio(inicioMes()); setFim(hoje()); }} className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs text-slate-300">Mês</button>
        </div>
      </div>

      {erro && <div className="mb-4 px-4 py-2 rounded-lg text-sm bg-red-500/10 text-red-400">{erro}</div>}
      {loading || !dados ? (
        <div className="flex items-center justify-center h-40"><div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            {card(<DollarSign size={14} />, "Faturamento", moeda(dados.faturamento), "text-emerald-400")}
            {card(<Receipt size={14} />, "Vendas", String(dados.qtd_vendas))}
            {card(<TrendingUp size={14} />, "Ticket médio", moeda(dados.ticket_medio))}
            {card(<TrendingUp size={14} />, "Lucro estimado", moeda(dados.lucro_estimado), dados.lucro_estimado >= 0 ? "text-emerald-400" : "text-red-400")}
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <h3 className="text-slate-300 font-bold text-sm mb-3">Por forma de pagamento</h3>
              {dados.por_forma.length === 0 ? <p className="text-slate-500 text-sm">Sem vendas no período.</p> : (
                <div className="space-y-2 text-sm">
                  {dados.por_forma.map((f) => (
                    <div key={f.forma_pagamento} className="flex justify-between">
                      <span className="text-slate-400">{LABEL[f.forma_pagamento] || f.forma_pagamento} <span className="text-slate-600">({f.qtd})</span></span>
                      <span className="text-white font-semibold">{moeda(f.total)}</span>
                    </div>
                  ))}
                </div>
              )}
              {dados.desconto_total > 0 && <p className="text-slate-500 text-xs mt-3">Descontos concedidos: {moeda(dados.desconto_total)}</p>}
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <h3 className="text-slate-300 font-bold text-sm mb-3 flex items-center gap-1"><Trophy size={14} className="text-amber-400" /> Produtos mais vendidos</h3>
              {dados.top_produtos.length === 0 ? <p className="text-slate-500 text-sm">Sem dados no período.</p> : (
                <div className="space-y-2 text-sm">
                  {dados.top_produtos.map((p, i) => (
                    <div key={p.produto_id} className="flex justify-between gap-2">
                      <span className="text-slate-400 truncate">{i + 1}. {p.nome_produto} <span className="text-slate-600">({p.qtd})</span></span>
                      <span className="text-white font-semibold shrink-0">{moeda(p.total)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {dados.por_dia.length > 1 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 mt-3">
              <h3 className="text-slate-300 font-bold text-sm mb-3">Vendas por dia</h3>
              <div className="space-y-1 text-sm max-h-60 overflow-y-auto">
                {dados.por_dia.map((d) => (
                  <div key={d.dia} className="flex justify-between">
                    <span className="text-slate-400">{d.dia.split("-").reverse().join("/")} <span className="text-slate-600">({d.qtd})</span></span>
                    <span className="text-white">{moeda(d.total)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-slate-600 text-xs mt-4">* Lucro estimado usa o custo atual de cada produto, descontados os descontos das vendas. É uma estimativa.</p>
        </>
      )}
    </motion.div>
  );
}
