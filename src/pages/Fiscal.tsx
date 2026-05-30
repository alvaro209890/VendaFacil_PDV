import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { FileText, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { getConfigFiscal, salvarConfigFiscal } from "../lib/api";
import type { ConfigFiscal } from "../lib/api";

export default function FiscalPage() {
  const [cfg, setCfg] = useState<ConfigFiscal>({ ambiente: "homologacao", gateway: "focusnfe" });
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const { config } = await getConfigFiscal();
      setCfg({ ambiente: "homologacao", gateway: "focusnfe", ...config });
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao carregar configuração." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void carregar(); }, [carregar]);

  const set = (campo: keyof ConfigFiscal, valor: string | number | boolean) =>
    setCfg((c) => ({ ...c, [campo]: valor }));

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSalvando(true);
    setMsg(null);
    try {
      // Não reenvia segredos vazios (mantém o que já está salvo).
      const payload: ConfigFiscal = { ...cfg };
      if (!payload.gateway_token) delete payload.gateway_token;
      if (!payload.csc) delete payload.csc;
      const { config } = await salvarConfigFiscal(payload);
      setCfg({ ambiente: "homologacao", gateway: "focusnfe", ...config });
      setMsg({ tipo: "ok", texto: "Configuração fiscal salva!" });
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setSalvando(false);
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
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><FileText size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">Configurações Fiscais (NFC-e)</h1>
          <p className="text-slate-500 text-xs">Dados da loja e do gateway de emissão de nota.</p>
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
            <p className="text-white font-bold text-sm">Emissão fiscal habilitada</p>
            <p className="text-slate-500 text-xs">Quando ligado, a venda pode gerar NFC-e pelo gateway.</p>
          </div>
        </label>

        <fieldset className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <legend className="text-slate-300 text-xs font-bold uppercase px-2">Emitente</legend>
          <div className="grid md:grid-cols-2 gap-3">
            <div><label className={lbl}>Razão social</label><input className={inputCls} value={cfg.razao_social || ""} onChange={(e) => set("razao_social", e.target.value)} /></div>
            <div><label className={lbl}>Nome fantasia</label><input className={inputCls} value={cfg.nome_fantasia || ""} onChange={(e) => set("nome_fantasia", e.target.value)} /></div>
            <div><label className={lbl}>CNPJ</label><input className={inputCls} value={cfg.cnpj || ""} onChange={(e) => set("cnpj", e.target.value)} placeholder="00.000.000/0001-00" /></div>
            <div><label className={lbl}>Inscrição Estadual</label><input className={inputCls} value={cfg.inscricao_estadual || ""} onChange={(e) => set("inscricao_estadual", e.target.value)} /></div>
            <div>
              <label className={lbl}>Regime tributário</label>
              <select className={inputCls} value={cfg.regime_tributario || "1"} onChange={(e) => set("regime_tributario", e.target.value)}>
                <option value="1">Simples Nacional</option>
                <option value="2">Simples — excesso de sublimite</option>
                <option value="3">Regime Normal</option>
              </select>
            </div>
          </div>
        </fieldset>

        <fieldset className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <legend className="text-slate-300 text-xs font-bold uppercase px-2">Endereço</legend>
          <div className="grid md:grid-cols-3 gap-3">
            <div className="md:col-span-2"><label className={lbl}>Logradouro</label><input className={inputCls} value={cfg.logradouro || ""} onChange={(e) => set("logradouro", e.target.value)} /></div>
            <div><label className={lbl}>Número</label><input className={inputCls} value={cfg.numero || ""} onChange={(e) => set("numero", e.target.value)} /></div>
            <div><label className={lbl}>Bairro</label><input className={inputCls} value={cfg.bairro || ""} onChange={(e) => set("bairro", e.target.value)} /></div>
            <div><label className={lbl}>Município</label><input className={inputCls} value={cfg.municipio || ""} onChange={(e) => set("municipio", e.target.value)} /></div>
            <div><label className={lbl}>Cód. IBGE município</label><input className={inputCls} value={cfg.codigo_municipio || ""} onChange={(e) => set("codigo_municipio", e.target.value)} placeholder="7 dígitos" /></div>
            <div><label className={lbl}>UF</label><input className={inputCls} value={cfg.uf || ""} onChange={(e) => set("uf", e.target.value)} maxLength={2} /></div>
            <div><label className={lbl}>CEP</label><input className={inputCls} value={cfg.cep || ""} onChange={(e) => set("cep", e.target.value)} /></div>
          </div>
        </fieldset>

        <fieldset className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <legend className="text-slate-300 text-xs font-bold uppercase px-2">Gateway & Ambiente</legend>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className={lbl}>Gateway</label>
              <select className={inputCls} value={cfg.gateway || "focusnfe"} onChange={(e) => set("gateway", e.target.value)}>
                <option value="focusnfe">Focus NFe</option>
                <option value="plugnotas">PlugNotas (em breve)</option>
              </select>
            </div>
            <div>
              <label className={lbl}>Ambiente</label>
              <select className={inputCls} value={cfg.ambiente || "homologacao"} onChange={(e) => set("ambiente", e.target.value)}>
                <option value="homologacao">Homologação (teste)</option>
                <option value="producao">Produção (vale fiscalmente)</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className={lbl}>Token do gateway {cfg.gateway_token_preenchido && <span className="text-emerald-400">(já configurado — preencha só para alterar)</span>}</label>
              <input className={inputCls} type="password" value={cfg.gateway_token || ""} onChange={(e) => set("gateway_token", e.target.value)} placeholder={cfg.gateway_token_preenchido ? "••••••••" : "token da API"} />
            </div>
            <div><label className={lbl}>CSC (idCSC) {cfg.csc_preenchido && <span className="text-emerald-400">(salvo)</span>}</label><input className={inputCls} type="password" value={cfg.csc || ""} onChange={(e) => set("csc", e.target.value)} /></div>
            <div><label className={lbl}>ID do CSC (Token)</label><input className={inputCls} value={cfg.csc_id || ""} onChange={(e) => set("csc_id", e.target.value)} placeholder="ex.: 000001" /></div>
            <div><label className={lbl}>Série NFC-e</label><input type="number" className={inputCls} value={cfg.serie ?? 1} onChange={(e) => set("serie", Number(e.target.value))} /></div>
            <div><label className={lbl}>Próximo número</label><input type="number" className={inputCls} value={cfg.proximo_numero ?? 1} onChange={(e) => set("proximo_numero", Number(e.target.value))} /></div>
          </div>
          <p className="text-slate-500 text-[11px] leading-snug">
            O certificado digital A1 e o CSC são cadastrados no painel do gateway (Focus NFe). Aqui o sistema só guarda o token de API. Comece em <b>Homologação</b> para testar; só mude para <b>Produção</b> quando as notas de teste autorizarem.
          </p>
        </fieldset>

        <button disabled={salvando} className="w-full md:w-auto px-6 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-bold rounded-lg flex items-center justify-center gap-2">
          <Save size={18} /> {salvando ? "Salvando..." : "Salvar configuração"}
        </button>
      </form>
    </motion.div>
  );
}
