import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Wallet, ArrowDownCircle, ArrowUpCircle, Lock, Unlock, CheckCircle2, AlertCircle } from "lucide-react";
import { caixaAtual, abrirCaixa, movimentoCaixa, fecharCaixa } from "../lib/api";
import type { CaixaAtual } from "../lib/api";

const moeda = (v: number) => `R$ ${(v || 0).toFixed(2)}`;
const LABEL: Record<string, string> = { dinheiro: "Dinheiro", pix: "PIX", debito: "Débito", credito: "Crédito", fiado: "Fiado" };

export default function CaixaPage() {
  const [estado, setEstado] = useState<CaixaAtual | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [abertura, setAbertura] = useState("0");
  const [contado, setContado] = useState("");
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try { setEstado(await caixaAtual()); }
    catch (e) { setMsg({ tipo: "erro", texto: (e as Error).message }); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void carregar(); }, [carregar]);

  async function abrir() {
    setBusy(true); setMsg(null);
    try { setEstado(await abrirCaixa(Number(abertura) || 0)); }
    catch (e) { setMsg({ tipo: "erro", texto: (e as Error).message }); }
    finally { setBusy(false); }
  }

  async function movimento(tipo: "sangria" | "suprimento") {
    const v = prompt(`${tipo === "sangria" ? "Sangria (retirada)" : "Suprimento (reforço)"} — valor em R$:`, "");
    if (v === null) return;
    const valor = Number(v);
    if (!valor || valor <= 0) { setMsg({ tipo: "erro", texto: "Valor inválido." }); return; }
    const motivo = prompt("Motivo (opcional):", "") || "";
    setBusy(true); setMsg(null);
    try { await movimentoCaixa(tipo, valor, motivo); await carregar(); }
    catch (e) { setMsg({ tipo: "erro", texto: (e as Error).message }); }
    finally { setBusy(false); }
  }

  async function fechar() {
    if (contado === "") { setMsg({ tipo: "erro", texto: "Informe o valor contado na gaveta." }); return; }
    if (!confirm("Fechar o caixa agora?")) return;
    setBusy(true); setMsg(null);
    try {
      const r = await fecharCaixa(Number(contado), "");
      const dif = r.sessao.diferenca ?? 0;
      setMsg({ tipo: "ok", texto: `Caixa fechado. Diferença: ${moeda(dif)} ${dif === 0 ? "(bateu certinho!)" : dif > 0 ? "(sobra)" : "(falta)"}` });
      setContado("");
      await carregar();
    } catch (e) { setMsg({ tipo: "erro", texto: (e as Error).message }); }
    finally { setBusy(false); }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;

  const inputCls = "w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500";
  const card = (titulo: string, valor: string, cor?: string) => (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{titulo}</div>
      <div className={`text-2xl font-black ${cor || "text-white"}`}>{valor}</div>
    </div>
  );

  const aberto = estado?.aberto;
  const r = estado?.resumo;

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><Wallet size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">Caixa</h1>
          <p className="text-slate-500 text-xs">Abertura, sangria/suprimento e fechamento do dia.</p>
        </div>
      </div>

      {msg && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${msg.tipo === "ok" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
          {msg.tipo === "ok" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />} {msg.texto}
        </div>
      )}

      {!aberto ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h2 className="text-white font-bold mb-1 flex items-center gap-2"><Unlock size={18} /> Abrir caixa</h2>
          <p className="text-slate-500 text-xs mb-4">Informe o fundo de troco inicial (dinheiro na gaveta ao abrir).</p>
          <div className="flex items-end gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Valor de abertura (R$)</label>
              <input type="number" step="0.01" value={abertura} onChange={(e) => setAbertura(e.target.value)} className={`${inputCls} w-40`} />
            </div>
            <button onClick={abrir} disabled={busy} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white rounded-lg font-bold">Abrir caixa</button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {card("Abertura", moeda(r!.valor_abertura))}
            {card("Vendas", moeda(r!.vendas_total), "text-emerald-400")}
            {card("Suprimentos", moeda(r!.suprimentos))}
            {card("Sangrias", moeda(r!.sangrias), "text-amber-400")}
          </div>
          <div className="mb-4">{card("💵 Dinheiro esperado na gaveta", moeda(r!.dinheiro_esperado), "text-brand-400")}</div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 mb-4">
            <h3 className="text-slate-300 font-bold text-sm mb-2">Vendas por forma de pagamento</h3>
            {r!.vendas_qtd === 0 ? <p className="text-slate-500 text-sm">Nenhuma venda ainda nesta sessão.</p> : (
              <div className="grid sm:grid-cols-2 gap-2 text-sm">
                {Object.entries(r!.por_forma).map(([k, v]) => (
                  <div key={k} className="flex justify-between bg-slate-950/50 rounded-lg px-3 py-2">
                    <span className="text-slate-400">{LABEL[k] || k} <span className="text-slate-600">({v.qtd})</span></span>
                    <span className="text-white font-semibold">{moeda(v.total)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-2 mb-6">
            <button onClick={() => movimento("suprimento")} disabled={busy} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-bold"><ArrowUpCircle size={16} className="text-emerald-400" /> Suprimento</button>
            <button onClick={() => movimento("sangria")} disabled={busy} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-bold"><ArrowDownCircle size={16} className="text-amber-400" /> Sangria</button>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <h3 className="text-white font-bold mb-1 flex items-center gap-2"><Lock size={18} /> Fechar caixa</h3>
            <p className="text-slate-500 text-xs mb-4">Conte o dinheiro na gaveta e informe o valor. O sistema compara com o esperado ({moeda(r!.dinheiro_esperado)}).</p>
            <div className="flex items-end gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Valor contado (R$)</label>
                <input type="number" step="0.01" value={contado} onChange={(e) => setContado(e.target.value)} className={`${inputCls} w-40`} placeholder="0,00" />
              </div>
              <button onClick={fechar} disabled={busy} className="px-5 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-60 text-white rounded-lg font-bold">Fechar caixa</button>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}
