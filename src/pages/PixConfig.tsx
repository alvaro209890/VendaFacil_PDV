import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Smartphone, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { getConfigPix, salvarConfigPix } from "../lib/api";
import type { ConfigPix } from "../lib/api";

export default function PixConfigPage() {
  const [cfg, setCfg] = useState<ConfigPix>({ pix_chave: "", pix_nome: "", pix_cidade: "" });
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const { config } = await getConfigPix();
      setCfg(config);
    } catch {
      setMsg({ tipo: "erro", texto: "Erro ao carregar configuração." });
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void carregar(); }, [carregar]);

  const set = (campo: keyof ConfigPix, valor: string) => setCfg((c) => ({ ...c, [campo]: valor }));

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSalvando(true); setMsg(null);
    try {
      const { config } = await salvarConfigPix(cfg);
      setCfg(config);
      setMsg({ tipo: "ok", texto: "Configuração do PIX salva! O QR já usa esses dados." });
    } catch (err) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setSalvando(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" /></div>;

  const inputCls = "w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-brand-500";
  const lbl = "text-slate-400 text-xs block mb-0.5";

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><Smartphone size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">PIX da loja</h1>
          <p className="text-slate-500 text-xs">Chave para gerar o QR Code de cobrança no PDV.</p>
        </div>
      </div>

      {msg && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${msg.tipo === "ok" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
          {msg.tipo === "ok" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />} {msg.texto}
        </div>
      )}

      <form onSubmit={salvar} className="space-y-4 bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <div>
          <label className={lbl}>Chave PIX</label>
          <input className={inputCls} value={cfg.pix_chave} onChange={(e) => set("pix_chave", e.target.value)} placeholder="CPF/CNPJ, e-mail, telefone ou chave aleatória" />
          <p className="text-slate-500 text-[11px] mt-1">É a chave onde a loja recebe o dinheiro (a mesma do seu banco).</p>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className={lbl}>Nome do recebedor</label>
            <input className={inputCls} value={cfg.pix_nome} onChange={(e) => set("pix_nome", e.target.value)} placeholder="Nome da loja" maxLength={25} />
          </div>
          <div>
            <label className={lbl}>Cidade</label>
            <input className={inputCls} value={cfg.pix_cidade} onChange={(e) => set("pix_cidade", e.target.value)} placeholder="Cidade da loja" maxLength={15} />
          </div>
        </div>
        <button disabled={salvando} className="w-full md:w-auto px-6 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-bold rounded-lg flex items-center justify-center gap-2">
          <Save size={18} /> {salvando ? "Salvando..." : "Salvar"}
        </button>
        <p className="text-slate-500 text-[11px] leading-snug">
          O PIX fica separado da maquininha: preencha estes dados para gerar o QR Code na tela do PDV.
        </p>
      </form>
    </motion.div>
  );
}
