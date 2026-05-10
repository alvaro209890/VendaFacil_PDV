import { useState, useEffect, useCallback } from "react";
import { listarProdutos, checkout, getDashboard } from "../lib/api";
import type { Produto, DashboardData } from "../lib/api";

type CartItem = Produto & { qtd: number };

const PAGAMENTOS = [
  { value: "dinheiro", label: "Dinheiro", icon: "💵" },
  { value: "pix", label: "PIX", icon: "📱" },
  { value: "debito", label: "Débito", icon: "💳" },
  { value: "credito", label: "Crédito", icon: "💳" },
];

export default function PDV() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [busca, setBusca] = useState("");
  const [carrinho, setCarrinho] = useState<CartItem[]>([]);
  const [desconto, setDesconto] = useState(0);
  const [pagamento, setPagamento] = useState("dinheiro");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [dash, setDash] = useState<DashboardData | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [p, d] = await Promise.all([listarProdutos(true), getDashboard()]);
      setProdutos(p.produtos.filter((x) => x.estoque > 0));
      setDash(d);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const filtrados = busca
    ? produtos.filter(
        (p) =>
          p.nome.toLowerCase().includes(busca.toLowerCase()) ||
          p.codigo_barras.includes(busca)
      )
    : produtos;

  function addAoCarrinho(p: Produto) {
    setCarrinho((prev) => {
      const existe = prev.find((i) => i.id === p.id);
      if (existe) {
        if (existe.qtd >= p.estoque) return prev;
        return prev.map((i) => (i.id === p.id ? { ...i, qtd: i.qtd + 1 } : i));
      }
      return [...prev, { ...p, qtd: 1 }];
    });
    setMsg(null);
  }

  function removerDoCarrinho(id: number) {
    setCarrinho((prev) => prev.filter((i) => i.id !== id));
  }

  function alterarQtd(id: number, delta: number) {
    setCarrinho((prev) =>
      prev.map((i) => {
        if (i.id !== id) return i;
        const nova = i.qtd + delta;
        if (nova < 1 || nova > i.estoque) return i;
        return { ...i, qtd: nova };
      })
    );
  }

  const subtotal = carrinho.reduce((s, i) => s + i.qtd * (i.preco_venda || i.preco_custo), 0);
  const total = Math.max(0, subtotal - desconto);

  async function finalizarVenda() {
    if (carrinho.length === 0) return;
    setLoading(true);
    setMsg(null);
    try {
      await checkout({
        itens: carrinho.map((i) => ({ produto_id: i.id, quantidade: i.qtd })),
        desconto,
        forma_pagamento: pagamento,
      });
      setMsg({ tipo: "ok", texto: `Venda finalizada! Total: R$ ${total.toFixed(2)}` });
      setCarrinho([]);
      setDesconto(0);
      setPagamento("dinheiro");
      carregar();
    } catch (err: unknown) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setLoading(false);
    }
  }

  const itensCarrinho = carrinho.length;

  return (
    <div className="flex flex-col lg:flex-row gap-4 h-full">
      {/* Coluna esquerda: Produtos */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Busca */}
        <div className="mb-3">
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar produto por nome ou código de barras..."
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 text-sm"
            autoFocus
          />
        </div>

        {/* Grade de produtos */}
        <div className="flex-1 overflow-y-auto rounded-xl bg-slate-900 border border-slate-800 p-3">
          {filtrados.length === 0 ? (
            <div className="text-center text-slate-500 py-12">
              {busca ? "Nenhum produto encontrado." : "Nenhum produto cadastrado. Adicione produtos primeiro."}
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-2">
              {filtrados.map((p) => {
                const preco = p.preco_venda || p.preco_custo;
                const baixo = p.estoque <= p.estoque_minimo;
                return (
                  <button
                    key={p.id}
                    onClick={() => addAoCarrinho(p)}
                    className="text-left bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-brand-600 rounded-lg p-3 transition-all active:scale-95"
                  >
                    <p className="text-white text-sm font-medium truncate">{p.nome}</p>
                    <p className="text-brand-400 font-bold text-lg mt-0.5">R$ {preco.toFixed(2)}</p>
                    <p className={`text-xs mt-1 ${baixo ? "text-amber-400" : "text-slate-500"}`}>
                      {baixo ? `⚠️ Só ${p.estoque} ${p.unidade}` : `${p.estoque} ${p.unidade}`}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Coluna direita: Carrinho + Checkout */}
      <div className="w-full lg:w-96 flex flex-col bg-slate-900 border border-slate-800 rounded-xl p-4">
        <h2 className="text-white font-bold text-lg mb-3">
          🛒 Carrinho {itensCarrinho > 0 && <span className="text-brand-400">({itensCarrinho})</span>}
        </h2>

        {carrinho.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8 flex-1 flex items-center justify-center">
            Toque nos produtos para adicionar
          </p>
        ) : (
          <>
            {/* Itens */}
            <div className="flex-1 overflow-y-auto space-y-2 mb-3">
              {carrinho.map((i) => {
                const preco = i.preco_venda || i.preco_custo;
                const sub = i.qtd * preco;
                return (
                  <div key={i.id} className="flex items-center gap-2 bg-slate-800 rounded-lg p-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm truncate">{i.nome}</p>
                      <p className="text-slate-400 text-xs">R$ {preco.toFixed(2)} × {i.qtd}</p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => alterarQtd(i.id, -1)}
                        className="w-7 h-7 rounded bg-slate-700 text-white text-sm hover:bg-slate-600"
                      >
                        −
                      </button>
                      <span className="text-white text-sm w-6 text-center">{i.qtd}</span>
                      <button
                        onClick={() => alterarQtd(i.id, 1)}
                        className="w-7 h-7 rounded bg-slate-700 text-white text-sm hover:bg-slate-600"
                      >
                        +
                      </button>
                    </div>
                    <p className="text-brand-400 font-bold text-sm w-20 text-right">R$ {sub.toFixed(2)}</p>
                    <button
                      onClick={() => removerDoCarrinho(i.id)}
                      className="text-red-400 hover:text-red-300 text-lg px-1"
                      title="Remover"
                    >
                      ×
                    </button>
                  </div>
                );
              })}
            </div>

            {/* Totais */}
            <div className="border-t border-slate-700 pt-3 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Subtotal</span>
                <span className="text-white">R$ {subtotal.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Desconto</span>
                <input
                  type="number"
                  value={desconto || ""}
                  onChange={(e) => setDesconto(Number(e.target.value) || 0)}
                  placeholder="0.00"
                  min={0}
                  max={subtotal}
                  step={0.01}
                  className="w-24 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-white text-right text-sm focus:outline-none focus:border-brand-500"
                />
              </div>
              <div className="flex justify-between font-bold text-lg">
                <span className="text-white">Total</span>
                <span className="text-brand-400">R$ {total.toFixed(2)}</span>
              </div>
            </div>

            {/* Pagamento */}
            <div className="mt-3">
              <label className="text-slate-400 text-xs mb-1 block">Pagamento</label>
              <div className="grid grid-cols-4 gap-1">
                {PAGAMENTOS.map((fp) => (
                  <button
                    key={fp.value}
                    onClick={() => setPagamento(fp.value)}
                    className={`py-2 rounded-lg text-xs font-medium transition-colors ${
                      pagamento === fp.value
                        ? "bg-brand-600 text-white"
                        : "bg-slate-800 text-slate-400 hover:text-white"
                    }`}
                  >
                    <span className="block text-base">{fp.icon}</span>
                    {fp.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Botão finalizar */}
            <button
              onClick={finalizarVenda}
              disabled={loading || carrinho.length === 0}
              className="mt-4 w-full py-3 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold rounded-xl transition-colors text-lg"
            >
              {loading ? "Processando..." : `Finalizar Venda • R$ ${total.toFixed(2)}`}
            </button>
          </>
        )}

        {/* Mensagem de feedback */}
        {msg && (
          <div
            className={`mt-3 p-3 rounded-lg text-sm ${
              msg.tipo === "ok"
                ? "bg-green-500/10 border border-green-500/30 text-green-400"
                : "bg-red-500/10 border border-red-500/30 text-red-400"
            }`}
          >
            {msg.texto}
          </div>
        )}

        {/* Mini resumo */}
        {dash && (
          <div className="mt-auto pt-3 border-t border-slate-800 flex gap-3 text-xs text-slate-500">
            <span>{dash.total_produtos} produtos</span>
            <span>{dash.vendas_hoje_qtd} vendas hoje</span>
            <span>R$ {(dash.vendas_hoje_total || 0).toFixed(2)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
