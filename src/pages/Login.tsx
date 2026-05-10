import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, registro, setToken } from "../lib/api";
import { useAuthStore } from "../store/authStore";

export default function Login() {
  const [email, setEmail] = useState("");
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
    if (!email.trim() || !senha.trim()) {
      setErro("Preencha todos os campos.");
      return;
    }
    setCarregando(true);
    try {
      const data = await login(email.trim(), senha);
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
    if (!email.trim() || !senha.trim() || !nome.trim()) {
      setErro("Preencha todos os campos.");
      return;
    }
    if (senha.length < 4) {
      setErro("A senha deve ter pelo menos 4 caracteres.");
      return;
    }
    setCarregando(true);
    try {
      const data = await registro(email.trim(), nome.trim(), senha);
      setToken(data.token);
      setUser(data.user);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      setErro((err as Error).message || "Erro ao cadastrar.");
    } finally {
      setCarregando(false);
    }
  }

  const IconCarrinho = (
    <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
    </svg>
  );

  const IconEmail = (
    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );

  const IconLock = (
    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  );

  const IconUser = (
    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-600 mb-4">
            {IconCarrinho}
          </div>
          <h1 className="text-2xl font-bold text-white">VendaFácil PDV</h1>
          <p className="text-slate-400 text-sm mt-1">Sistema de PDV para mercadinhos</p>
        </div>

        {/* Card */}
        <div className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-800 p-6">
          {/* Abas */}
          <div className="flex gap-1 bg-slate-800 rounded-lg p-1 mb-6">
            <button
              onClick={() => { setModo("login"); setErro(""); }}
              className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${modo === "login" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}
            >
              Entrar
            </button>
            <button
              onClick={() => { setModo("registro"); setErro(""); }}
              className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${modo === "registro" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}
            >
              Criar conta
            </button>
          </div>

          {erro && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-lg p-3 mb-4">
              {erro}
            </div>
          )}

          {modo === "login" && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">E-mail</label>
                <div className="relative">
                  {IconEmail}
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="seu@email.com" className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Senha</label>
                <div className="relative">
                  {IconLock}
                  <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="••••••••" className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm" />
                </div>
              </div>
              <button type="submit" disabled={carregando} className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2">
                {carregando && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                {carregando ? "Entrando..." : "Entrar"}
              </button>
            </form>
          )}

          {modo === "registro" && (
            <form onSubmit={handleRegistro} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Nome</label>
                <div className="relative">
                  {IconUser}
                  <input type="text" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome" className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">E-mail</label>
                <div className="relative">
                  {IconEmail}
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="seu@email.com" className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Senha</label>
                <div className="relative">
                  {IconLock}
                  <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Mínimo 4 caracteres" className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm" />
                </div>
              </div>
              <button type="submit" disabled={carregando} className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2">
                {carregando && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                {carregando ? "Criando conta..." : "Criar conta"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
