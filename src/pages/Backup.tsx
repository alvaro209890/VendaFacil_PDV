import { useState, useEffect, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Database, Download, Upload, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { baixarBackup, restaurarBackup, listarBackups } from "../lib/api";
import type { BackupItem } from "../lib/api";

export default function BackupPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [pasta, setPasta] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      const r = await listarBackups();
      setBackups(r.backups);
      setPasta(r.pasta);
    } catch { /* silencioso */ }
  }, []);
  useEffect(() => { void carregar(); }, [carregar]);

  async function baixar() {
    setBusy(true); setMsg(null);
    try {
      await baixarBackup();
      setMsg({ tipo: "ok", texto: "Backup gerado e baixado. Guarde em local seguro (pen drive, nuvem)." });
      carregar();
    } catch (e) { setMsg({ tipo: "erro", texto: (e as Error).message }); }
    finally { setBusy(false); }
  }

  async function onArquivo(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!confirm("Restaurar este backup vai SUBSTITUIR todos os dados atuais (produtos, vendas, etc.). O estado atual será salvo automaticamente antes. Continuar?")) return;
    setBusy(true); setMsg(null);
    try {
      await restaurarBackup(file);
      setMsg({ tipo: "ok", texto: "Backup restaurado! A página será recarregada." });
      setTimeout(() => window.location.reload(), 1500);
    } catch (e) { setMsg({ tipo: "erro", texto: (e as Error).message }); setBusy(false); }
  }

  const fmtData = (iso: string) => new Date(iso).toLocaleString("pt-BR");

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-brand-600/20 grid place-items-center text-brand-400"><Database size={20} /></div>
        <div>
          <h1 className="text-xl font-black text-white">Backup</h1>
          <p className="text-slate-500 text-xs">Proteja os dados da loja: baixe cópias e restaure quando precisar.</p>
        </div>
      </div>

      {msg && (
        <div className={`mb-4 px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${msg.tipo === "ok" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
          {msg.tipo === "ok" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />} {msg.texto}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-3 mb-6">
        <button onClick={baixar} disabled={busy} className="flex items-center justify-center gap-2 p-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white rounded-2xl font-bold">
          <Download size={18} /> Baixar backup agora
        </button>
        <input ref={fileRef} type="file" accept=".db" onChange={onArquivo} className="hidden" />
        <button onClick={() => fileRef.current?.click()} disabled={busy} className="flex items-center justify-center gap-2 p-4 bg-slate-800 hover:bg-slate-700 disabled:opacity-60 text-white rounded-2xl font-bold">
          <Upload size={18} /> Restaurar de um arquivo
        </button>
      </div>

      <div className="bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded-xl p-3 text-xs mb-6">
        <b>Backups automáticos</b> são feitos todo dia e a cada inicialização — ficam na pasta
        <code className="mx-1 text-amber-200">{pasta || "dados/backups"}</code> na máquina.
        Mesmo assim, <b>baixe um backup de vez em quando</b> e guarde fora do computador
        (pen drive/nuvem): se o PC pifar, a pasta local vai junto.
      </div>

      <h2 className="text-slate-300 font-bold text-sm mb-2 flex items-center gap-2"><Clock size={15} /> Backups na máquina</h2>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        {backups.length === 0 ? (
          <p className="text-slate-500 text-sm p-4">Nenhum backup ainda.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {backups.map((b) => (
                <tr key={b.nome} className="border-b border-slate-800 last:border-0">
                  <td className="p-3 text-slate-300 font-mono text-xs truncate">{b.nome}</td>
                  <td className="p-3 text-slate-500 whitespace-nowrap">{fmtData(b.data)}</td>
                  <td className="p-3 text-slate-500 text-right whitespace-nowrap">{b.tamanho_kb} KB</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </motion.div>
  );
}
