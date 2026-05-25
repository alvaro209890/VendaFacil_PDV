import { BrowserRouter, Routes, Route, Navigate, NavLink, useLocation } from "react-router-dom";
import PrivateRoute from "./components/PrivateRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import PDV from "./pages/PDV";
import Produtos from "./pages/Produtos";
import Vendas from "./pages/Vendas";
import Categorias from "./pages/Categorias";
import Clientes from "./pages/Clientes";
import ContasReceber from "./pages/ContasReceber";
import { clearToken } from "./lib/api";
import { useAuthStore } from "./store/authStore";

const navItems = [
  { to: "/dashboard", label: "Dashboard", short: "Home", icon: "📊" },
  { to: "/pdv", label: "PDV / Vender", short: "PDV", icon: "🛒" },
  { to: "/produtos", label: "Produtos", short: "Produtos", icon: "📦" },
  { to: "/categorias", label: "Categorias", short: "Cat.", icon: "🏷️" },
  { to: "/clientes", label: "Clientes", short: "Clientes", icon: "👥" },
  { to: "/vendas", label: "Vendas", short: "Vendas", icon: "🧾" },
  { to: "/contas-receber", label: "Contas a Receber", short: "Fiado", icon: "💰" },
];

function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const clearUser = useAuthStore((s) => s.clearUser);
  const currentItem = navItems.find((item) => location.pathname.startsWith(item.to)) ?? navItems[1];

  function handleSair() {
    clearToken();
    clearUser();
  }

  return (
    <div className="app-shell flex bg-slate-950 text-slate-100">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-slate-900 border-r border-slate-800 shrink-0">
        <div className="h-16 flex items-center gap-2 px-4 border-b border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-sm">
            🛒
          </div>
          <span className="text-white font-bold">VendaFácil PDV</span>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-brand-600/20 text-brand-400 border border-brand-600/30"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-3 border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm text-slate-400">
              {(user?.nome || "U")[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">{user?.nome || "Usuário"}</p>
              <p className="text-slate-500 text-xs truncate">{user?.email}</p>
            </div>
            <button
              onClick={handleSair}
              className="touch-target text-slate-500 hover:text-red-400 transition-colors"
              title="Sair"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar mobile: título limpo + sair; navegação fica no rodapé */}
        <header className="md:hidden mobile-topbar sticky top-0 z-40 bg-slate-900/95 backdrop-blur border-b border-slate-800 px-3 py-2.5">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 flex items-center gap-2">
              <span className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center text-base shrink-0">🛒</span>
              <div className="min-w-0">
                <p className="text-white font-bold text-sm leading-tight truncate">VendaFácil PDV</p>
                <p className="text-slate-400 text-xs leading-tight truncate">{currentItem.icon} {currentItem.label}</p>
              </div>
            </div>
            <button
              onClick={handleSair}
              className="touch-target rounded-xl bg-slate-800 text-slate-400 hover:text-red-400 border border-slate-700 active:scale-95"
              aria-label="Sair"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-4 md:p-6 pb-24 md:pb-6">{children}</main>

        {/* Bottom navigation mobile: alvos grandes para dedo e rolagem horizontal sem quebrar layout */}
        <nav className="md:hidden fixed inset-x-0 bottom-0 z-50 bg-slate-900/95 backdrop-blur border-t border-slate-800 safe-bottom">
          <div className="flex gap-1 overflow-x-auto px-2 pt-2 pb-2 mobile-scrollbar">
            {navItems.map((item) => {
              const active = location.pathname.startsWith(item.to);
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`min-w-[4.25rem] flex-1 flex flex-col items-center justify-center gap-0.5 rounded-xl px-2 py-2 text-[0.68rem] font-medium transition-colors active:scale-95 ${
                    active
                      ? "bg-brand-600 text-white shadow-lg shadow-brand-950/30"
                      : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  <span className="text-lg leading-none">{item.icon}</span>
                  <span className="whitespace-nowrap">{item.short}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/pdv" element={<PDV />} />
                  <Route path="/produtos" element={<Produtos />} />
                  <Route path="/categorias" element={<Categorias />} />
                  <Route path="/clientes" element={<Clientes />} />
                  <Route path="/vendas" element={<Vendas />} />
                  <Route path="/contas-receber" element={<ContasReceber />} />
                  <Route path="*" element={<Navigate to="/pdv" replace />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
