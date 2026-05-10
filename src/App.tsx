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
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/pdv", label: "PDV / Vender", icon: "🛒" },
  { to: "/produtos", label: "Produtos", icon: "📦" },
  { to: "/categorias", label: "Categorias", icon: "🏷️" },
  { to: "/clientes", label: "Clientes", icon: "👥" },
  { to: "/vendas", label: "Vendas", icon: "🧾" },
  { to: "/contas-receber", label: "Contas a Receber", icon: "💰" },
];

function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const clearUser = useAuthStore((s) => s.clearUser);

  function handleSair() {
    clearToken();
    clearUser();
  }

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-64 bg-slate-900 border-r border-slate-800">
        {/* Logo */}
        <div className="h-16 flex items-center gap-2 px-4 border-b border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-sm">
            🛒
          </div>
          <span className="text-white font-bold">VendaFácil PDV</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
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

        {/* User */}
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
              className="text-slate-500 hover:text-red-400 transition-colors"
              title="Sair"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile topbar */}
        <header className="md:hidden h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">🛒</span>
            <span className="text-white font-bold text-sm">VendaFácil PDV</span>
          </div>
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const active = location.pathname.startsWith(item.to);
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    active
                      ? "bg-brand-600/20 text-brand-400"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {item.icon}
                </NavLink>
              );
            })}
            <button
              onClick={handleSair}
              className="ml-2 text-slate-400 hover:text-red-400 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
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
