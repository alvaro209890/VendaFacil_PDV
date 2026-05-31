import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, 
  ShoppingCart, 
  Trash2, 
  Plus, 
  Minus, 
  Smartphone, 
  CreditCard, 
  Banknote, 
  FileText, 
  CheckCircle2,
  X,
  AlertCircle
} from "lucide-react";
import {
  listarProdutos, checkout, getDashboard, gerarPixQrCode, listarClientes,
  getConfigMaquininha, criarCobrancaMaquininha, consultarCobrancaMaquininha,
  cancelarCobrancaMaquininha, getConfigFiscal,
} from "../lib/api";
import type { Produto, DashboardData, PixQrCodeResponse, Cliente } from "../lib/api";
import { imprimirRecibo, getLarguraRecibo, setLarguraRecibo } from "../lib/recibo";
import type { ReciboData } from "../lib/recibo";
import Mascote from "../components/Mascote";

type CartItem = Produto & { qtd: number };

const PAGAMENTOS = [
  { value: "dinheiro", label: "Dinheiro", icon: <Banknote size={18} /> },
  { value: "pix", label: "PIX", icon: <Smartphone size={18} /> },
  { value: "debito", label: "Débito", icon: <CreditCard size={18} /> },
  { value: "credito", label: "Crédito", icon: <CreditCard size={18} /> },
  { value: "fiado", label: "Fiado", icon: <FileText size={18} /> },
];

// Estados da cobrança Point → texto amigável exibido no modal.
const ESTADO_MAQ: Record<string, string> = {
  OPEN: "Enviando para a maquininha...",
  ON_TERMINAL: "Aguardando o cartão na maquininha...",
  PROCESSING: "Processando o pagamento...",
  FINISHED: "Pagamento aprovado!",
};

const fmtQtd = (v: number) => Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
const passoQtd = (unidade?: string) => ["KG", "G", "LT", "ML"].includes((unidade || "").toUpperCase()) ? 0.1 : 1;

