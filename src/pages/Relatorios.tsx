import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { BarChart3, TrendingUp, Receipt, DollarSign, Trophy, ShieldCheck, FileText, Download } from "lucide-react";
import { relatorioVendas, relatorioFiscal, exportarXmlsZip } from "../lib/api";
import type { RelatorioVendas, RelatorioFiscal } from "../lib/api";

const moeda = (v: number) => `R$ ${(v || 0).toFixed(2)}`;
const LABEL: Record<string, string> = { dinheiro: "Dinheiro", pix: "PIX", debito: "Débito", credito: "Crédito", fiado: "Fiado" };

function hoje() { return new Date().toISOString().slice(0, 10); }
function inicioMes() { return hoje().slice(0, 8) + "01"; }

export default function RelatoriosPage() {
  const [aba, setAba] = useState<"vendas" | "fiscal">("vendas");
  const [inicio, setInicio] = useState(inicioMes());
  const [fim, setFim] = useState(hoje());
  const [dados, setDados] = useState<RelatorioVendas | null>(null);
  const [fiscal, setFiscal] = useState<RelatorioFiscal | null>(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");
  const [exportando, setExportando] = useState(false);

  async function exportarXmls() {
    setExportando(true);
    setErro("");
    try {
      await exportarXmlsZip(inicio, fim);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setExportando(false);
    }
  }

  const carregar = useCallback(async () => {
    setLoading(true); setErro("");
    try {
      if (aba === "vendas") setDados(await relatorioVendas(inicio, fim));
      else setFiscal(await relatorioFiscal(inicio, fim));
    }
    catch (e) { setErro((e as Error).message); }
    finally { setLoading(false); }
  }, [inicio, fim, aba]);
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
          <h1 className="text-xl font-black text-white">Relatórios</h1>
          <p className="text-slate-500 text-xs">Vendas e apuração fiscal do Simples Nacional.</p>
        </div>
      </div>

      <div className="flex gap-1 mb-5 bg-slate-900 border border-slate-800 rounded-xl p-1 w-fit">
        <button onClick={() => setAba("vendas")}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${aba === "vendas" ? "bg-brand-600 text-white" : "text-slate-400 hover:text-white"}`}>
          <BarChart3 size={14} /> Vendas
        </button>
        <button onClick={() => setAba("fiscal")}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors ${aba === "fiscal" ? "bg-brand-600 text-white" : "text-slate-400 hover:text-white"}`}>
          <ShieldCheck size={14} /> Fiscal (Simples)
        </button>
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
      {loading ? (
        <div className="flex items-center justify-center h-40"><div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : aba === "vendas" && dados ? (
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
      ) : aba === "fiscal" && fiscal ? (
        <>
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 mb-3 flex gap-3">
            <FileText size={18} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-amber-200/80 text-xs leading-relaxed">
              Entregue estes números ao seu contador para o <strong>PGDAS-D</strong>. A receita de produtos
              com <strong>ICMS já recolhido por Substituição Tributária</strong> (CSOSN 500) e com
              <strong> PIS/COFINS monofásico/ST/alíquota zero</strong> (CST 04/05/06) deve ser informada como receita
              <em> com substituição tributária / tributação concentrada</em> — assim você não paga esses
              impostos de novo no DAS.
            </p>
          </div>

          <button
            onClick={() => void exportarXmls()}
            disabled={exportando}
            className="mb-3 w-full md:w-auto px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-bold rounded-lg flex items-center justify-center gap-2"
          >
            <Download size={16} /> {exportando ? "Gerando ZIP..." : "Exportar XMLs do período (ZIP) p/ o contador"}
          </button>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
            {card(<DollarSign size={14} />, "Faturamento total", moeda(fiscal.total_geral), "text-emerald-400")}
            {card(<ShieldCheck size={14} />, "Receita segregada", moeda(fiscal.receita_segregada), "text-amber-400")}
            {card(<Receipt size={14} />, "Tributada integral", moeda(fiscal.receita_tributada_integral))}
          </div>

          <div className="grid md:grid-cols-2 gap-3 mb-3">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <h3 className="text-slate-300 font-bold text-sm mb-3">ICMS</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-400">Já recolhido por ST (CSOSN 500)</span><span className="text-amber-400 font-semibold">{moeda(fiscal.icms.substituicao_tributaria)}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Tributado normal no DAS</span><span className="text-white font-semibold">{moeda(fiscal.icms.tributado_normal)}</span></div>
              </div>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
              <h3 className="text-slate-300 font-bold text-sm mb-3">PIS / COFINS</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-400">Monofásico / ST / alíquota zero (CST 04-06)</span><span className="text-amber-400 font-semibold">{moeda(fiscal.pis_cofins.monofasico_st)}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Tributado normal no DAS</span><span className="text-white font-semibold">{moeda(fiscal.pis_cofins.tributado_normal)}</span></div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <h3 className="text-slate-300 font-bold text-sm mb-3">Detalhe por produto</h3>
            {fiscal.itens.length === 0 ? <p className="text-slate-500 text-sm">Sem vendas no período.</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-500 text-xs uppercase text-left">
                      <th className="py-1 pr-2 font-medium">Produto</th>
                      <th className="py-1 px-2 font-medium">NCM</th>
                      <th className="py-1 px-2 font-medium">CSOSN</th>
                      <th className="py-1 px-2 font-medium">CST PIS/COF</th>
                      <th className="py-1 pl-2 font-medium text-right">Receita</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fiscal.itens.map((it) => (
                      <tr key={it.produto_id} className="border-t border-slate-800/70">
                        <td className="py-1.5 pr-2 text-slate-300 max-w-[14rem] truncate">
                          {it.nome_produto}
                          {(it.icms_substituicao || it.pis_cofins_concentrado) && (
                            <span className="ml-2 text-[10px] bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded">segregar</span>
                          )}
                        </td>
                        <td className="py-1.5 px-2 text-slate-500">{it.ncm || "—"}</td>
                        <td className="py-1.5 px-2 text-slate-400">{it.csosn}</td>
                        <td className="py-1.5 px-2 text-slate-400">{it.cst_pis}/{it.cst_cofins}</td>
                        <td className="py-1.5 pl-2 text-right text-white font-semibold">{moeda(it.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <p className="text-slate-600 text-xs mt-4">* A classificação usa o cadastro fiscal atual de cada produto (CSOSN, CST de PIS/COFINS). Mantenha o cadastro correto para a segregação ficar certa.</p>
        </>
      ) : null}
    </motion.div>
  );
}
