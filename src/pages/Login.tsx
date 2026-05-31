import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Lock, 
  User, 
  ShoppingCart,
  ChevronRight,
  AlertCircle,
  Loader2
} from "lucide-react";
import { login, registro, setToken } from "../lib/api";
import { useAuthStore } from "../store/authStore";

export default function Login() {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [modo, setModo] = useState<"login" | "registro">("login");
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    if (!usuario.trim() || !senha.trim()) {
      setErro("Preencha todos os campos.");
      return;
    }
    setCarregando(true);
    try {
      const data = await login(usuario.trim(), senha);
      setToken(data.token);
      setUser(data.user);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setErro((err as Error).message || "Erro ao entrar.");
    } finally {
      setCarregando(false);
    }
  }

  async function handleRegistro(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    if (!usuario.trim() || !senha.trim() || !nome.trim()) {
      setErro("Preencha todos os campos.");
      return;
    }
    if (senha.length < 4) {
      setErro("A senha deve ter pelo menos 4 caracteres.");
      return;
    }
    setCarregando(true);
    try {
      const data = await registro(usuario.trim(), nome.trim(), senha);
      setToken(data.token);
      setUser(data.user);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setErro((err as Error).message || "Erro ao cadastrar.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] p-4 relative overflow-hidden">
      {/* Background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand-600/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-emerald-600/10 blur-[120px] rounded-full" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-[440px] relative z-10"
      >
        {/* Logo Section */}
        <div className="text-center mb-10">
          <motion.div 
            whileHover={{ scale: 1.05, rotate: 5 }}
            className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-brand-500 to-brand-700 mb-6 shadow-2xl shadow-brand-500/20"
          >
            <ShoppingCart className="text-white" size={32} />
          </motion.div>
          <h1 className="text-4xl font-black text-white tracking-tighter mb-2">VENDAFÁCIL</h1>
          <p className="text-slate-500 font-bold text-xs uppercase tracking-[0.4em]">Gestão Inteligente de PDV</p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/50 backdrop-blur-2xl rounded-[32px] shadow-2xl border border-slate-800/50 p-8 sm:p-10 relative overflow-hidden">
          {/* Subtle reflection */}
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />
          
          {/* Abas */}
          <div className="flex gap-1 bg-slate-950/50 border border-slate-800/50 rounded-2xl p-1.5 mb-8">
            <button
              onClick={() => { setModo("login"); setErro(""); }}
              className={`flex-1 py-2.5 text-xs font-black uppercase tracking-widest rounded-xl transition-all duration-300 ${
                modo === "login" 
                  ? "bg-brand-600 text-white shadow-lg shadow-brand-600/20" 
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Login
            </button>
            <button
              onClick={() => { setModo("registro"); setErro(""); }}
              className={`flex-1 py-2.5 text-xs font-black uppercase tracking-widest rounded-xl transition-all duration-300 ${
                modo === "registro" 
                  ? "bg-brand-600 text-white shadow-lg shadow-brand-600/20" 
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              Registro
            </button>
          </div>

          <AnimatePresence mode="wait">
            {erro && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px] font-bold uppercase tracking-wider rounded-xl p-4 mb-6 flex items-center gap-3"
              >
                <AlertCircle size={14} className="shrink-0" />
                {erro}
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            <motion.form
              key={modo}
              initial={{ opacity: 0, x: modo === "login" ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: modo === "login" ? 10 : -10 }}
              transition={{ duration: 0.2 }}
              onSubmit={modo === "login" ? handleLogin : handleRegistro} 
              className="space-y-5"
            >
              {modo === "registro" && (
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Nome Completo</label>
                  <div className="relative group">
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-brand-500 transition-colors">
                      <User size={18} />
                    </div>
                    <input 
                      type="text" 
                      value={nome} 
                      onChange={(e) => setNome(e.target.value)} 
                      placeholder="Ex: João Silva" 
                      className="w-full pl-12 pr-4 py-4 bg-slate-950/50 border border-slate-800 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-brand-500/50 focus:ring-4 focus:ring-brand-500/5 transition-all text-sm font-medium shadow-inner" 
                    />
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Usuário</label>
                <div className="relative group">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-brand-500 transition-colors">
                    <User size={18} />
                  </div>
                  <input 
                    type="text" 
                    value={usuario} 
                    onChange={(e) => setUsuario(e.target.value)} 
                    placeholder="Ex: teste" 
                    autoCapitalize="none"
                    className="w-full pl-12 pr-4 py-4 bg-slate-950/50 border border-slate-800 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-brand-500/50 focus:ring-4 focus:ring-brand-500/5 transition-all text-sm font-medium shadow-inner" 
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Senha de Acesso</label>
                <div className="relative group">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-brand-500 transition-colors">
                    <Lock size={18} />
                  </div>
                  <input 
                    type="password" 
                    value={senha} 
                    onChange={(e) => setSenha(e.target.value)} 
                    placeholder="••••••••" 
                    className="w-full pl-12 pr-4 py-4 bg-slate-950/50 border border-slate-800 rounded-2xl text-white placeholder-slate-600 focus:outline-none focus:border-brand-500/50 focus:ring-4 focus:ring-brand-500/5 transition-all text-sm font-medium shadow-inner" 
                  />
                </div>
              </div>

              <motion.button 
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit" 
                disabled={carregando} 
                className="w-full py-4 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 disabled:opacity-50 text-white font-black uppercase tracking-widest rounded-2xl shadow-xl shadow-brand-900/20 transition-all flex items-center justify-center gap-3 mt-4"
              >
                {carregando ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <>
                    <span>{modo === "login" ? "Entrar no Sistema" : "Criar Minha Conta"}</span>
                    <ChevronRight size={18} />
                  </>
                )}
              </motion.button>
            </motion.form>
          </AnimatePresence>

          <p className="text-center text-slate-600 text-[10px] font-bold uppercase tracking-widest mt-8">
            Ambiente Seguro & Criptografado
          </p>
        </div>
      </motion.div>
    </div>
  );
}