export default function PDV() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [busca, setBusca] = useState("");
  const [carrinho, setCarrinho] = useState<CartItem[]>([]);
  const [desconto, setDesconto] = useState(0);
  const [pagamento, setPagamento] = useState("dinheiro");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteFiado, setClienteFiado] = useState<number | "">("");
  const [emitirNota, setEmitirNota] = useState(false);
  const [cpfConsumidor, setCpfConsumidor] = useState("");

  // PIX QR Code state
  const [pixModal, setPixModal] = useState<PixQrCodeResponse | null>(null);
  const [pixLoading, setPixLoading] = useState(false);

  // Recibo (impressora térmica)
  const [lojaInfo, setLojaInfo] = useState<{ nome: string; cnpj?: string; endereco?: string }>({ nome: "VendaFácil PDV" });
  const [ultimaVenda, setUltimaVenda] = useState<ReciboData | null>(null);
  const [imprimirAuto, setImprimirAuto] = useState(() => localStorage.getItem("recibo_auto") === "1");
  const [largura, setLargura] = useState<58 | 80>(getLarguraRecibo());

  // Maquininha (Mercado Pago Point) — cobrança integrada, só quando online.
  const [maqHabilitada, setMaqHabilitada] = useState(false);
  const [maqDeviceOk, setMaqDeviceOk] = useState(false);
  const [maqModal, setMaqModal] = useState<{
    fase: "criando" | "aguardando" | "erro";
    intentId?: string;
    estado?: string;
    erro?: string;
  } | null>(null);
  const maqPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [p, d, c] = await Promise.all([listarProdutos(true), getDashboard(), listarClientes()]);
      setProdutos(p.produtos.filter((x) => x.estoque > 0));
      setDash(d);
      setClientes(c.clientes);
    } catch {
      // silent
    }
    // Config da maquininha (separado: não pode derrubar o carregamento do PDV).
    try {
      const { config } = await getConfigMaquininha();
      setMaqHabilitada(!!config.habilitado);
      setMaqDeviceOk(!!config.device_id);
    } catch {
      setMaqHabilitada(false);
    }
    // Cabeçalho do recibo (usa os dados fiscais da loja, se preenchidos).
    try {
      const { config } = await getConfigFiscal();
      const partes = [config.logradouro, config.numero, config.bairro, config.municipio, config.uf]
        .filter(Boolean).join(", ");
      setLojaInfo({
        nome: config.nome_fantasia || config.razao_social || "VendaFácil PDV",
        cnpj: config.cnpj || undefined,
        endereco: partes || undefined,
      });
    } catch { /* mantém o padrão */ }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const filtrados = busca
    ? produtos.filter(
        (p) =>
          p.nome.toLowerCase().includes(busca.toLowerCase()) ||
          p.codigo_barras.includes(busca)
      )
    : produtos;

  const buscaRef = useRef<HTMLInputElement>(null);

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

  // Leitor de código de barras / Enter: bipa → adiciona → limpa → mantém o foco.
  function onBuscaKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setBusca("");
      return;
    }
    if (e.key !== "Enter") return;
    e.preventDefault();
    const termo = busca.trim();
    if (!termo) return;
    const exato = produtos.find((p) => p.codigo_barras && p.codigo_barras === termo);
    const alvo = exato || (filtrados.length >= 1 ? filtrados[0] : null);
    if (alvo) {
      addAoCarrinho(alvo);
      setBusca("");
    } else {
      setMsg({ tipo: "erro", texto: `Nada encontrado para "${termo}".` });
    }
    buscaRef.current?.focus();
  }

  // Atalhos globais: F2 finaliza a venda, F4 foca a busca.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "F2") {
        e.preventDefault();
        if (carrinho.length > 0 && !loading && !maqModal && !pixModal) void finalizarVenda();
      } else if (e.key === "F4") {
        e.preventDefault();
        buscaRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carrinho, loading, pagamento, clienteFiado, desconto, maqModal, pixModal]);

  function removerDoCarrinho(id: number) {
    setCarrinho((prev) => prev.filter((i) => i.id !== id));
  }

  function alterarQtd(id: number, delta: number) {
    setCarrinho((prev) =>
      prev.map((i) => {
        if (i.id !== id) return i;
        const nova = Number((i.qtd + delta).toFixed(3));
        if (nova <= 0 || nova > i.estoque) return i;
        return { ...i, qtd: nova };
      })
    );
  }

  function definirQtd(id: number, valor: number) {
    setCarrinho((prev) =>
      prev.map((i) => {
        if (i.id !== id) return i;
        const nova = Number((valor || 0).toFixed(3));
        if (nova <= 0) return { ...i, qtd: 0.001 };
        return { ...i, qtd: Math.min(nova, i.estoque) };
      })
    );
  }

  const subtotal = carrinho.reduce((s, i) => s + i.qtd * (i.preco_venda || i.preco_custo), 0);
  const total = Math.max(0, subtotal - desconto);

  async function gerarPix() {
    if (carrinho.length === 0 || total <= 0) return;
    setPixLoading(true);
    setMsg(null);
    try {
      const pix = await gerarPixQrCode(total);
      setPixModal(pix);
    } catch (err: unknown) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setPixLoading(false);
    }
  }

  function cancelarPix() {
    setPixModal(null);
  }

  // Para o polling da maquininha (se estiver rodando).
  const pararPollMaquininha = useCallback(() => {
    if (maqPollRef.current) {
      clearInterval(maqPollRef.current);
      maqPollRef.current = null;
    }
  }, []);

  // Limpa o polling se a tela for desmontada.
  useEffect(() => pararPollMaquininha, [pararPollMaquininha]);

  // Cobrança pela maquininha (cartão OU PIX) só vale quando: habilitada, com
  // dispositivo configurado E com internet. Sem isso, cartão = manual e PIX =
  // QR estático na tela do PDV.
  const podeCobrarMaquininha =
    (pagamento === "debito" || pagamento === "credito" || pagamento === "pix") &&
    maqHabilitada && maqDeviceOk && navigator.onLine;

  async function finalizarVenda() {
    if (carrinho.length === 0) return;
    if (podeCobrarMaquininha) {
      await iniciarCobrancaMaquininha();   // cartão ou PIX na telinha da maquininha
      return;
    }
    if (pagamento === "pix") {
      await gerarPix();                    // sem maquininha → QR estático no PDV
      return;
    }
    await confirmarVenda();
  }

  async function iniciarCobrancaMaquininha() {
    setMsg(null);
    setMaqModal({ fase: "criando" });
    const uuid = crypto.randomUUID();
    let intentId: string;
    try {
      const r = await criarCobrancaMaquininha(total, uuid, pagamento);
      intentId = r.payment_intent_id;
    } catch (err) {
      // Falhou ao acionar a máquina (ex.: caiu a internet) → oferece manual.
      setMaqModal({ fase: "erro", erro: (err as Error).message });
      return;
    }
    setMaqModal({ fase: "aguardando", intentId, estado: "OPEN" });

    // Poll do status até concluir/cancelar/dar erro.
    pararPollMaquininha();
    maqPollRef.current = setInterval(async () => {
      try {
        const st = await consultarCobrancaMaquininha(intentId);
        setMaqModal((m) => (m ? { ...m, estado: st.state } : m));
        if (st.pago && st.payment_status === "approved") {
          pararPollMaquininha();
          const obs = st.payment_id ? `MP Point: ${st.payment_id}` : undefined;
          setMaqModal(null);
          await confirmarVenda(obs);
        } else if (["CANCELED", "ERROR", "ABANDONED"].includes(st.state || "")) {
          pararPollMaquininha();
          setMaqModal({ fase: "erro", intentId, erro: `Cobrança ${st.state?.toLowerCase()} na maquininha.` });
        }
      } catch {
        // Erro de rede no poll: para e oferece manual (não trava a venda).
        pararPollMaquininha();
        setMaqModal({ fase: "erro", intentId, erro: "Sem conexão com a maquininha. Use o cartão manual." });
      }
    }, 2500);
  }

  async function cancelarCobrancaMaq() {
    pararPollMaquininha();
    const id = maqModal?.intentId;
    setMaqModal(null);
    if (id) {
      try { await cancelarCobrancaMaquininha(id); } catch { /* já pode ter encerrado */ }
    }
  }

  // Fallback: registra a venda como cartão manual (caixa passou no aparelho).
  async function registrarCartaoManual() {
    pararPollMaquininha();
    setMaqModal(null);
    await confirmarVenda("Cartão manual (sem cobrança integrada)");
  }

  async function confirmarVenda(obsExtra?: string) {
    setLoading(true);
    setMsg(null);
    if (pagamento === "fiado" && !clienteFiado) {
      setMsg({ tipo: "erro", texto: "Selecione um cliente para venda fiada." });
      setLoading(false);
      return;
    }
    try {
      const resp = await checkout({
        itens: carrinho.map((i) => ({ produto_id: i.id, quantidade: i.qtd })),
        desconto,
        forma_pagamento: pagamento,
        observacao: obsExtra,
        cliente_id: pagamento === "fiado" ? Number(clienteFiado) : undefined,
        emitir_nota: emitirNota,
        cpf_consumidor: emitirNota ? cpfConsumidor : undefined,
      });
      // Monta o recibo antes de limpar o carrinho.
      const recibo: ReciboData = {
        loja: lojaInfo,
        itens: (resp.itens || []).map((i) => {
          const produto = carrinho.find((p) => p.id === i.produto_id);
          return {
            nome: i.nome_produto, qtd: i.quantidade, preco: i.preco_unitario,
            subtotal: i.subtotal, unidade: produto?.unidade,
          };
        }),
        subtotal,
        desconto,
        total,
        forma: pagamento,
        vendaId: resp.venda?.id,
        data: resp.venda?.criado_em,
        nota: resp.nota && resp.nota.status === "autorizada" ? {
          numero: resp.nota.numero, serie: resp.nota.serie, chave: resp.nota.chave,
          protocolo: resp.nota.protocolo, qrcode_base64: resp.nota.qrcode_base64,
        } : null,
      };
      setUltimaVenda(recibo);
      if (imprimirAuto) imprimirRecibo(recibo, largura);

      setMsg({ tipo: "ok", texto: `Venda finalizada! Total: R$ ${total.toFixed(2)}${emitirNota ? " (Nota emitida)" : ""}` });
      setCarrinho([]);
      setDesconto(0);
      setPagamento("dinheiro");
      setClienteFiado("");
      setEmitirNota(false);
      setCpfConsumidor("");
      setPixModal(null);
      carregar();
    } catch (err: unknown) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setLoading(false);
    }
  }

  const itensCarrinho = carrinho.length;

  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-full">
      {/* Coluna esquerda: Produtos */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Busca */}
        <div className="relative mb-6">
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-500">
            <Search size={18} />
          </div>
          <input
            ref={buscaRef}
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            onKeyDown={onBuscaKeyDown}
            placeholder="Bipe o código de barras ou busque por nome  ·  Enter adiciona"
            className="w-full pl-12 pr-4 py-4 bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all text-sm shadow-xl"
            autoFocus
          />
          <span className="absolute inset-y-0 right-4 hidden md:flex items-center pointer-events-none text-[10px] font-bold text-slate-600 uppercase tracking-wider">F2 finaliza</span>
        </div>

        {/* Grade de produtos */}
        <div className="flex-1 overflow-y-auto rounded-2xl bg-slate-900/30 backdrop-blur-sm border border-slate-800/50 p-4">
          {filtrados.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <Mascote estado="pensando" frase={busca ? "Não encontrei nada..." : "Cadastre alguns produtos!"} />
              <p className="text-slate-500 text-sm mt-4">
                {busca ? "Nenhum produto corresponde à sua busca." : "Sua vitrine está vazia."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-3">
              <AnimatePresence mode="popLayout">
                {filtrados.map((p) => {
                  const preco = p.preco_venda || p.preco_custo;
                  const baixo = p.estoque <= p.estoque_minimo;
                  return (
                    <motion.button
                      layout
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      whileHover={{ y: -4, scale: 1.02 }}
                      whileTap={{ scale: 0.95 }}
                      key={p.id}
                      onClick={() => addAoCarrinho(p)}
                      className="group text-left bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 hover:border-brand-500/50 rounded-2xl p-4 transition-all shadow-lg hover:shadow-brand-500/5 flex flex-col h-full"
                    >
                      <div className="flex-1">
                        <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-1">{p.categoria_nome || "Geral"}</p>
                        <p className="text-white text-sm font-bold leading-snug line-clamp-2">{p.nome}</p>
                      </div>
                      <div className="mt-4">
                        <p className="text-brand-400 font-black text-lg">R$ {preco.toFixed(2)}</p>
                        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold mt-2 ${baixo ? "bg-amber-500/10 text-amber-500" : "bg-slate-700/30 text-slate-500"}`}>
                          {baixo && <AlertCircle size={10} />}
                          {fmtQtd(p.estoque)} {p.unidade}
                        </div>
                      </div>
                    </motion.button>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Coluna direita: Carrinho + Checkout */}
      <div className="w-full lg:w-[400px] flex flex-col bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-5 shadow-2xl shrink-0 relative overflow-hidden">
        {/* Decorative glow */}
        <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-brand-600/10 blur-[80px] rounded-full pointer-events-none" />

        <div className="flex items-center justify-between mb-6 relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-600/20 flex items-center justify-center text-brand-400">
              <ShoppingCart size={20} />
            </div>
            <h2 className="text-white font-black text-lg tracking-tight">CARRINHO</h2>
          </div>
          {itensCarrinho > 0 && (
            <span className="px-3 py-1 rounded-full bg-brand-600 text-white text-[10px] font-black uppercase shadow-lg shadow-brand-600/20">
              {itensCarrinho} {itensCarrinho === 1 ? "Item" : "Itens"}
            </span>
          )}
        </div>

        {carrinho.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-12 relative z-10">
            <Mascote estado="normal" frase="Estou esperando!" />
            <p className="text-slate-500 text-sm mt-4 text-center">
              Adicione produtos para<br />começar a vender.
            </p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col relative z-10">
            {/* Itens */}
            <div className="flex-1 overflow-y-auto space-y-3 mb-6 pr-1 custom-scrollbar max-h-[40dvh] lg:max-h-none">
              <AnimatePresence initial={false}>
                {carrinho.map((i) => {
                  const preco = i.preco_venda || i.preco_custo;
                  const sub = i.qtd * preco;
                  return (
                    <motion.div
                      layout
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      key={i.id}
                      className="flex items-center gap-3 bg-slate-800/50 border border-slate-700/30 rounded-2xl p-3 group"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm font-bold truncate">{i.nome}</p>
                        <p className="text-slate-500 text-[10px] font-bold uppercase tracking-wider mt-0.5">R$ {preco.toFixed(2)} / {i.unidade}</p>
                      </div>
                      <div className="flex items-center gap-2 bg-slate-900/50 rounded-xl p-1 border border-slate-700/50">
                        <button
                          onClick={() => alterarQtd(i.id, -passoQtd(i.unidade))}
                          className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                        >
                          <Minus size={14} />
                        </button>
                        <input
                          type="number"
                          value={i.qtd}
                          onChange={(e) => definirQtd(i.id, Number(e.target.value))}
                          min={passoQtd(i.unidade)}
                          max={i.estoque}
                          step={passoQtd(i.unidade)}
                          className="w-14 bg-transparent text-white text-xs font-bold text-center focus:outline-none"
                        />
                        <button
                          onClick={() => alterarQtd(i.id, passoQtd(i.unidade))}
                          className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                      <div className="text-right w-20">
                        <p className="text-brand-400 font-black text-sm">R$ {sub.toFixed(2)}</p>
                        <button
                          onClick={() => removerDoCarrinho(i.id)}
                          className="text-slate-600 hover:text-red-400 transition-colors mt-1"
                        >
                          <Trash2 size={14} className="ml-auto" />
                        </button>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Totais */}
            <div className="bg-slate-800/30 rounded-2xl p-4 border border-slate-700/30 space-y-3 mb-6">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-slate-500">Subtotal</span>
                <span className="text-white text-sm">R$ {subtotal.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-slate-500">Desconto</span>
                <div className="relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500">R$</span>
                  <input
                    type="number"
                    value={desconto || ""}
                    onChange={(e) => setDesconto(Number(e.target.value) || 0)}
                    placeholder="0.00"
                    className="w-24 bg-slate-900/50 border border-slate-700/50 rounded-lg pl-7 pr-2 py-1.5 text-brand-400 text-right text-xs font-bold focus:outline-none focus:border-brand-500 transition-all"
                  />
                </div>
              </div>
              <div className="pt-3 border-t border-slate-700/50 flex justify-between items-end">
                <span className="text-slate-400 text-xs font-black uppercase tracking-widest">Total a Pagar</span>
                <span className="text-white font-black text-2xl tracking-tighter">
                  <span className="text-brand-400 text-sm mr-1">R$</span>
                  {total.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Pagamento */}
            <div className="mb-6">
              <label className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-3 block">Forma de Pagamento</label>
              <div className="grid grid-cols-5 gap-2">
                {PAGAMENTOS.map((fp) => (
                  <motion.button
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    key={fp.value}
                    onClick={() => { setPagamento(fp.value); if (fp.value !== "fiado") setClienteFiado(""); }}
                    className={`flex flex-col items-center justify-center py-3 rounded-xl transition-all border ${
                      pagamento === fp.value
                        ? "bg-brand-600 border-brand-500 text-white shadow-lg shadow-brand-600/20"
                        : "bg-slate-800/40 border-slate-700/50 text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    <span className="mb-1">{fp.icon}</span>
                    <span className="text-[9px] font-black uppercase tracking-tighter leading-none">{fp.label}</span>
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Select de cliente para venda fiada */}
            {pagamento === "fiado" && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6"
              >
                <label className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-2 block">Selecionar Cliente</label>
                <select
                  value={clienteFiado}
                  onChange={(e) => setClienteFiado(e.target.value ? Number(e.target.value) : "")}
                  className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl text-white text-sm font-bold focus:outline-none focus:border-brand-500 appearance-none shadow-inner"
                >
                  <option value="">Selecione um cliente...</option>
                  {clientes.map((cl) => (
                    <option key={cl.id} value={cl.id}>{cl.nome}</option>
                  ))}
                </select>
                {clientes.length === 0 && (
                  <p className="text-amber-500 text-[10px] font-bold mt-2 flex items-center gap-1">
                    <AlertCircle size={10} /> Cadastre clientes na aba lateral primeiro.
                  </p>
                )}
              </motion.div>
            )}

            {/* Botão finalizar */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input 
                  type="checkbox" 
                  checked={emitirNota} 
                  onChange={(e) => setEmitirNota(e.target.checked)}
                  className="w-4 h-4 rounded accent-brand-500 bg-slate-800 border-slate-700" 
                />
                <span className="text-slate-400 text-xs font-bold group-hover:text-slate-300 transition-colors">Emitir NFC-e (Cupom Fiscal)</span>
              </label>

              {emitirNota && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="overflow-hidden">
                  <input
                    type="text"
                    value={cpfConsumidor}
                    onChange={(e) => setCpfConsumidor(e.target.value)}
                    placeholder="CPF/CNPJ do Consumidor (opcional)"
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-xs focus:outline-none focus:border-brand-500"
                  />
                </motion.div>
              )}

              {/* Recibo (impressora térmica) */}
              <div className="flex items-center justify-between gap-2 mb-3 text-xs">
                <label className="flex items-center gap-2 text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={imprimirAuto}
                    onChange={(e) => { setImprimirAuto(e.target.checked); localStorage.setItem("recibo_auto", e.target.checked ? "1" : "0"); }}
                    className="w-4 h-4 accent-brand-500"
                  />
                  🖨️ Imprimir recibo ao finalizar
                </label>
                <select
                  value={largura}
                  onChange={(e) => { const v = Number(e.target.value) as 58 | 80; setLargura(v); setLarguraRecibo(v); }}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-300"
                  title="Largura do papel da impressora térmica"
                >
                  <option value={80}>80mm</option>
                  <option value={58}>58mm</option>
                </select>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={finalizarVenda}
                disabled={loading || pixLoading || !!maqModal || carrinho.length === 0}
                className={`w-full py-4 rounded-2xl text-white font-black text-lg tracking-tight shadow-xl transition-all flex items-center justify-center gap-3 ${
                  loading || pixLoading || !!maqModal || carrinho.length === 0
                    ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                    : "bg-gradient-to-r from-emerald-600 to-teal-600 shadow-emerald-900/20"
                }`}
              >
                {loading ? (
                  <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <CheckCircle2 size={22} />
                    <span>FINALIZAR VENDA</span>
                  </>
                )}
              </motion.button>
            </div>
          </div>
        )}

        {/* Mensagem de feedback */}
        <AnimatePresence>
          {msg && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`mt-6 p-4 rounded-2xl flex items-start gap-3 relative z-10 ${
                msg.tipo === "ok"
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border border-red-500/30 text-red-400"
              }`}
            >
              {msg.tipo === "ok" ? <CheckCircle2 size={18} className="shrink-0" /> : <AlertCircle size={18} className="shrink-0" />}
              <div className="flex-1">
                <p className="text-xs font-bold leading-tight">{msg.texto}</p>
                {msg.tipo === "ok" && ultimaVenda && (
                  <button
                    onClick={() => imprimirRecibo(ultimaVenda, largura)}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-bold px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 transition-colors"
                  >
                    🖨️ Imprimir recibo
                  </button>
                )}
              </div>
              <button onClick={() => setMsg(null)} className="text-slate-500 hover:text-white transition-colors">
                <X size={14} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mini resumo */}
        {dash && (
          <div className="mt-auto pt-6 border-t border-slate-800/50 flex justify-between items-center relative z-10">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">
              Vendas Hoje
            </div>
            <div className="text-right">
              <p className="text-white font-bold text-sm">R$ {(dash.vendas_hoje_total || 0).toFixed(2)}</p>
              <p className="text-brand-400 text-[10px] font-bold uppercase tracking-tighter">{dash.vendas_hoje_qtd} vendas</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Modal PIX QR Code ── */}
      <AnimatePresence>
        {pixModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-[#020617]/90 backdrop-blur-sm"
              onClick={cancelarPix}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-sm bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl text-center overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand-500 to-emerald-500" />
              
              <div className="flex items-center justify-between mb-6">
                <div className="w-10 h-10 rounded-xl bg-brand-600/10 flex items-center justify-center text-brand-400">
                  <Smartphone size={20} />
                </div>
                <h2 className="text-white font-black text-xl tracking-tight">PAGAMENTO PIX</h2>
                <button onClick={cancelarPix} className="w-10 h-10 rounded-xl hover:bg-slate-800 flex items-center justify-center text-slate-500 transition-colors">
                  <X size={20} />
                </button>
              </div>

              <p className="text-slate-400 text-sm mb-6">
                Escaneie o QR Code abaixo para pagar
              </p>

              <div className="bg-white rounded-2xl p-4 mb-6 inline-block shadow-inner mx-auto">
                <img
                  src={`data:image/png;base64,${pixModal.qr_base64}`}
                  alt="QR Code PIX"
                  className="w-48 h-48 mx-auto"
                />
              </div>

              <div className="mb-6">
                <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total a Pagar</p>
                <p className="text-brand-400 font-black text-3xl tracking-tighter">
                  <span className="text-lg mr-1">R$</span>
                  {total.toFixed(2)}
                </p>
              </div>

              <div className="bg-slate-800/50 rounded-2xl p-4 mb-8 border border-slate-700/50">
                <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-3 text-left">Código Pix Copia e Cola</p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    readOnly
                    value={pixModal.payload}
                    className="flex-1 bg-slate-950/50 text-white text-xs font-mono rounded-lg px-3 py-2 border border-slate-800 truncate"
                    onClick={(e) => (e.target as HTMLInputElement).select()}
                  />
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(pixModal.payload);
                      setMsg({ tipo: "ok", texto: "Código PIX copiado!" });
                    }}
                    className="px-4 bg-brand-600 hover:bg-brand-500 text-white text-xs font-black uppercase rounded-lg transition-all active:scale-95"
                  >
                    COPIAR
                  </button>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={cancelarPix}
                  className="flex-1 px-4 py-4 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-2xl text-sm font-black uppercase tracking-widest transition-all"
                >
                  VOLTAR
                </button>
                <button
                  onClick={() => confirmarVenda()}
                  disabled={loading}
                  className="flex-1 px-4 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl text-sm font-black uppercase tracking-widest transition-all shadow-lg shadow-emerald-900/20"
                >
                  {loading ? "..." : "CONFIRMAR ✅"}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── Modal Maquininha (Mercado Pago Point) ── */}
      <AnimatePresence>
        {maqModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-[#020617]/90 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-sm bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl text-center overflow-hidden"
            >
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-brand-500 to-emerald-500" />

              <div className="flex items-center justify-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-xl bg-brand-600/10 flex items-center justify-center text-brand-400">
                  <CreditCard size={20} />
                </div>
                <h2 className="text-white font-black text-xl tracking-tight">MAQUININHA</h2>
              </div>

              <div className="mb-6">
                <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total a Cobrar</p>
                <p className="text-brand-400 font-black text-3xl tracking-tighter">
                  <span className="text-lg mr-1">R$</span>{total.toFixed(2)}
                </p>
              </div>

              {maqModal.fase !== "erro" ? (
                <>
                  <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                  <p className="text-white text-sm font-bold mb-1">
                    {maqModal.fase === "criando"
                      ? "Acionando a maquininha..."
                      : pagamento === "pix"
                        ? "Cliente paga o PIX na maquininha"
                        : "Peça o cartão ao cliente"}
                  </p>
                  <p className="text-slate-500 text-xs mb-8">
                    {ESTADO_MAQ[maqModal.estado || ""] || "Aguardando a maquininha..."}
                  </p>
                  <button
                    onClick={cancelarCobrancaMaq}
                    className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl text-sm font-black uppercase tracking-widest transition-all"
                  >
                    CANCELAR
                  </button>
                </>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-400 grid place-items-center mx-auto mb-4">
                    <AlertCircle size={24} />
                  </div>
                  <p className="text-red-400 text-sm font-bold mb-6">{maqModal.erro}</p>
                  <div className="flex flex-col gap-3">
                    <button
                      onClick={registrarCartaoManual}
                      disabled={loading}
                      className="w-full px-4 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl text-sm font-black uppercase tracking-widest transition-all shadow-lg shadow-emerald-900/20"
                    >
                      {loading ? "..." : "REGISTRAR CARTÃO MANUAL"}
                    </button>
                    <button
                      onClick={cancelarCobrancaMaq}
                      className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-2xl text-sm font-black uppercase tracking-widest transition-all"
                    >
                      FECHAR
                    </button>
                  </div>
                  <p className="text-slate-500 text-[11px] mt-4 leading-snug">
                    "Cartão manual" = você passou o cartão direto no aparelho; o sistema só registra a venda.
                  </p>
                </>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

