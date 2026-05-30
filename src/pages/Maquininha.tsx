import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { CreditCard, Save, CheckCircle2, AlertCircle, RefreshCw, Search } from "lucide-react";
import {
  getConfigMaquininha,
  salvarConfigMaquininha,
  listarDispositivosMaquininha,
} from "../lib/api";
import type { ConfigMaquininha, DispositivoPoint } from "../lib/api";

export default function MaquininhaPage() {
  const [cfg, setCfg] = useState<ConfigMaquininha>({ provedor: "mercadopago", imprimir_comprovante: 1 });
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const [dispositivos, setDispositivos] = useState<DispositivoPoint[]>([]);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const { config } = await getConfigMaquininha();
      setCfg({ provedor: "mercadopago", imprimir_comprovante: 1, ...config });
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao carregar configuração." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void carregar(); }, [carregar]);

  const set = (campo: keyof ConfigMaquininha, valor: string | number | boolean) =>
    setCfg((c) => ({ ...c, [campo]: valor }));

  // Monta o payload sem reenviar o token vazio (mantém o já salvo).
  function payloadAtual(): ConfigMaquininha {
    const p: ConfigMaquininha = { ...cfg };
    if (!p.access_token) delete p.access_token;
    return p;
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSalvando(true);
    setMsg(null);
    try {
      const { config } = await salvarConfigMaquininha(payloadAtual());
      setCfg({ provedor: "mercadopago", imprimir_comprovante: 1, ...config });
      setMsg({ tipo: "ok", texto: "Configuração da maquininha salva!" });
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setSalvando(false);
    }
  }

  // Salva o token primeiro (a listagem usa o token guardado no servidor) e
  // então busca as maquininhas pareadas à conta.
  async function buscarDispositivos() {
    setBuscando(true);
    setMsg(null);
    try {
      await salvarConfigMaquininha(payloadAtual());
      const { dispositivos } = await listarDispositivosMaquininha();
      setDispositivos(dispositivos);
      if (dispositivos.length === 0) {
        setMsg({ tipo: "erro", texto: "Nenhuma maquininha encontrada nesta conta. Confira o Access Token e se a Point está ativada." });
      } else {
        setMsg({ tipo: "ok", texto: `${dispositivos.length} maquininha(s) encontrada(s). Selecione a sua abaixo.` });
        if (!cfg.device_id) set("device_id", dispositivos[0].id);
      }
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setBuscando(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const inputCls = "w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500";
  const lbl = "text-slate-400 text-xs block mb-0.5";

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><CreditCard size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">Maquininha (Mercado Pago Point)</h1>
          <p className="text-slate-500 text-xs">Cobrança no cartão pela máquina física, direto do PDV.</p>
        </div>
      </div>

      {msg && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${msg.tipo === "ok" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
          {msg.tipo === "ok" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />} {msg.texto}
        </div>
      )}

      <form onSubmit={salvar} className="space-y-5">
        <label className="flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer">
          <input type="checkbox" checked={!!cfg.habilitado} onChange={(e) => set("habilitado", e.target.checked)} className="w-5 h-5 accent-brand-500" />
          <div>
            <p className="text-white font-bold text-sm">Cobrança por maquininha habilitada</p>
            <p className="text-slate-500 text-xs">Quando ligado, a venda no cartão dispara a cobrança na Point.</p>
          </div>
        </label>

        <fieldset className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <legend className="text-slate-300 text-xs font-bold uppercase px-2">Conta Mercado Pago</legend>
          <div>
            <label className={lbl}>
              Access Token {cfg.access_token_preenchido && <span className="text-emerald-400">(já configurado — preencha só para alterar)</span>}
            </label>
            <input
              className={inputCls}
              type="password"
              value={cfg.access_token || ""}
              onChange={(e) => set("access_token", e.target.value)}
              placeholder={cfg.access_token_preenchido ? "••••••••" : "APP_USR-..."}
            />
            <p className="text-slate-500 text-[11px] mt-1 leading-snug">
              Pegue em <b>mercadopago.com.br/developers</b> → Suas integrações → aplicação → Credenciais de produção.
            </p>
          </div>
        </fieldset>

        <fieldset className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <legend className="text-slate-300 text-xs font-bold uppercase px-2">Maquininha</legend>

          <button
            type="button"
            onClick={() => void buscarDispositivos()}
            disabled={buscando}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-60 text-white text-sm font-bold rounded-lg flex items-center gap-2 border border-slate-700"
          >
            {buscando ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
            {buscando ? "Buscando..." : "Buscar maquininhas da conta"}
          </button>

          {dispositivos.length > 0 && (
            <div>
              <label className={lbl}>Maquininhas encontradas</label>
              <select
                className={inputCls}
                value={cfg.device_id || ""}
                onChange={(e) => set("device_id", e.target.value)}
              >
                {dispositivos.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.id}{d.operating_mode ? ` — ${d.operating_mode}` : ""}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className={lbl}>Device ID (id da Point)</label>
              <input className={inputCls} value={cfg.device_id || ""} onChange={(e) => set("device_id", e.target.value)} placeholder="PAX_A910__SMARTPOS..." />
            </div>
            <div>
              <label className={lbl}>POS ID (opcional)</label>
              <input className={inputCls} value={cfg.pos_id || ""} onChange={(e) => set("pos_id", e.target.value)} />
            </div>
            <div>
              <label className={lbl}>Store ID (opcional)</label>
              <input className={inputCls} value={cfg.store_id || ""} onChange={(e) => set("store_id", e.target.value)} />
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer pt-1">
            <input type="checkbox" checked={!!cfg.imprimir_comprovante} onChange={(e) => set("imprimir_comprovante", e.target.checked)} className="w-5 h-5 accent-brand-500" />
            <span className="text-slate-300 text-sm">Imprimir comprovante na maquininha</span>
          </label>

          <p className="text-slate-500 text-[11px] leading-snug">
            A maquininha precisa estar ativada na conta e em <b>modo PDV/Integração</b> (configurado uma vez no menu do próprio aparelho). A cobrança no cartão exige internet.
          </p>
        </fieldset>

        <button disabled={salvando} className="w-full md:w-auto px-6 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-bold rounded-lg flex items-center justify-center gap-2">
          <Save size={18} /> {salvando ? "Salvando..." : "Salvar configuração"}
        </button>
      </form>
    </motion.div>
  );
}
