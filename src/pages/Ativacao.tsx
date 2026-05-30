import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { ShoppingCart, KeyRound, Loader2, AlertCircle, WifiOff } from "lucide-react";
import { getAtivacaoStatus, ativar } from "../lib/api";
import type { AtivacaoStatus } from "../lib/api";

/**
 * Porteiro de licença. Enquanto o sistema não estiver ativado (ou estiver
 * bloqueado pelo painel), mostra a tela de ativação. Caso contrário, libera
 * o app normalmente. Se a licença não for obrigatória (modo local), passa direto.
 */
export default function GateAtivacao({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AtivacaoStatus | null>(null);
  const [carregando, setCarregando] = useState(true);

  const checar = useCallback(async () => {
    try {
      setStatus(await getAtivacaoStatus());
    } catch {
      // Backend antigo/sem endpoint → não bloqueia (modo local).
      setStatus({ obrigatoria: false, ativado: true, bloqueado: false, motivo: "" });
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void checar();
  }, [checar]);

  if (carregando) {
    return (
      <div className="min-h-screen bg-[#020617] grid place-items-center text-slate-500">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  if (status && (!status.obrigatoria || (status.ativado && !status.bloqueado))) {
    return <>{children}</>;
  }

  return <TelaAtivacao status={status!} onAtivado={checar} />;
}

function TelaAtivacao({ status, onAtivado }: { status: AtivacaoStatus; onAtivado: () => void }) {
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Já ativado, porém bloqueado (conta suspensa / licença vencida / sem revalidar).
  const bloqueadoAtivado = status.ativado && status.bloqueado;

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const novo = await ativar(login.trim(), senha);
      if (novo.bloqueado) setErro(novo.motivo);
      else onAtivado();
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl bg-emerald-600/20 grid place-items-center text-emerald-400">
            <ShoppingCart size={24} />
          </div>
          <h1 className="text-2xl font-black text-white">
            VendaFácil <span className="text-emerald-400">PDV</span>
          </h1>
        </div>

        {bloqueadoAtivado ? (
          <div className="mt-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 text-amber-300 text-sm flex gap-3">
            <WifiOff size={18} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-bold mb-1">Acesso suspenso</p>
              <p>{status.motivo}</p>
            </div>
          </div>
        ) : (
          <p className="text-slate-400 text-sm mt-2 mb-6">
            Primeiro acesso — ative o sistema com a conta da sua loja
            (fornecida no momento da contratação).
          </p>
        )}

        <form onSubmit={enviar} className="space-y-3 mt-6">
          <div className="relative">
            <span className="absolute inset-y-0 left-3 flex items-center text-slate-500"><KeyRound size={18} /></span>
            <input
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="Login da loja"
              required
              autoFocus
              className="w-full pl-11 pr-3 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            placeholder="Senha da loja"
            required
            className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
          />
          {erro && (
            <p className="text-red-400 text-sm flex items-center gap-2">
              <AlertCircle size={16} /> {erro}
            </p>
          )}
          <button
            disabled={enviando}
            className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white font-black uppercase tracking-wide rounded-xl py-3 transition-all flex items-center justify-center gap-2"
          >
            {enviando ? <Loader2 size={18} className="animate-spin" /> : "Ativar sistema"}
          </button>
        </form>

        <p className="text-slate-600 text-xs text-center mt-6">
          Após ativar, o sistema funciona mesmo sem internet.
        </p>
      </motion.div>
    </div>
  );
}
