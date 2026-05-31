import { BrowserRouter, Routes, Route, Navigate, NavLink, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import PrivateRoute from "./components/PrivateRoute";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import PDV from "./pages/PDV";
import Produtos from "./pages/Produtos";
import Vendas from "./pages/Vendas";
import Categorias from "./pages/Categorias";
import Clientes from "./pages/Clientes";
import ContasReceber from "./pages/ContasReceber";
import Fiscal from "./pages/Fiscal";
import Maquininha from "./pages/Maquininha";
import Caixa from "./pages/Caixa";
import GateAtivacao from "./pages/Ativacao";
import Mascote from "./components/Mascote";
import { clearToken } from "./lib/api";
import { useAuthStore } from "./store/authStore";
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Package, 
  Tags, 
  Users, 
  ReceiptText, 
  Wallet,
  FileText,
  CreditCard,
  Banknote,
  LogOut
} from "lucide-react";

const navItems = [
  { to: "/dashboard", label: "Dashboard", short: "Home", icon: <LayoutDashboard size={20} /> },
  { to: "/pdv", label: "PDV / Vender", short: "PDV", icon: <ShoppingCart size={20} /> },
  { to: "/produtos", label: "Produtos", short: "Produtos", icon: <Package size={20} /> },
  { to: "/categorias", label: "Categorias", short: "Cat.", icon: <Tags size={20} /> },
  { to: "/clientes", label: "Clientes", short: "Clientes", icon: <Users size={20} /> },
  { to: "/vendas", label: "Vendas", short: "Vendas", icon: <ReceiptText size={20} /> },
  { to: "/caixa", label: "Caixa", short: "Caixa", icon: <Banknote size={20} /> },
  { to: "/contas-receber", label: "Contas a Receber", short: "Fiado", icon: <Wallet size={20} /> },
  { to: "/fiscal", label: "Fiscal / NFC-e", short: "Fiscal", icon: <FileText size={20} /> },
  { to: "/maquininha", label: "Maquininha", short: "Cartão", icon: <CreditCard size={20} /> },
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
    <div className="app-shell flex bg-[#020617] text-slate-100 font-sans selection:bg-brand-500/30">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-slate-900/50 backdrop-blur-xl border-r border-slate-800/50 shrink-0 relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-brand-600/10 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="h-20 flex items-center gap-3 px-6 relative z-10">
          <motion.div 
            whileHover={{ scale: 1.1, rotate: 5 }}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/20"
          >
            <ShoppingCart className="text-white" size={20} />
          </motion.div>
          <div>
            <span className="text-white font-black tracking-tight text-lg block uppercase">VendaFácil</span>
            <span className="text-brand-400 font-bold text-[10px] tracking-[0.2em] uppercase -mt-1 block">Sistema PDV</span>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto relative z-10">
          {navItems.map((item) => {
            const active = location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`group flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-300 relative ${
                  active
                    ? "text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                }`}
              >
                {active && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute inset-0 bg-gradient-to-r from-brand-600/20 to-transparent border-l-4 border-brand-500 rounded-xl"
                    initial={false}
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <span className={`relative z-10 transition-transform duration-300 ${active ? "text-brand-400 scale-110" : "group-hover:scale-110"}`}>
                  {item.icon}
                </span>
                <span className="relative z-10">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Mascote Area */}
        <div className="px-6 py-4 flex justify-center border-t border-slate-800/50 relative z-10">
          <Mascote estado="normal" frase="Boas vendas!" />
        </div>

        <div className="p-4 border-t border-slate-800/50 bg-slate-900/40 backdrop-blur-md relative z-10">
          <div className="flex items-center gap-3 px-2 py-1">
            <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-sm font-bold text-brand-400 shadow-inner">
              {(user?.nome || "U")[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-bold truncate">{user?.nome || "Usuário"}</p>
              <p className="text-slate-500 text-[10px] font-medium truncate uppercase tracking-wider">{user?.email}</p>
            </div>
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handleSair}
              className="p-2 text-slate-500 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10"
              title="Sair"
            >
              <LogOut size={18} />
            </motion.button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Glow background principal */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-600/5 blur-[120px] rounded-full pointer-events-none" />

        {/* Topbar mobile */}
        <header className="md:hidden mobile-topbar sticky top-0 z-40 bg-slate-900/80 backdrop-blur-xl border-b border-slate-800/50 px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center shadow-lg shadow-brand-500/20">
                <ShoppingCart className="text-white" size={18} />
              </div>
              <div className="min-w-0">
                <p className="text-white font-black text-sm leading-tight tracking-tight uppercase">VendaFácil</p>
                <div className="flex items-center gap-1.5">
                  <span className="text-brand-400">{currentItem.icon}</span>
                  <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider truncate">{currentItem.label}</p>
                </div>
              </div>
            </div>
            <motion.button
              whileTap={{ scale: 0.9 }}
              onClick={handleSair}
              className="p-2.5 rounded-xl bg-slate-800/50 text-slate-400 hover:text-red-400 border border-slate-700/50"
            >
              <LogOut size={18} />
            </motion.button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-6 pb-28 md:pb-6 relative z-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Bottom navigation mobile */}
        <nav className="md:hidden fixed inset-x-0 bottom-0 z-50 bg-slate-900/80 backdrop-blur-xl border-t border-slate-800/50 safe-bottom">
          <div className="flex gap-1 overflow-x-auto px-3 pt-2 pb-3 mobile-scrollbar">
            {navItems.map((item) => {
              const active = location.pathname.startsWith(item.to);
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={`min-w-[4.5rem] flex-1 flex flex-col items-center justify-center gap-1 rounded-xl px-2 py-2.5 text-[0.65rem] font-bold uppercase tracking-wider transition-all relative ${
                    active
                      ? "text-white"
                      : "text-slate-500 hover:text-white"
                  }`}
                >
                  {active && (
                    <motion.div
                      layoutId="activeNavMobile"
                      className="absolute inset-0 bg-brand-600 rounded-xl shadow-lg shadow-brand-600/20"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10">{item.icon}</span>
                  <span className="relative z-10 whitespace-nowrap">{item.short}</span>
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
      <GateAtivacao>
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
                  <Route path="/caixa" element={<Caixa />} />
                  <Route path="/contas-receber" element={<ContasReceber />} />
                  <Route path="/fiscal" element={<Fiscal />} />
                  <Route path="/maquininha" element={<Maquininha />} />
                  <Route path="*" element={<Navigate to="/pdv" replace />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
      </GateAtivacao>
    </BrowserRouter>
  );
}
