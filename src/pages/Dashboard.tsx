import { useNavigate } from "react-router-dom";
import { clearToken } from "../lib/api";
import { useAuthStore } from "../store/authStore";

const cards = [
  {
    titulo: "Produtos",
    descricao: "Gerencie seu catálogo de produtos",
    cor: "from-blue-600 to-blue-500",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
    ),
  },
  {
    titulo: "Vendas",
    descricao: "Registre vendas e emita NFC-e",
    cor: "from-green-600 to-green-500",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
      </svg>
    ),
  },
  {
    titulo: "Estoque",
    descricao: "Controle de inventário e alertas",
    cor: "from-amber-600 to-amber-500",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
      </svg>
    ),
  },
  {
    titulo: "Relatórios",
    descricao: "Acompanhe vendas e desempenho",
    cor: "from-purple-600 to-purple-500",
    icone: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clearUser = useAuthStore((s) => s.clearUser);

  function handleSair() {
    clearToken();
    clearUser();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Topbar */}
      <header className="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 md:px-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
            </svg>
          </div>
          <span className="text-white font-bold text-sm md:text-base">VendaFácil PDV</span>
        </div>

        <div className="flex items-center gap-4">
          <span className="text-slate-400 text-sm hidden sm:inline">{user?.email}</span>
          <button
            onClick={handleSair}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-800"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span className="hidden sm:inline">Sair</span>
          </button>
        </div>
      </header>

      {/* Conteúdo */}
      <main className="max-w-6xl mx-auto p-4 md:p-6">
        <div className="mb-8">
          <h2 className="text-xl md:text-2xl font-bold text-white">
            Bem-vindo, {user?.nome || user?.email?.split("@")[0] || "Usuário"}!
          </h2>
          <p className="text-slate-400 mt-1 text-sm md:text-base">
            Gerencie seu mercadinho com eficiência.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((card) => (
            <div
              key={card.titulo}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors cursor-pointer group"
            >
              <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${card.cor} flex items-center justify-center text-white mb-3 group-hover:scale-110 transition-transform`}>
                {card.icone}
              </div>
              <h3 className="text-white font-semibold text-sm">{card.titulo}</h3>
              <p className="text-slate-400 text-xs mt-1">{card.descricao}</p>
              <span className="inline-block mt-3 text-xs text-slate-600 bg-slate-800 px-2 py-0.5 rounded">
                Em breve
              </span>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
