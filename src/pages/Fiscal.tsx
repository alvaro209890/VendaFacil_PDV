import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { FileText, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { getConfigFiscal, salvarConfigFiscal } from "../lib/api";
import type { ConfigFiscal } from "../lib/api";

export default function FiscalPage() {
  const [cfg, setCfg] = useState<ConfigFiscal>({ ambiente: "homologacao", provedor_fiscal: "sefaz_mt_direto", uf: "MT" });
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const { config } = await getConfigFiscal();
      setCfg({ ambiente: "homologacao", provedor_fiscal: "sefaz_mt_direto", uf: "MT", ...config });
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
      if (!payload.certificado_a1_b64) delete payload.certificado_a1_b64;
      if (!payload.certificado_senha) delete payload.certificado_senha;
      if (!payload.resp_tec_csrt) delete payload.resp_tec_csrt;
      const { config } = await salvarConfigFiscal(payload);
      setCfg({ ambiente: "homologacao", provedor_fiscal: "sefaz_mt_direto", uf: "MT", ...config });
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

  async function carregarCertificado(file?: File) {
    if (!file) return;
    const data = await file.arrayBuffer();
    const bytes = new Uint8Array(data);
    let bin = "";
    bytes.forEach((b) => { bin += String.fromCharCode(b); });
    setCfg((c) => ({ ...c, certificado_a1_b64: btoa(bin), certificado_nome: file.name }));
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><FileText size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">Configurações Fiscais (NFC-e)</h1>
          <p className="text-slate-500 text-xs">Dados da loja, certificado A1 e emissão direta SEFAZ-MT.</p>
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
            <p className="text-slate-500 text-xs">Quando ligado, a venda pode gerar NFC-e/NF-e pelo provedor fiscal.</p>
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
          <legend className="text-slate-300 text-xs font-bold uppercase px-2">SEFAZ-MT & Ambiente</legend>
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className={lbl}>Provedor fiscal</label>
              <select className={inputCls} value={cfg.provedor_fiscal || "sefaz_mt_direto"} onChange={(e) => set("provedor_fiscal", e.target.value)}>
                <option value="sefaz_mt_direto">SEFAZ-MT direto</option>
                <option value="focusnfe">Focus NFe (legado)</option>
              </select>
            </div>
            <div>
              <label className={lbl}>Ambiente</label>
              <select className={inputCls} value={cfg.ambiente || "homologacao"} onChange={(e) => set("ambiente", e.target.value)}>
                <option value="homologacao">Homologação (teste)</option>
                <option value="producao">Produção (vale fiscalmente)</option>
              </select>
            </div>
            {cfg.provedor_fiscal !== "sefaz_mt_direto" && (
              <div className="md:col-span-2">
                <label className={lbl}>Token do gateway legado {cfg.gateway_token_preenchido && <span className="text-emerald-400">(já configurado — preencha só para alterar)</span>}</label>
                <input className={inputCls} type="password" value={cfg.gateway_token || ""} onChange={(e) => set("gateway_token", e.target.value)} placeholder={cfg.gateway_token_preenchido ? "••••••••" : "token da API"} />
              </div>
            )}
            <div className="md:col-span-2">
              <label className={lbl}>Certificado A1 da loja {cfg.certificado_a1_b64_preenchido && <span className="text-emerald-400">(salvo)</span>}</label>
              <input className={inputCls} type="file" accept=".pfx,.p12" onChange={(e) => carregarCertificado(e.target.files?.[0])} />
              {cfg.certificado_nome && <p className="text-slate-500 text-[11px] mt-1">{cfg.certificado_nome}</p>}
            </div>
            <div className="md:col-span-2">
              <label className={lbl}>Senha do certificado {cfg.certificado_senha_preenchido && <span className="text-emerald-400">(salva)</span>}</label>
              <input className={inputCls} type="password" value={cfg.certificado_senha || ""} onChange={(e) => set("certificado_senha", e.target.value)} placeholder={cfg.certificado_senha_preenchido ? "preencha só para alterar" : "senha do A1"} />
            </div>
            <div><label className={lbl}>CSC (idCSC) {cfg.csc_preenchido && <span className="text-emerald-400">(salvo)</span>}</label><input className={inputCls} type="password" value={cfg.csc || ""} onChange={(e) => set("csc", e.target.value)} /></div>
            <div><label className={lbl}>ID do CSC (Token)</label><input className={inputCls} value={cfg.csc_id || ""} onChange={(e) => set("csc_id", e.target.value)} placeholder="ex.: 000001" /></div>
            <div><label className={lbl}>Série NFC-e</label><input type="number" className={inputCls} value={cfg.serie_nfce ?? 1} onChange={(e) => set("serie_nfce", Number(e.target.value))} /></div>
            <div><label className={lbl}>Próx. NFC-e</label><input type="number" className={inputCls} value={cfg.proximo_numero_nfce ?? 1} onChange={(e) => set("proximo_numero_nfce", Number(e.target.value))} /></div>
            <div><label className={lbl}>Série NF-e</label><input type="number" className={inputCls} value={cfg.serie_nfe ?? 1} onChange={(e) => set("serie_nfe", Number(e.target.value))} /></div>
            <div><label className={lbl}>Próx. NF-e</label><input type="number" className={inputCls} value={cfg.proximo_numero_nfe ?? 1} onChange={(e) => set("proximo_numero_nfe", Number(e.target.value))} /></div>
          </div>
          <p className="text-slate-500 text-[11px] leading-snug">
            Use o certificado A1 da própria mercearia e o CSC/idCSC liberado pela SEFAZ-MT. Comece em <b>Homologação</b> para testar; só mude para <b>Produção</b> depois de validar com o contador e autorizar notas reais.
          </p>
        </fieldset>

        <details className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <summary className="text-slate-300 text-xs font-bold uppercase cursor-pointer select-none">
            Responsável Técnico (avançado) {cfg.resp_tec_habilitado ? <span className="text-emerald-400 normal-case">— ligado</span> : <span className="text-slate-500 normal-case">— desligado (padrão)</span>}
          </summary>
          <div className="mt-3 space-y-3">
            <p className="text-slate-500 text-[11px] leading-snug">
              <b>Mato Grosso não exige</b> este grupo hoje — deixe <b>desligado</b>. Ligue apenas se a SEFAZ da sua UF passar a exigir o Responsável Técnico (ex.: PR a partir de 2026). Informe o CNPJ da empresa de software. O CSRT só é necessário em UFs que o exijam — sem ele, envia-se apenas o contato.
            </p>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={!!cfg.resp_tec_habilitado} onChange={(e) => set("resp_tec_habilitado", e.target.checked)} className="w-5 h-5 accent-brand-500" />
              <span className="text-white font-bold text-sm">Enviar grupo infRespTec no XML</span>
            </label>
            {cfg.resp_tec_habilitado && (
              <div className="grid md:grid-cols-2 gap-3">
                <div><label className={lbl}>CNPJ (empresa de software)</label><input className={inputCls} value={cfg.resp_tec_cnpj || ""} onChange={(e) => set("resp_tec_cnpj", e.target.value)} placeholder="00.000.000/0001-00" /></div>
                <div><label className={lbl}>Contato</label><input className={inputCls} value={cfg.resp_tec_contato || ""} onChange={(e) => set("resp_tec_contato", e.target.value)} /></div>
                <div><label className={lbl}>E-mail</label><input className={inputCls} value={cfg.resp_tec_email || ""} onChange={(e) => set("resp_tec_email", e.target.value)} /></div>
                <div><label className={lbl}>Telefone</label><input className={inputCls} value={cfg.resp_tec_fone || ""} onChange={(e) => set("resp_tec_fone", e.target.value)} placeholder="só dígitos" /></div>
                <div><label className={lbl}>ID do CSRT</label><input className={inputCls} value={cfg.resp_tec_id_csrt || ""} onChange={(e) => set("resp_tec_id_csrt", e.target.value)} placeholder="ex.: 01" /></div>
                <div><label className={lbl}>CSRT {cfg.resp_tec_csrt_preenchido && <span className="text-emerald-400">(salvo)</span>}</label><input className={inputCls} type="password" value={cfg.resp_tec_csrt || ""} onChange={(e) => set("resp_tec_csrt", e.target.value)} placeholder={cfg.resp_tec_csrt_preenchido ? "preencha só para alterar" : "código fornecido pela SEFAZ"} /></div>
              </div>
            )}
          </div>
        </details>

        <button disabled={salvando} className="w-full md:w-auto px-6 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-bold rounded-lg flex items-center justify-center gap-2">
          <Save size={18} /> {salvando ? "Salvando..." : "Salvar configuração"}
        </button>
      </form>
    </motion.div>
  );
}
