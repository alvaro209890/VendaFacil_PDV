import { useState, useEffect, useLayoutEffect, useCallback, useRef } from "react";
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
  cancelarCobrancaMaquininha, getConfigFiscal, getAtivacaoStatus,
  criarCobrancaPixMp, consultarCobrancaPixMp, confirmarVendaPixMp, getPixMpStatus,
} from "../lib/api";
import type { Produto, DashboardData, PixQrCodeResponse, Cliente, PagamentoEletronico, PixMpCobranca, ParcelaVenda } from "../lib/api";
import { imprimirRecibo, getLarguraRecibo, setLarguraRecibo } from "../lib/recibo";
import type { ReciboData } from "../lib/recibo";
import Mascote from "../components/Mascote";
import { useAuthStore } from "../store/authStore";
import { itemCarrinho, linhaCarrinho, limiteCarrinho, unidadeCarrinho, lerCarrinho, salvarCarrinho, faltaParaVender, pareceCodigo } from "../lib/carrinho";
import JanelaProdutoModal from "../components/JanelaProduto";
import type { JanelaProduto } from "../components/JanelaProduto";
import type { CartItem } from "../lib/carrinho";
import { lerNumeroPtBr as decimalDigitado, moeda, decimal2 } from "../lib/numeros";

const PAGAMENTOS = [
  { value: "dinheiro", label: "Dinheiro", icon: <Banknote size={18} /> },
  { value: "pix", label: "PIX", icon: <Smartphone size={18} /> },
  { value: "debito", label: "Débito", icon: <CreditCard size={18} /> },
  { value: "credito", label: "Crédito", icon: <CreditCard size={18} /> },
  { value: "fiado", label: "Fiado", icon: <FileText size={18} /> },
] as const;

type FormaDividida = ParcelaVenda["forma"];
type LinhaPagamento = { forma: FormaDividida; valor: string };
type PlanoDividido = {
  parcelas: ParcelaVenda[];
  meios: ("point" | "pix_mp" | "pix_manual" | null)[];
  proxima: number;
  referencia: string;
  tentativa: number;
};

// Estados da cobrança Point → texto amigável exibido no modal.
const ESTADO_MAQ: Record<string, string> = {
  OPEN: "Enviando para a maquininha...",
  ON_TERMINAL: "Aguardando o pagamento na maquininha...",
  PROCESSING: "Processando o pagamento...",
  FINISHED: "Pagamento aprovado!",
};
const TIMEOUT_POINT_MS = 45_000;
const ERRO_POINT_NAO_PUXOU =
  "A cobrança foi criada no Mercado Pago, mas a Point não puxou para a tela. Reinicie a maquininha, pressione Atualizar/botão verde nela e tente novamente.";

const fmtQtd = (v: number) => Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 3 });
const passoQtd = (unidade?: string) => ["KG", "G", "LT", "ML"].includes((unidade || "").toUpperCase()) ? 0.1 : 1;
const parseMoeda = (v: string) => decimalDigitado(v) ?? 0;


export default function PDV() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  // Todos os ativos, inclusive sem estoque: o código bipado de um produto zerado
  // abre a janela de entrada em vez de "Nada encontrado".
  const [todosProdutos, setTodosProdutos] = useState<Produto[]>([]);
  const [janela, setJanela] = useState<JanelaProduto | null>(null);
  const [janelaSalvando, setJanelaSalvando] = useState(false);
  const [busca, setBusca] = useState("");
  const chaveCarrinho = `vf_carrinho_v1:${useAuthStore((s) => s.user?.id)}`;
  const [carrinho, setCarrinho] = useState<CartItem[]>(() => lerCarrinho(chaveCarrinho));
  const [descontoTexto, setDescontoTexto] = useState("");
  const [quantidadesTexto, setQuantidadesTexto] = useState<Record<string, string>>({});
  const desconto = decimalDigitado(descontoTexto, 2) ?? 0;
  function setDesconto(valor: number) { setDescontoTexto(valor ? String(valor) : ""); }
  const [pagamento, setPagamento] = useState("dinheiro");
  const [divisao, setDivisao] = useState<LinhaPagamento[] | null>(null);
  const planoDivididoRef = useRef<PlanoDividido | null>(null);
  const checkoutEmCursoRef = useRef(false);
  const [valorRecebido, setValorRecebido] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string; recibo?: ReciboData } | null>(null);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [licencaBloqueada, setLicencaBloqueada] = useState(false);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteFiado, setClienteFiado] = useState<number | "">("");
  const [emitirNota, setEmitirNota] = useState(false);
  // Com o fiscal habilitado em produção, toda venda sai com NFC-e por padrão;
  // o operador ainda pode desmarcar numa venda específica.
  const notaPadraoRef = useRef(false);
  const painelDinheiroRef = useRef<HTMLDivElement>(null);
  const [cpfConsumidor, setCpfConsumidor] = useState("");

  // PIX QR Code state
  const [pixModal, setPixModal] = useState<PixQrCodeResponse | null>(null);
  const pixManualConfirmadoRef = useRef(false);
  const [pixLoading, setPixLoading] = useState(false);

  // Recibo (impressora térmica)
  const [lojaInfo, setLojaInfo] = useState<{ nome: string; razao?: string; cnpj?: string; endereco?: string }>({ nome: "VendaFácil PDV" });
  // Sempre começa marcado ao abrir o PDV; desmarcar vale só até recarregar a tela.
  const [imprimirAuto, setImprimirAuto] = useState(true);
  const [largura, setLargura] = useState<58 | 80>(getLarguraRecibo());

  // Maquininha (Mercado Pago Point) — cobrança integrada, só quando online.
  const [maqHabilitada, setMaqHabilitada] = useState(false);
  const [maqDeviceOk, setMaqDeviceOk] = useState(false);
  const [maqPixIntegrado, setMaqPixIntegrado] = useState(false);
  // PIX automático pelo Mercado Pago: QR dinâmico + confirmação sozinha (sem clique).
  const [pixMp, setPixMp] = useState<{
    fase: "aguardando" | "aprovado" | "erro";
    cobranca: PixMpCobranca;
    erro?: string;
  } | null>(null);
  const [pixMpProcessando, setPixMpProcessando] = useState(false);
  const pixMpPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pixMpFechandoRef = useRef(false);
  const pixDivididoRef = useRef<((id: string) => void) | null>(null);
  // Fotografia do carrinho no momento em que o QR foi gerado: é com ela que a venda
  // fecha quando o pagamento chega, mesmo que o operador mexa na tela.
  const pixMpSnapshotRef = useRef<{
    itens: { produto_id: number; quantidade: number; modo_venda?: "embalagem" | "unidade" }[];
    desconto: number;
    total: number;
    subtotal: number;
    recebido: number;
    troco: number;
    clienteFiado: number | "";
    emitirNota: boolean;
    cpf: string;
  } | null>(null);
  const [maqModal, setMaqModal] = useState<{
    fase: "criando" | "aguardando" | "erro";
    intentId?: string;
    estado?: string;
    erro?: string;
    forma?: string;
    valor?: number;
  } | null>(null);
  const maqPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const maqTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Guarda o intentId ativo para cancelar no MP se o componente for desmontado.
  const maqIntentIdRef = useRef<string | null>(null);
  // Vínculo do pagamento eletrônico da última cobrança aprovada (p/ a NFC-e).
  const maqPagamentoRef = useRef<PagamentoEletronico | null>(null);
  const carrinhoBloqueado = loading || pixLoading || !!maqModal || !!pixModal ||
    !!maqPagamentoRef.current || !!pixMp || !!planoDivididoRef.current;

  // PIX automático disponível? (token do Mercado Pago + chave PIX da loja)
  const [pixMpPronto, setPixMpPronto] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [p, d, c] = await Promise.all([listarProdutos(true), getDashboard(), listarClientes()]);
      setTodosProdutos(p.produtos);
      setProdutos(p.produtos.filter((x) => x.estoque > 0));
      // Reabre o rascunho com preço/estoque atuais; o backend segue validando o checkout.
      setCarrinho((anterior) => anterior.map((item) => {
        const atual = p.produtos.find((produto) => produto.id === item.id);
        return atual ? itemCarrinho(atual, item.modo_venda, item.qtd) : item;
      }));
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
      setMaqPixIntegrado(!!config.pix_integrado);
    } catch {
      setMaqHabilitada(false);
    }
    // PIX automático (Mercado Pago) — separado também, para não travar o PDV.
    try {
      const pixStatus = await getPixMpStatus();
      setPixMpPronto(!!pixStatus.configurado);
    } catch {
      setPixMpPronto(false);
    }
    try {
      const licenca = await getAtivacaoStatus();
      setLicencaBloqueada(licenca.ativado && licenca.bloqueado);
    } catch {
      setLicencaBloqueada(false);
    }
    // Cabeçalho do recibo (usa os dados fiscais da loja, se preenchidos).
    try {
      const { config } = await getConfigFiscal();
      const padrao = !!config.habilitado && config.ambiente === "producao";
      if (padrao !== notaPadraoRef.current) {
        notaPadraoRef.current = padrao;
        setEmitirNota(padrao);
      }
      const partes = [config.logradouro, config.numero, config.bairro, config.municipio, config.uf]
        .filter(Boolean).join(", ");
      setLojaInfo({
        nome: config.nome_fantasia || config.razao_social || "VendaFácil PDV",
        razao: config.razao_social || undefined,
        cnpj: config.cnpj || undefined,
        endereco: partes || undefined,
      });
    } catch { /* mantém o padrão */ }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  useEffect(() => {
    if (!salvarCarrinho(chaveCarrinho, carrinho)) {
      setMsg({ tipo: "erro", texto: "Não foi possível salvar o rascunho. Não recarregue esta aba antes de finalizar a venda." });
    }
  }, [carrinho, chaveCarrinho]);

  function cancelarVenda() {
    if (loading || maqModal || pixModal) return;
    if (maqPagamentoRef.current || planoDivididoRef.current || pixMp) {
      setMsg({ tipo: "erro", texto: "Há pagamento aprovado. Conclua a venda antes de cancelar o carrinho." });
      return;
    }
    if (!window.confirm("Cancelar esta venda e limpar o carrinho?")) return;
    setCarrinho([]); setQuantidadesTexto({});
    setDesconto(0);
    setValorRecebido("");
    setPagamento("dinheiro");
    setDivisao(null);
    setClienteFiado("");
    setEmitirNota(notaPadraoRef.current);
    setCpfConsumidor("");
    setMsg(null);
    buscaRef.current?.focus();
  }

  const filtrados = busca
    ? produtos.filter(
        (p) =>
          p.nome.toLowerCase().includes(busca.toLowerCase()) ||
          (p.codigo_barras.includes(busca) || p.codigo_barras_unidade?.includes(busca))
      )
    : produtos;

  const buscaRef = useRef<HTMLInputElement>(null);
  const descontoRef = useRef<HTMLInputElement>(null);
  const quantidadeRef = useRef<HTMLInputElement>(null);
  const pagamentoRef = useRef<HTMLButtonElement>(null);
  const modalPagamentoAnterior = useRef(false);
  const modalPagamentoAberto = !!(pixModal || maqModal);

  useLayoutEffect(() => {
    if (modalPagamentoAnterior.current && !modalPagamentoAberto) buscaRef.current?.focus();
    modalPagamentoAnterior.current = modalPagamentoAberto;
  }, [modalPagamentoAberto]);

  function addAoCarrinho(p: Produto, modo: 'embalagem' | 'unidade' = 'unidade'): boolean {
    if (carrinhoBloqueado) return false;
    const novo = itemCarrinho(p, modo);
    if (!(novo.preco_venda > 0)) {
      setMsg({tipo:'erro', texto:`"${p.nome}" está sem preço de venda. Cadastre o preço em Produtos antes de vender.`});
      return false;
    }
    const existe = carrinho.find(i => linhaCarrinho(i) === linhaCarrinho(novo));
    const qtd = (existe?.qtd || 0) + 1;
    if (qtd > limiteCarrinho(novo, carrinho)) {
      setMsg({tipo:'erro',texto:`Estoque insuficiente de "${p.nome}" para ${modo}.`});
      return false;
    }
    setCarrinho(prev => existe ? prev.map(i => linhaCarrinho(i) === linhaCarrinho(novo) ? {...i,qtd} : i) : [...prev,novo]);
    setMsg(null); buscaRef.current?.focus();
    return true;
  }

  /** Vende 1 ou, se faltar estoque/preço, abre a janela para resolver ali mesmo. */
  function venderOuCompletar(p: Produto, modo: 'embalagem' | 'unidade' = 'unidade') {
    if (carrinhoBloqueado) return;
    const falta = faltaParaVender(p, modo, carrinho);
    if (falta.semPreco || falta.semEstoque) {
      setMsg(null);
      setJanela({ tipo: 'completar', produto: p, modo, ...falta });
      return;
    }
    addAoCarrinho(p, modo);
  }

  function fecharJanela() {
    if (janelaSalvando) return;
    setJanela(null);
    buscaRef.current?.focus();
  }

  function produtoPronto(p: Produto, modo: 'embalagem' | 'unidade', criado: boolean) {
    setTodosProdutos(prev => [...prev.filter(x => x.id !== p.id), p]);
    setProdutos(prev => {
      const resto = prev.filter(x => x.id !== p.id);
      return p.estoque > 0 ? [...resto, p] : resto;
    });
    // Linhas já no carrinho passam a enxergar o estoque/preço novos.
    setCarrinho(prev => prev.map(i => i.id === p.id ? itemCarrinho(p, i.modo_venda, i.qtd) : i));
    setJanela(null);
    if (addAoCarrinho(p, modo)) setMsg({ tipo: 'ok', texto: `"${p.nome}" ${criado ? 'cadastrado' : 'atualizado'} e adicionado à venda.` });
  }

  // Leitor de código de barras / Enter: bipa → adiciona → limpa → mantém o foco.
  function onBuscaKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (carrinhoBloqueado || janela) return;
    if (e.key === "Escape") {
      setBusca("");
      return;
    }
    if (e.key !== "Enter") return;
    e.preventDefault();
    const termo = e.currentTarget.value.trim();
    if (!termo) return;
    const exato = todosProdutos.find((p) => (p.codigo_barras && p.codigo_barras === termo) || (p.codigo_barras_unidade && p.codigo_barras_unidade === termo));
    const confere = (p: Produto) => p.nome.toLowerCase().includes(termo.toLowerCase()) || p.codigo_barras.includes(termo) || !!p.codigo_barras_unidade?.includes(termo);
    // Código exato (mesmo zerado) > parecido com estoque > parecido sem estoque.
    const alvo = exato || produtos.find(confere) || todosProdutos.find(confere);
    setBusca("");
    if (alvo) {
      // addAoCarrinho devolve o foco à busca; a janela, se abrir, fica com ele.
      venderOuCompletar(alvo, exato?.vende_por_unidade && exato.codigo_barras === termo ? "embalagem" : "unidade");
    } else {
      // Não cadastrado: janela de cadastro rápido, já com o código (ou o nome) digitado.
      setMsg(null);
      setJanela(pareceCodigo(termo) ? { tipo: "cadastrar", codigo: termo, nome: "" } : { tipo: "cadastrar", codigo: "", nome: termo });
    }
  }

  // Instala antes de pintar, sempre com o estado do render atual (como o clique).
  // F2 finaliza, F3 quantidade, F4 busca, F6 desconto, F7 pagamento; Esc fecha modal.
  useLayoutEffect(() => {
    function onKey(e: KeyboardEvent) {
      // Janela de cadastro/entrada aberta: só Esc (fecha); atalhos do caixa esperam.
      if (janela) {
        if (e.key === "Escape") { e.preventDefault(); fecharJanela(); }
        return;
      }
      // Estado atual, inclusive enquanto o PIX está carregando.
      if (e.key === "Escape" && !loading) {
        if (pixModal) {
          e.preventDefault();
          cancelarPix();
        } else if (maqModal && maqModal.fase !== "criando" && !maqPagamentoRef.current) {
          e.preventDefault();
          void cancelarCobrancaMaq();
        }
      } else if (e.key === "F2") {
        e.preventDefault();
        if (carrinho.length > 0 && !loading && !pixLoading && !maqModal && !pixModal) void finalizarVenda();
      } else if (e.key === "F3" && !loading && !pixLoading && !maqModal && !pixModal) {
        e.preventDefault();
        quantidadeRef.current?.focus();
        quantidadeRef.current?.select();
      } else if (e.key === "F7" && !loading && !pixLoading && !maqModal && !pixModal) {
        e.preventDefault();
        pagamentoRef.current?.focus();
      } else if (e.key === "F6" && !loading && !pixLoading && !maqModal && !pixModal) {
        e.preventDefault();
        descontoRef.current?.focus();
        descontoRef.current?.select();
      } else if (e.key === "F4" && !loading && !pixLoading && !maqModal && !pixModal) {
        e.preventDefault();
        buscaRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  function limparTextoQuantidade(id: string) {
    setQuantidadesTexto((prev) => { const novo = { ...prev }; delete novo[id]; return novo; });
  }

  function quantidadeDigitadaValida(id: string, estoque: number) {
    const item = carrinho.find(i => linhaCarrinho(i) === id);
    const qtd = quantidadesTexto[id] === undefined ? item?.qtd : decimalDigitado(quantidadesTexto[id], 3);
    if (item?.vende_por_unidade && !Number.isInteger(qtd)) return false;
    if (quantidadesTexto[id] === undefined) return !!qtd && qtd <= estoque;
    const numero = decimalDigitado(quantidadesTexto[id], 3);
    return numero !== null && numero > 0 && numero <= estoque;
  }

  function confirmarQuantidade(id: string, estoque: number) {
    if (!quantidadeDigitadaValida(id, estoque)) {
      setMsg({ tipo: "erro", texto: "Corrija a quantidade: maior que zero, até o estoque e com até 3 casas decimais." });
      return false;
    }
    limparTextoQuantidade(id);
    return true;
  }

  function removerDoCarrinho(id: string) {
    if (carrinhoBloqueado) return;
    limparTextoQuantidade(id);
    setCarrinho((prev) => prev.filter((i) => linhaCarrinho(i) !== id));
    if (!carrinho.some((i) => linhaCarrinho(i) !== id)) {
      setDesconto(0);
      setValorRecebido("");
      setPagamento("dinheiro");
      setDivisao(null);
      setClienteFiado("");
      setEmitirNota(notaPadraoRef.current);
      setCpfConsumidor("");
    }
    setMsg(null);
    setBusca("");
    buscaRef.current?.focus();
  }

  function alterarQtd(id: string, delta: number) {
    if (carrinhoBloqueado) return;
    const item = carrinho.find((i) => linhaCarrinho(i) === id);
    if (!item) return;
    if (Number((item.qtd + delta).toFixed(3)) <= 0) {
      removerDoCarrinho(id);
      return;
    }
    limparTextoQuantidade(id);
    setCarrinho((prev) =>
      prev.map((i) => {
        if (linhaCarrinho(i) !== id) return i;
        const nova = Number((i.qtd + delta).toFixed(3));
        if (nova <= 0 || nova > limiteCarrinho(i, prev)) return i;
        return { ...i, qtd: nova };
      })
    );
    buscaRef.current?.focus();
  }

  function definirQtd(id: string, valor: number) {
    if (carrinhoBloqueado) return;
    setCarrinho((prev) =>
      prev.map((i) => {
        if (linhaCarrinho(i) !== id) return i;
        const nova = Number((valor || 0).toFixed(3));
        if (nova <= 0) return { ...i, qtd: 0.001 };
        return { ...i, qtd: Math.min(nova, limiteCarrinho(i, prev)) };
      })
    );
  }

  const centavos = (valor: number) => Math.round((valor + Number.EPSILON) * 100);
  const subtotalCentavos = carrinho.reduce((s, i) => s + centavos(i.qtd * (i.preco_venda || i.preco_custo)), 0);
  const subtotal = subtotalCentavos / 100;
  const totalCentavos = Math.max(0, subtotalCentavos - centavos(desconto));
  const total = totalCentavos / 100;
  const parcelas = divisao?.map(p => ({ forma: p.forma, valor: decimalDigitado(p.valor, 2) ?? 0 }));
  const faltaParcelas = totalCentavos - (parcelas?.reduce((s, p) => s + centavos(p.valor), 0) ?? totalCentavos);
  const divisaoOk = !parcelas || (parcelas.length >= 2 && faltaParcelas === 0 && parcelas.every(p => p.valor > 0));
  const usaDinheiro = parcelas ? parcelas.some(p => p.forma === "dinheiro") : pagamento === "dinheiro";
  const usaFiado = parcelas ? parcelas.some(p => p.forma === "fiado") : pagamento === "fiado";
  const parteDinheiro = parcelas
    ? parcelas.reduce((s, p) => s + (p.forma === "dinheiro" ? centavos(p.valor) : 0), 0) / 100
    : total;
  const recebidoDinheiro = parseMoeda(valorRecebido);
  const trocoDinheiro = Math.max(0, centavos(recebidoDinheiro) - centavos(parteDinheiro)) / 100;
  const faltaDinheiro = Math.max(0, centavos(parteDinheiro) - centavos(recebidoDinheiro)) / 100;
  const dinheiroOk = !usaDinheiro || (parteDinheiro > 0 && faltaDinheiro === 0);

  async function gerarPix(valor = total) {
    if (carrinho.length === 0 || valor <= 0) return;
    setPixLoading(true);
    setMsg(null);
    pixManualConfirmadoRef.current = false;
    try {
      const pix = await gerarPixQrCode(valor);
      setPixModal(pix);
    } catch (err: unknown) {
      if (planoDivididoRef.current) {
        setPixModal({ payload: "", qr_base64: "" });
      } else {
        setMsg({ tipo: "erro", texto: (err as Error).message });
      }
    } finally {
      setPixLoading(false);
    }
  }

  // ── PIX automático (Mercado Pago) ──

  function pararPollPixMp() {
    if (pixMpPollRef.current) {
      clearInterval(pixMpPollRef.current);
      pixMpPollRef.current = null;
    }
  }

  /** Fecha a venda a partir da fotografia do carrinho — rodado quando o MP aprova. */
  const fecharVendaPixMp = useCallback(async (cobranca: PixMpCobranca) => {
    const concluirParcela = pixDivididoRef.current;
    if (concluirParcela) {
      pixDivididoRef.current = null;
      pararPollPixMp();
      setPixMp(null);
      concluirParcela(cobranca.id);
      return;
    }
    const snap = pixMpSnapshotRef.current;
    if (!snap || pixMpFechandoRef.current) return;
    pixMpFechandoRef.current = true;
    pararPollPixMp();
    setPixMp({ fase: "aprovado", cobranca });
    setPixMpProcessando(true);
    setLoading(true);
    try {
      const resp = await confirmarVendaPixMp(cobranca.id, {
        itens: snap.itens,
        desconto: snap.desconto,
        observacao: `PIX Mercado Pago ${cobranca.id}`,
        cliente_id: snap.clienteFiado === "" ? undefined : Number(snap.clienteFiado),
        emitir_nota: snap.emitirNota,
        cpf_consumidor: snap.emitirNota ? snap.cpf : undefined,
        valor: snap.total,
      });
      const recibo: ReciboData = {
        loja: lojaInfo,
        itens: (resp.itens || []).map((i) => ({
          nome: i.nome_produto, qtd: i.quantidade, preco: i.preco_unitario,
          subtotal: i.subtotal, unidade: i.unidade_venda,
          codigo: String(i.produto_id),
        })),
        subtotal: snap.subtotal,
        desconto: snap.desconto,
        total: snap.total,
        forma: "pix",
        vendaId: resp.venda?.id,
        data: resp.venda?.criado_em,
        nota: resp.nota && (resp.nota.status === "autorizada" || resp.nota.status === "contingencia") ? {
          numero: resp.nota.numero, serie: resp.nota.serie, chave: resp.nota.chave,
          protocolo: resp.nota.protocolo, qrcode_base64: resp.nota.qrcode_base64,
          status: resp.nota.status, cpf: snap.cpf || undefined,
          xml: resp.nota.xml_autorizado || resp.nota.xml_assinado,
          ambiente: resp.nota.ambiente,
        } : null,
      };
      if (imprimirAuto) imprimirRecibo(recibo, largura, () => buscaRef.current?.focus());
      const statusNota = resp.nota?.status;
      const avisoFiscal = !!resp.erro_nota || (snap.emitirNota && statusNota !== "autorizada");
      const motivoFiscal = resp.erro_nota || resp.nota?.motivo_rejeicao || resp.nota?.mensagem
        || "Retorno fiscal não confirmou a autorização.";
      const resultadoFiscal = avisoFiscal
        ? ` Venda registrada; não repita a venda. NFC-e ${statusNota || "não emitida"}: ${motivoFiscal}`
        : statusNota === "autorizada" ? " (Nota emitida)" : "";
      setMsg({
        tipo: avisoFiscal ? "erro" : "ok",
        texto: `PIX confirmado! Venda ${resp.ja_confirmada ? "já registrada" : "finalizada"} — Total: ${moeda(snap.total)}${resultadoFiscal}`,
        recibo,
      });
      pixMpSnapshotRef.current = null;
      setPixMp(null);
      setPixModal(null);
      setCarrinho([]); setQuantidadesTexto({});
      setDesconto(0);
      setPagamento("dinheiro");
      setDivisao(null);
      setValorRecebido("");
      setClienteFiado("");
      setEmitirNota(notaPadraoRef.current);
      setCpfConsumidor("");
      carregar();
      buscaRef.current?.focus();
    } catch (err: unknown) {
      // Pagamento aprovado mas venda não fechou (ex.: estoque acabou no meio):
      // o QR some e a mensagem diz exatamente o que aconteceu — a cobrança continua
      // registrada no MP, então repetir a cobrança seria cobrar duas vezes.
      setPixMp({ fase: "erro", cobranca, erro: (err as Error).message });
    } finally {
      setPixMpProcessando(false);
      setLoading(false);
      pixMpFechandoRef.current = false;
    }
  }, [lojaInfo, imprimirAuto, largura]);

  async function iniciarPixMp(valor = total, referencia?: string, concluirParcela?: (id: string) => void) {
    if (carrinho.length === 0 || valor <= 0) return;
    setPixLoading(true);
    setMsg(null);
    pixMpFechandoRef.current = false;
    try {
      const cobranca = await criarCobrancaPixMp(valor, `Venda PDV ${moeda(valor)}`, referencia);
      pixDivididoRef.current = concluirParcela ?? null;
      pixMpSnapshotRef.current = {
        itens: carrinho.map((i) => ({ produto_id: i.id, quantidade: i.qtd, modo_venda: i.modo_venda })),
        desconto,
        total,
        subtotal,
        recebido: recebidoDinheiro,
        troco: trocoDinheiro,
        clienteFiado,
        emitirNota,
        cpf: cpfConsumidor,
      };
      setPixMp({ fase: "aguardando", cobranca });
    } catch (err: unknown) {
      setMsg({ tipo: "erro", texto: (err as Error).message });
    } finally {
      setPixLoading(false);
    }
  }

  // Polling do PIX: a cada 4 s pergunta ao backend (que pergunta ao MP). Quando o
  // pagamento é aprovado, fecha a venda sozinho — o caixa não toca em nada.
  useEffect(() => {
    if (!pixMp || pixMp.fase !== "aguardando") {
      pararPollPixMp();
      return;
    }
    const id = pixMp.cobranca.id;
    let vivo = true;
    let consultando = false;
    const consultar = async () => {
      if (!vivo || consultando || pixMpFechandoRef.current) return;
      consultando = true;
      try {
        const atual = await consultarCobrancaPixMp(id);
        if (!vivo) return;
        if (atual.aprovado) {
          vivo = false;
          void fecharVendaPixMp(atual);
          return;
        }
        if (atual.encerrado) {
          vivo = false;
          pararPollPixMp();
          if (pixDivididoRef.current && planoDivididoRef.current) {
            pixDivididoRef.current = null;
            planoDivididoRef.current.tentativa++;
            setPixMp(null);
            setMsg({ tipo: "erro", texto: `PIX ${atual.status}. Retome a venda para cobrar essa parcela.` });
            return;
          }
          setPixMp({ fase: "erro", cobranca: atual, erro: `PIX ${atual.status} ${atual.status_detail || ""}`.trim() });
          return;
        }
        setPixMp((prev) => (prev && prev.fase === "aguardando" ? { ...prev, cobranca: atual } : prev));
      } catch {
        // Sem internet momentânea: a próxima rodada tenta de novo.
      } finally {
        consultando = false;
      }
    };
    pixMpPollRef.current = setInterval(consultar, 4000);
    void consultar();
    return () => { vivo = false; pararPollPixMp(); };
  }, [pixMp?.cobranca.id, pixMp?.fase, fecharVendaPixMp]);

  function cancelarPixMp() {
    pararPollPixMp();
    setPixMp(null);
    pixMpSnapshotRef.current = null;
    setMsg(null);
  }

  function cancelarPix() {
    setPixModal(null);
    const plano = planoDivididoRef.current;
    if (plano && !plano.meios.slice(0, plano.proxima).some(Boolean)) planoDivididoRef.current = null;
  }

  // Para o polling da maquininha (se estiver rodando).
  const pararPollMaquininha = useCallback(() => {
    if (maqPollRef.current) {
      clearInterval(maqPollRef.current);
      maqPollRef.current = null;
    }
  }, []);

  const pararTimeoutMaquininha = useCallback(() => {
    if (maqTimeoutRef.current) {
      clearTimeout(maqTimeoutRef.current);
      maqTimeoutRef.current = null;
    }
  }, []);

  // Ao desmontar (navegar para outra tela): para o poll E cancela na maquininha
  // se houver cobrança pendente — evita que o pedido fique aberto no MP.
  useEffect(() => () => {
    pararPollMaquininha();
    pararTimeoutMaquininha();
    const id = maqIntentIdRef.current;
    if (id) {
      cancelarCobrancaMaquininha(id).catch(() => undefined);
      maqIntentIdRef.current = null;
    }
  }, [pararPollMaquininha, pararTimeoutMaquininha]);

  // Cobranca pela maquininha: cartao (credito/debito) sempre que a Point estiver
  // ligada; PIX só quando "PIX integrado" estiver habilitado na config (senão o
  // PIX cai no QR estático do PDV, sem vínculo fiscal).
  const podeCobrarMaquininha = (forma: string) =>
    maqHabilitada && maqDeviceOk && navigator.onLine && (
      forma === "debito" || forma === "credito" || (forma === "pix" && maqPixIntegrado)
    );

  async function avancarPagamentoDividido(plano: PlanoDividido) {
    while (plano.proxima < plano.parcelas.length && !plano.meios[plano.proxima]) plano.proxima++;
    const indice = plano.proxima;
    const parte = plano.parcelas[indice];
    if (!parte) {
      await confirmarVenda();
      return;
    }
    const referencia = `${plano.referencia}-${indice}-${plano.tentativa}`;
    if (plano.meios[indice] === "point") {
      await iniciarCobrancaMaquininha(parte.forma, parte.valor, plano, referencia);
    } else if (plano.meios[indice] === "pix_mp") {
      await iniciarPixMp(parte.valor, referencia, id => concluirParcela(plano, { pix_mp_id: id }));
    } else {
      await gerarPix(parte.valor);
    }
  }

  function concluirParcela(plano: PlanoDividido, dados: Partial<ParcelaVenda> = {}) {
    Object.assign(plano.parcelas[plano.proxima], dados);
    plano.proxima++;
    void avancarPagamentoDividido(plano);
  }

  async function finalizarVenda() {
    if (checkoutEmCursoRef.current || loading || pixLoading || maqModal || pixModal || pixMp) return;
    if (licencaBloqueada) {
      setMsg({ tipo: "erro", texto: "Licença suspensa. Dá para fechar o caixa e exportar, mas não vender." });
      return;
    }
    if (carrinho.length === 0) return;
    if (descontoTexto.trim() && decimalDigitado(descontoTexto, 2) === null) {
      setMsg({ tipo: "erro", texto: "Corrija o desconto: valor não negativo com até 2 casas decimais." });
      return;
    }
    if (carrinho.some((i) => !quantidadeDigitadaValida(linhaCarrinho(i), limiteCarrinho(i, carrinho)))) {
      setMsg({ tipo: "erro", texto: "Corrija a quantidade: maior que zero, até o estoque e com até 3 casas decimais." });
      return;
    }
    if (!divisaoOk) {
      setMsg({ tipo: "erro", texto: "Preencha as parcelas com valores positivos que somem o total da venda." });
      return;
    }
    if (usaFiado && !clienteFiado) {
      setMsg({ tipo: "erro", texto: "Selecione um cliente para lançar o fiado." });
      return;
    }
    if (!dinheiroOk) {
      setMsg({ tipo: "erro", texto: `Informe o dinheiro recebido. Ainda faltam ${moeda(faltaDinheiro)}.` });
      return;
    }
    if (parcelas) {
      const plano = planoDivididoRef.current ?? {
        parcelas,
        meios: parcelas.map(({ forma }) => {
          if (forma === "pix" && pixMpPronto && navigator.onLine) return "pix_mp";
          if (podeCobrarMaquininha(forma)) return "point";
          return forma === "pix" ? "pix_manual" : null;
        }),
        proxima: 0,
        referencia: crypto.randomUUID(),
        tentativa: 0,
      } satisfies PlanoDividido;
      planoDivididoRef.current = plano;
      await avancarPagamentoDividido(plano);
      return;
    }
    if (maqPagamentoRef.current) {
      await confirmarVenda();
      return;
    }
    if (podeCobrarMaquininha(pagamento)) {
      await iniciarCobrancaMaquininha();   // cartao integrado na Point
      return;
    }
    if (pagamento === "pix") {
      // PIX automático (Mercado Pago) fecha a venda sozinho quando o pagamento cai;
      // só cai no QR estático (confirmação manual) se o MP não estiver configurado.
      if (pixMpPronto) {
        await iniciarPixMp();
        return;
      }
      await gerarPix();
      return;
    }
    await confirmarVenda();
  }

  async function iniciarCobrancaMaquininha(forma = pagamento, valor = total,
    plano?: PlanoDividido, referencia: string = crypto.randomUUID()) {
    setMsg(null);
    setMaqModal({ fase: "criando", forma, valor });
    let intentId: string;
    try {
      const anteriores = plano?.parcelas.flatMap(p => p.pagamento?.payment_id ? [p.pagamento.payment_id] : []);
      const r = await criarCobrancaMaquininha(valor, referencia, forma, anteriores);
      intentId = r.payment_intent_id;
    } catch (err) {
      // Falhou ao acionar a máquina (ex.: caiu a internet) → oferece manual.
      setMaqModal({ fase: "erro", forma, valor, erro: (err as Error).message });
      return;
    }
    maqIntentIdRef.current = intentId;
    setMaqModal({ fase: "aguardando", intentId, estado: "OPEN", forma, valor });

    // Poll do status até concluir/cancelar/dar erro.
    pararPollMaquininha();
    pararTimeoutMaquininha();
    if (!plano) maqTimeoutRef.current = setTimeout(() => {
      pararPollMaquininha();
      maqIntentIdRef.current = null;
      void cancelarCobrancaMaquininha(intentId).catch(() => undefined);
      setMaqModal({ fase: "erro", intentId, forma, valor, erro: ERRO_POINT_NAO_PUXOU });
    }, TIMEOUT_POINT_MS);
    maqPollRef.current = setInterval(async () => {
      try {
        const st = await consultarCobrancaMaquininha(intentId);
        if (maqIntentIdRef.current !== intentId) return;
        setMaqModal((m) => (m ? { ...m, estado: st.state, erro: undefined } : m));
        if (st.state && st.state !== "OPEN") {
          pararTimeoutMaquininha();
        }
        if (st.pago && st.payment_status === "approved") {
          pararPollMaquininha();
          pararTimeoutMaquininha();
          maqIntentIdRef.current = null;
          setMaqModal(null);
          if (plano) {
            if (!st.payment_id) {
              setMaqModal({ fase: "erro", forma, valor, erro: "A Point aprovou a cobrança sem identificador. Confira na maquininha." });
              return;
            }
            concluirParcela(plano, { pagamento: { ...st.pagamento_fiscal, payment_id: String(st.payment_id) } });
          } else {
            maqPagamentoRef.current = st.pagamento_fiscal ?? null;
            await confirmarVenda(st.payment_id ? `MP Point: ${st.payment_id}` : undefined);
          }
        } else if (["CANCELED", "ERROR", "ABANDONED"].includes(st.state || "")) {
          pararPollMaquininha();
          pararTimeoutMaquininha();
          maqIntentIdRef.current = null;
          if (plano) plano.tentativa++;
          setMaqModal({ fase: "erro", forma, valor, erro: `Cobrança ${st.state?.toLowerCase()} na maquininha.` });
        }
      } catch {
        // Erro de rede no poll: para e oferece manual (não trava a venda).
        if (maqIntentIdRef.current !== intentId) return;
        if (plano) {
          setMaqModal(m => m && { ...m, erro: "Sem conexão. Aguardando para consultar a mesma cobrança." });
        } else {
          pararPollMaquininha();
          setMaqModal({ fase: "erro", intentId, forma, valor, erro: "Sem conexão com a maquininha. Use o cartão manual." });
        }
      }
    }, 2500);
  }

  async function cancelarCobrancaMaq() {
    const plano = planoDivididoRef.current;
    const ativa = maqIntentIdRef.current;
    if (plano && ativa) {
      try {
        const resp = await cancelarCobrancaMaquininha(ativa);
        if (!resp.cancelado || maqIntentIdRef.current !== ativa) return;
        plano.tentativa++;
      } catch (err: unknown) {
        setMaqModal(m => m && { ...m, erro: (err as Error).message });
        return;
      }
    }
    pararPollMaquininha();
    pararTimeoutMaquininha();
    const id = maqModal?.intentId ?? maqIntentIdRef.current;
    maqIntentIdRef.current = null;
    setMaqModal(null);
    if (id && !plano) {
      try { await cancelarCobrancaMaquininha(id); } catch { /* já pode ter encerrado */ }
    }
  }

  // Fallback: registra a venda como cartão manual (caixa passou no aparelho).
  async function registrarCartaoManual() {
    pararPollMaquininha();
    pararTimeoutMaquininha();
    setMaqModal(null);
    await confirmarVenda("Cartão manual (sem cobrança integrada)");
  }

  async function confirmarVenda(obsExtra?: string) {
    if (checkoutEmCursoRef.current) return;
    const plano = planoDivididoRef.current;
    setLoading(true);
    setMsg(null);
    if (usaFiado && !clienteFiado) {
      setMsg({ tipo: "erro", texto: "Selecione um cliente para venda fiada." });
      setLoading(false);
      return;
    }
    if (!dinheiroOk) {
      setMsg({ tipo: "erro", texto: `Informe o dinheiro recebido. Ainda faltam ${moeda(faltaDinheiro)}.` });
      setLoading(false);
      return;
    }
    const obsPagamento = usaDinheiro
      ? `Dinheiro recebido: ${moeda(recebidoDinheiro)} | Troco: ${moeda(trocoDinheiro)}`
      : "";
    const observacao = [obsExtra, obsPagamento].filter(Boolean).join(" | ");
    checkoutEmCursoRef.current = true;
    try {
      const pagamentoFiscal = maqPagamentoRef.current ?? undefined;
      const resp = await checkout({
        itens: carrinho.map((i) => ({ produto_id: i.id, quantidade: i.qtd, modo_venda: i.modo_venda })),
        desconto,
        forma_pagamento: plano ? undefined : pagamento,
        pagamentos: plano?.parcelas,
        referencia_checkout: plano?.referencia,
        dinheiro_recebido: usaDinheiro ? recebidoDinheiro : undefined,
        observacao,
        cliente_id: usaFiado ? Number(clienteFiado) : undefined,
        emitir_nota: emitirNota,
        cpf_consumidor: emitirNota ? cpfConsumidor : undefined,
        pagamento: pagamentoFiscal,
      });
      // Monta o recibo antes de limpar o carrinho.
      const recibo: ReciboData = {
        loja: lojaInfo,
        itens: (resp.itens || []).map((i) => {
          const produto = carrinho.find((p) => p.id === i.produto_id);
          return {
            nome: i.nome_produto, qtd: i.quantidade, preco: i.preco_unitario,
            subtotal: i.subtotal, unidade: i.unidade_venda || produto?.unidade, codigo: String(i.produto_id),
          };
        }),
        subtotal,
        desconto,
        total,
        forma: resp.venda.forma_pagamento,
        pagamentos: resp.venda.pagamentos,
        recebido: usaDinheiro ? recebidoDinheiro : undefined,
        troco: usaDinheiro ? trocoDinheiro : undefined,
        vendaId: resp.venda?.id,
        data: resp.venda?.criado_em,
        nota: resp.nota && (resp.nota.status === "autorizada" || resp.nota.status === "contingencia") ? {
          numero: resp.nota.numero, serie: resp.nota.serie, chave: resp.nota.chave,
          protocolo: resp.nota.protocolo, qrcode_base64: resp.nota.qrcode_base64,
          status: resp.nota.status, cpf: cpfConsumidor || undefined,
          xml: resp.nota.xml_autorizado || resp.nota.xml_assinado,
          ambiente: resp.nota.ambiente,
        } : null,
      };
      if (imprimirAuto) imprimirRecibo(recibo, largura, () => buscaRef.current?.focus());

      // A venda já foi gravada: falha fiscal não deve incentivar repetir a cobrança.
      const statusNota = resp.nota?.status;
      const avisoFiscal = !!resp.erro_nota || (emitirNota && statusNota !== "autorizada");
      const motivoFiscal = resp.erro_nota || resp.nota?.motivo_rejeicao || resp.nota?.mensagem
        || "Retorno fiscal não confirmou a autorização.";
      const resultadoFiscal = avisoFiscal
        ? ` Venda registrada; não repita a venda. NFC-e ${statusNota || "não emitida"}: ${motivoFiscal}`
        : statusNota === "autorizada" ? " (Nota emitida)" : "";
      setMsg({ tipo: avisoFiscal ? "erro" : "ok", texto: `Venda finalizada! Total: ${moeda(total)}${resultadoFiscal}`, recibo });
      maqPagamentoRef.current = null;
      planoDivididoRef.current = null;
      setDivisao(null);
      setCarrinho([]); setQuantidadesTexto({});
      setDesconto(0);
      setPagamento("dinheiro");
      setValorRecebido("");
      setClienteFiado("");
      setEmitirNota(notaPadraoRef.current);
      setCpfConsumidor("");
      setPixModal(null);
      carregar();
      buscaRef.current?.focus();
    } catch (err: unknown) {
      const sufixo = plano ? " Retome para registrar a mesma venda." : "";
      setMsg({ tipo: "erro", texto: (err as Error).message + sufixo });
    } finally {
      checkoutEmCursoRef.current = false;
      setLoading(false);
    }
  }

  const itensCarrinho = carrinho.length;
  const carrinhoVazio = itensCarrinho === 0;
  const reciboDaVenda = msg?.recibo;
  const finalizarDesabilitado = loading || pixLoading || !!maqModal || !!pixModal || !!pixMp ||
    carrinhoVazio || !divisaoOk || !dinheiroOk;

  function alternarDivisao() {
    if (divisao) {
      setDivisao(null);
      return;
    }
    const forma = pagamento as FormaDividida;
    setValorRecebido("");
    setDivisao([
      { forma, valor: total.toFixed(2).replace(".", ",") },
      { forma: forma === "pix" ? "dinheiro" : "pix", valor: "" },
    ]);
  }

  // Em tela larga o checkout rola por dentro: ao escolher dinheiro, traz o campo
  // "Dinheiro recebido" para a vista (o FINALIZAR só libera com ele preenchido).
  // No celular a página rola inteira e não se mexe sozinha durante a leitura.
  useEffect(() => {
    if (!usaDinheiro || carrinhoVazio || divisao) return;
    if (!window.matchMedia("(min-width: 1024px)").matches) return;
    painelDinheiroRef.current?.scrollIntoView({ block: "nearest" });
  }, [usaDinheiro, carrinhoVazio, divisao]);

  return (
    // Em tela larga a página fica na altura da janela: a grade de produtos rola
    // sozinha e o FINALIZAR VENDA não desce junto quando há muitos produtos.
    <div className="flex flex-col lg:flex-row gap-6 min-h-full lg:h-full lg:min-h-0">
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
        <div data-testid="grade-produtos" className="flex-1 overflow-y-auto rounded-2xl bg-slate-900/30 backdrop-blur-sm border border-slate-800/50 p-4 max-h-[50dvh] lg:max-h-none">
          {filtrados.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <Mascote estado="pensando" frase={busca ? "Não encontrei nada..." : "Cadastre alguns produtos!"} />
              <p className="text-slate-500 text-sm mt-4">
                {busca ? "Nenhum produto corresponde à sua busca." : "Sua vitrine está vazia."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3">
              <AnimatePresence mode="popLayout">
                {filtrados.flatMap((produto) => (produto.vende_por_unidade ? [itemCarrinho(produto, 'embalagem'), itemCarrinho(produto, 'unidade')] : [itemCarrinho(produto)]).map((p) => {
                  const preco = p.preco_venda || p.preco_custo;
                  const baixo = p.estoque <= p.estoque_minimo;
                  return (
                    <motion.button
                      layout
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      whileHover={{ y: -4, scale: 1.02 }}
                      whileTap={{ scale: 0.95 }}
                      key={linhaCarrinho(p)}
                      onClick={() => venderOuCompletar(produto, p.modo_venda)}
                      className="group text-left bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 hover:border-brand-500/50 rounded-2xl p-4 transition-all shadow-lg hover:shadow-brand-500/5 flex flex-col h-full"
                    >
                      <div className="flex-1">
                        <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-1">{p.categoria_nome || "Geral"}</p>
                        <p className="text-white text-sm font-bold leading-snug line-clamp-2">{p.nome}</p>
                      </div>
                      {!!p.vende_por_unidade && <p className="mt-3 text-sm font-bold text-brand-300">{p.modo_venda === 'embalagem' ? `${p.unidade_compra} com ${fmtQtd(p.quantidade_por_embalagem)}` : 'Unidade'}</p>}
                      <div className="mt-4">
                        <p className="text-brand-400 font-black text-lg">{moeda(preco)}</p>
                        {!!p.vende_por_unidade && p.modo_venda === 'embalagem' && p.quantidade_por_embalagem > 0 && <p className="text-slate-400 text-xs">{moeda((preco / p.quantidade_por_embalagem))} cada</p>}
                        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold mt-2 ${baixo ? "bg-amber-500/10 text-amber-500" : "bg-slate-700/30 text-slate-500"}`}>
                          {baixo && <AlertCircle size={10} />}
                          {p.vende_por_unidade && p.modo_venda === 'embalagem' ? `${fmtQtd(Math.floor(p.estoque / (p.quantidade_por_embalagem || 1)))} ${p.unidade_compra} (${fmtQtd(p.estoque)} ${p.unidade})` : `${fmtQtd(p.estoque)} ${p.unidade}`}
                        </div>
                      </div>
                    </motion.button>
                  );
                }))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Coluna direita: Carrinho + Checkout */}
      <div className={`w-full lg:w-[400px] flex flex-col bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-5 shadow-2xl shrink-0 relative overflow-hidden lg:max-h-full lg:min-h-0 ${carrinhoVazio ? "lg:self-start" : ""}`}>
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
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-brand-600 text-white text-[10px] font-black uppercase shadow-lg shadow-brand-600/20">
                {itensCarrinho} {itensCarrinho === 1 ? "Item" : "Itens"}
              </span>
              <button type="button" onClick={cancelarVenda} disabled={loading || !!maqModal || !!pixModal}
                title="Cancelar venda" aria-label="Cancelar venda"
                className="p-2 rounded-lg text-red-400 hover:bg-red-500/10 disabled:opacity-40">
                <Trash2 size={18} />
              </button>
            </div>
          )}
        </div>

        {carrinhoVazio ? (
          <div className="flex flex-col items-center justify-center py-8 relative z-10">
            <Mascote estado="normal" frase="Estou esperando!" />
            <p className="text-slate-500 text-sm mt-4 text-center">
              Adicione produtos para<br />começar a vender.
            </p>
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex flex-col relative z-10">
            {/* Parte rolável: itens, totais, pagamento e opções. O botão fica fixo embaixo. */}
            <div data-testid="checkout-rolavel" className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1">
            {/* Itens */}
            <div className="overflow-y-auto space-y-3 mb-6 pr-1 custom-scrollbar max-h-[40dvh] lg:max-h-[24dvh]">
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
                      key={linhaCarrinho(i)}
                      className="flex flex-wrap items-center gap-3 bg-slate-800/50 border border-slate-700/30 rounded-2xl p-3 group"
                    >
                      <div className="flex-1 min-w-[8rem]">
                        <p className="text-white text-sm font-bold line-clamp-2 break-words" title={i.nome}>{i.nome}</p>
                        {!!i.vende_por_unidade && <span className="text-brand-300 text-xs font-bold">{i.modo_venda === 'embalagem' ? i.unidade_compra : 'AVULSO'}</span>}
                        <p className="text-slate-500 text-[10px] font-bold uppercase tracking-wider mt-0.5">{moeda(preco)} / {unidadeCarrinho(i)}</p>
                      </div>
                      <div className="flex items-center gap-2 bg-slate-900/50 rounded-xl p-1 border border-slate-700/50">
                        <button
                          type="button"
                          data-acao-carrinho
                          aria-label={`Diminuir quantidade de ${i.nome}${i.vende_por_unidade ? ` ${unidadeCarrinho(i)}` : ""}`}
                          title="Diminuir; na última unidade, remove da compra"
                          disabled={carrinhoBloqueado}
                          onClick={() => alterarQtd(linhaCarrinho(i), -passoQtd(unidadeCarrinho(i)))}
                          className="w-9 h-9 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700 transition-colors disabled:opacity-40"
                        >
                          <Minus size={14} />
                        </button>
                        <input
                          type="text"
                          inputMode="decimal"
                          disabled={carrinhoBloqueado}
                          ref={linhaCarrinho(i) === linhaCarrinho(carrinho[carrinho.length - 1]) ? quantidadeRef : undefined}
                          aria-label={`Quantidade de ${i.nome}${i.vende_por_unidade ? ` ${unidadeCarrinho(i)}` : ""}`}
                          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); if (confirmarQuantidade(linhaCarrinho(i), limiteCarrinho(i, carrinho))) buscaRef.current?.focus(); } }}
                          value={quantidadesTexto[linhaCarrinho(i)] ?? String(i.qtd)}
                          onChange={(e) => {
                            const texto = e.target.value;
                            setQuantidadesTexto((prev) => ({ ...prev, [linhaCarrinho(i)]: texto }));
                            const numero = decimalDigitado(texto, 3);
                            if (numero !== null && numero > 0 && numero <= limiteCarrinho(i, carrinho)) definirQtd(linhaCarrinho(i), numero);
                          }}
                          onBlur={(e) => {
                            if (e.relatedTarget instanceof HTMLElement && e.relatedTarget.closest('[data-acao-carrinho]')) return;
                            confirmarQuantidade(linhaCarrinho(i), limiteCarrinho(i, carrinho));
                          }}
                          min={passoQtd(unidadeCarrinho(i))}
                          max={limiteCarrinho(i, carrinho)}
                          step={passoQtd(unidadeCarrinho(i))}
                          className="w-14 bg-transparent text-white text-xs font-bold text-center focus:outline-none"
                        />
                        <button
                          type="button"
                          data-acao-carrinho
                          aria-label={`Aumentar quantidade de ${i.nome}${i.vende_por_unidade ? ` ${unidadeCarrinho(i)}` : ""}`}
                          disabled={carrinhoBloqueado}
                          onClick={() => alterarQtd(linhaCarrinho(i), passoQtd(unidadeCarrinho(i)))}
                          className="w-9 h-9 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700 transition-colors disabled:opacity-40"
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                      <div className="ml-auto text-right min-w-20">
                        <p className="text-brand-400 font-black text-sm">{moeda(sub)}</p>
                        <button
                          type="button"
                          data-acao-carrinho
                          aria-label={`Remover ${i.nome}${i.vende_por_unidade ? ` ${unidadeCarrinho(i)}` : ""} da compra`}
                          disabled={carrinhoBloqueado}
                          onClick={() => removerDoCarrinho(linhaCarrinho(i))}
                          className="mt-1 inline-flex items-center gap-1 rounded-lg bg-red-500/10 px-2 py-2 text-xs font-bold text-red-300 hover:bg-red-500/20 disabled:opacity-40"
                        >
                          <Minus size={14} /> Remover
                        </button>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Totais */}
            <div className="bg-slate-800/30 rounded-2xl p-4 border border-slate-700/30 space-y-3 mb-6 lg:mb-4">
              <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-slate-500">Subtotal</span>
                <span className="text-white text-sm">{moeda(subtotal)}</span>
              </div>
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider">
                <span className="text-slate-500">Desconto</span>
                <div className="relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500">R$</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    ref={descontoRef}
                    aria-label="Desconto"
                    disabled={carrinhoBloqueado}
                    value={descontoTexto}
                    onChange={(e) => setDescontoTexto(e.target.value)}
                    placeholder="0"
                    className="w-24 bg-slate-900/50 border border-slate-700/50 rounded-lg pl-7 pr-2 py-1.5 text-brand-400 text-right text-xs font-bold focus:outline-none focus:border-brand-500 transition-all"
                  />
                </div>
              </div>
              <div className="pt-3 border-t border-slate-700/50 flex justify-between items-end">
                <span className="text-slate-400 text-xs font-black uppercase tracking-widest">Total a Pagar</span>
                <span className="text-white font-black text-2xl tracking-tighter">
                  <span className="text-brand-400 text-sm mr-1">R$</span>
                  {decimal2(total)}
                </span>
              </div>
            </div>

            {/* Pagamento */}
            <div className="mb-6 lg:mb-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest">Forma de Pagamento</span>
                <button type="button" onClick={alternarDivisao} disabled={carrinhoBloqueado || carrinhoVazio || total <= 0}
                  ref={divisao ? pagamentoRef : undefined} aria-pressed={!!divisao}
                  className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-bold text-brand-300 hover:bg-slate-800 disabled:opacity-50">
                  {divisao ? "Pagamento único" : "Dividir"}
                </button>
              </div>
              {divisao ? (
                <div className="space-y-2">
                  {divisao.map((parte, i) => (
                    <div key={i} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-2">
                      <select aria-label={`Forma da parcela ${i + 1}`} disabled={carrinhoBloqueado} value={parte.forma}
                        onChange={e => setDivisao(divisao.map((p, j) => i === j ? { ...p, forma: e.target.value as FormaDividida } : p))}
                        className="min-w-0 rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-white">
                        {PAGAMENTOS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                      </select>
                      <div className="relative min-w-0">
                        <span className="absolute left-2 top-2 text-xs text-slate-400">R$</span>
                        <input aria-label={`Valor da parcela ${i + 1}`} inputMode="decimal" value={parte.valor}
                          placeholder="0,00" disabled={carrinhoBloqueado}
                          onChange={e => setDivisao(divisao.map((p, j) => i === j ? { ...p, valor: e.target.value } : p))}
                          className="w-full rounded-lg border border-slate-700 bg-slate-900 py-2 pl-7 pr-2 text-right text-sm text-white" />
                      </div>
                      <button type="button" aria-label={`Remover parcela ${i + 1}`} disabled={carrinhoBloqueado || divisao.length <= 2}
                        onClick={() => setDivisao(divisao.filter((_, j) => i !== j))}
                        className="rounded-lg px-2 text-slate-400 hover:bg-slate-800 disabled:opacity-30"><X size={16} /></button>
                    </div>
                  ))}
                  <div className="flex items-center justify-between gap-2">
                    <button type="button" disabled={carrinhoBloqueado || divisao.length >= 100}
                      onClick={() => setDivisao([...divisao, { forma: "pix", valor: "" }])}
                      className="px-1 py-1.5 text-xs font-bold text-brand-300 hover:underline disabled:opacity-50">Adicionar parcela</button>
                    <span aria-live="polite" className={`text-xs font-bold ${divisaoOk ? "text-emerald-400" : "text-amber-400"}`}>
                      {faltaParcelas !== 0 ? `${faltaParcelas > 0 ? "Falta" : "Sobra"} ${moeda(Math.abs(faltaParcelas) / 100)}`
                        : divisaoOk ? "Total conferido" : "Preencha todos os valores"}
                    </span>
                  </div>
                </div>
              ) : <div className="grid grid-cols-5 gap-2">
                {PAGAMENTOS.map((fp) => (
                  <motion.button
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    key={fp.value}
                    ref={pagamento === fp.value ? pagamentoRef : undefined}
                    disabled={carrinhoBloqueado}
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
              </div>}
            </div>

            {usaDinheiro && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                ref={painelDinheiroRef}
                className="mb-6 lg:mb-4 rounded-2xl border border-slate-700/40 bg-slate-800/30 p-4"
              >
                <div className="flex items-center justify-between gap-3 mb-3">
                  <label className="text-slate-500 text-[10px] font-black uppercase tracking-widest">Dinheiro recebido</label>
                  <span className={`text-xs font-black ${dinheiroOk ? "text-emerald-400" : "text-amber-400"}`}>
                    {dinheiroOk ? `Troco ${moeda(trocoDinheiro)}` : `Falta ${moeda(faltaDinheiro)}`}
                  </span>
                </div>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm font-bold">R$</span>
                  <input
                    type="text"
                    inputMode="decimal"
                    aria-label="Dinheiro recebido"
                    disabled={carrinhoBloqueado}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !loading && !pixLoading && !maqModal && !pixModal) {
                        e.preventDefault();
                        void finalizarVenda();
                      }
                    }}
                    value={valorRecebido}
                    onChange={(e) => setValorRecebido(e.target.value.replace(/[^\d,.]/g, ""))}
                    placeholder="0,00"
                    className="w-full bg-slate-950/60 border border-slate-700 rounded-xl pl-11 pr-4 py-3 text-white text-2xl font-black text-right focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="grid grid-cols-4 gap-2 mt-3">
                  {[parteDinheiro, 50, 100, 200].map((v, idx) => (
                    <button
                      key={`${v}-${idx}`}
                      disabled={carrinhoBloqueado}
                      onClick={() => setValorRecebido(v.toFixed(2).replace(".", ","))}
                      className="py-2 rounded-xl bg-slate-900/70 hover:bg-slate-700 text-slate-300 text-xs font-black transition-colors active:scale-95"
                    >
                      {idx === 0 ? "Exato" : moeda(v).replace("R$ ", "")}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Select de cliente para venda fiada */}
            {usaFiado && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6"
              >
                <label className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-2 block">Selecionar Cliente</label>
                <select
                  aria-label="Cliente do fiado"
                  disabled={carrinhoBloqueado}
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
                  disabled={carrinhoBloqueado}
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
                    disabled={carrinhoBloqueado}
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
                    onChange={(e) => setImprimirAuto(e.target.checked)}
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
            </div>
            </div>

            {/* Rodapé fixo: sempre visível, por maior que seja a lista de produtos. */}
            <div className="shrink-0 pt-3 border-t border-slate-800/60">
              {licencaBloqueada && (
                <p className="mb-3 rounded border border-amber-400/40 bg-amber-400/10 p-2 text-xs text-amber-200">
                  Licença suspensa. Dá para fechar o caixa e exportar, mas não vender.
                </p>
              )}

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={finalizarVenda}
                disabled={finalizarDesabilitado || licencaBloqueada}
                className={`w-full py-4 rounded-2xl text-white font-black text-lg tracking-tight shadow-xl transition-all flex items-center justify-center gap-3 ${
                  finalizarDesabilitado || licencaBloqueada
                    ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                    : "bg-gradient-to-r from-emerald-600 to-teal-600 shadow-emerald-900/20"
                }`}
              >
                {loading ? (
                  <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <CheckCircle2 size={22} />
                    <span>{planoDivididoRef.current ? "RETOMAR VENDA" : "FINALIZAR VENDA"}</span>
                    {carrinho.length > 0 && <span className="text-base font-bold opacity-90">· {moeda(total)}</span>}
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
                {reciboDaVenda && (
                  <button
                    onClick={() => imprimirRecibo(reciboDaVenda, largura, () => buscaRef.current?.focus())}
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
          <div className="mt-auto pt-6 lg:pt-3 border-t border-slate-800/50 flex justify-between items-center relative z-10">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">
              Vendas Hoje
            </div>
            <div className="text-right">
              <p className="text-white font-bold text-sm">{moeda((dash.vendas_hoje_total || 0))}</p>
              <p className="text-brand-400 text-[10px] font-bold uppercase tracking-tighter">{dash.vendas_hoje_qtd} vendas</p>
            </div>
          </div>
        )}
      </div>

      {janela && <JanelaProdutoModal janela={janela} onFechar={fecharJanela} onPronto={produtoPronto} onSalvando={setJanelaSalvando} />}

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
                {pixModal.qr_base64 ? "Escaneie o QR Code abaixo para pagar" : "Receba o PIX e confirme após verificar o pagamento."}
              </p>

              {pixModal.qr_base64 && <div className="bg-white rounded-2xl p-4 mb-6 inline-block shadow-inner mx-auto">
                <img
                  src={`data:image/png;base64,${pixModal.qr_base64}`}
                  alt="QR Code PIX"
                  className="w-48 h-48 mx-auto"
                />
              </div>}

              <div className="mb-6">
                <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total a Pagar</p>
                <p className="text-brand-400 font-black text-3xl tracking-tighter">
                  <span className="text-lg mr-1">R$</span>
                  {decimal2(planoDivididoRef.current?.parcelas[planoDivididoRef.current.proxima]?.valor ?? total)}
                </p>
              </div>

              {pixModal.payload && <div className="bg-slate-800/50 rounded-2xl p-4 mb-8 border border-slate-700/50">
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
              </div>}

              <div className="flex gap-3">
                <button
                  onClick={cancelarPix}
                  className="flex-1 px-4 py-4 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-2xl text-sm font-black uppercase tracking-widest transition-all"
                >
                  VOLTAR
                </button>
                <button
                  onClick={() => {
                    const plano = planoDivididoRef.current;
                    if (plano) {
                      if (pixManualConfirmadoRef.current) return;
                      pixManualConfirmadoRef.current = true;
                      setPixModal(null);
                      concluirParcela(plano);
                    } else {
                      void confirmarVenda();
                    }
                  }}
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

      {/* ── Modal PIX automático (Mercado Pago) — fecha a venda sozinho ── */}
      <AnimatePresence>
        {pixMp && (
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

              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-brand-600/10 flex items-center justify-center text-brand-400">
                  <Smartphone size={20} />
                </div>
                <h2 className="text-white font-black text-xl tracking-tight">PAGAMENTO PIX</h2>
                <button
                  onClick={cancelarPixMp}
                  disabled={pixMpProcessando}
                  className="w-10 h-10 rounded-xl hover:bg-slate-800 flex items-center justify-center text-slate-500 transition-colors disabled:opacity-40"
                >
                  <X size={20} />
                </button>
              </div>

              {pixMp.fase === "aguardando" && (
                <>
                  <p className="text-slate-400 text-sm mb-4">
                    Mostre o QR para o cliente pagar. <span className="text-emerald-400 font-bold">{planoDivididoRef.current ? "A parcela é confirmada automaticamente" : "A venda fecha sozinha"}</span> quando o PIX cair.
                  </p>
                  <div className="bg-white rounded-2xl p-4 mb-4 inline-block shadow-inner mx-auto">
                    {pixMp.cobranca.qr_base64 ? (
                      <img
                        src={`data:image/png;base64,${pixMp.cobranca.qr_base64}`}
                        alt="QR Code PIX"
                        className="w-48 h-48 mx-auto"
                      />
                    ) : (
                      <div className="w-48 h-48 flex items-center justify-center text-slate-400 text-xs">
                        Gerando QR...
                      </div>
                    )}
                  </div>
                  <div className="mb-4">
                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total a Pagar</p>
                    <p className="text-brand-400 font-black text-3xl tracking-tighter">
                      <span className="text-lg mr-1">R$</span>{decimal2(pixMp.cobranca.valor ?? total)}
                    </p>
                  </div>
                  <div className="flex items-center justify-center gap-2 text-emerald-400 text-sm font-bold mb-4">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                    Aguardando o pagamento...
                  </div>
                  {!!pixMp.cobranca.payload && (
                    <div className="bg-slate-800/50 rounded-2xl p-4 mb-4 border border-slate-700/50">
                      <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-2 text-left">Pix Copia e Cola</p>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          readOnly
                          value={pixMp.cobranca.payload}
                          className="flex-1 bg-slate-950/50 text-white text-xs font-mono rounded-lg px-3 py-2 border border-slate-800 truncate"
                          onClick={(e) => (e.target as HTMLInputElement).select()}
                        />
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(pixMp.cobranca.payload);
                            setMsg({ tipo: "ok", texto: "Código PIX copiado!" });
                          }}
                          className="px-4 bg-brand-600 hover:bg-brand-500 text-white text-xs font-black uppercase rounded-lg transition-all active:scale-95"
                        >
                          COPIAR
                        </button>
                      </div>
                    </div>
                  )}
                  {!planoDivididoRef.current && <button
                    onClick={cancelarPixMp}
                    className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl text-xs font-black uppercase tracking-widest transition-all"
                  >
                    Cancelar cobrança
                  </button>}
                </>
              )}

              {pixMp.fase === "aprovado" && (
                <div className="py-8">
                  <CheckCircle2 size={56} className="mx-auto text-emerald-400 mb-4" />
                  <p className="text-white font-black text-xl mb-2">PIX CONFIRMADO</p>
                  <p className="text-slate-400 text-sm">
                    {pixMpProcessando ? "Fechando a venda..." : "Registrando a venda..."}
                  </p>
                </div>
              )}

              {pixMp.fase === "erro" && (
                <>
                  <AlertCircle size={48} className="mx-auto text-amber-400 mb-4" />
                  <p className="text-white font-black text-lg mb-2">PIX APROVADO, VENDA NÃO FECHOU</p>
                  <p className="text-slate-400 text-sm mb-4">{pixMp.erro}</p>
                  <p className="text-amber-300 text-xs mb-4">
                    O dinheiro entrou no Mercado Pago. Corrija o motivo (estoque, por exemplo) e registre a venda — não cobre o cliente de novo.
                  </p>
                  <button
                    onClick={() => {
                      void fecharVendaPixMp(pixMp.cobranca);
                    }}
                    className="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl text-xs font-black uppercase tracking-widest mb-2"
                  >
                    Tentar fechar de novo
                  </button>
                  <button
                    onClick={cancelarPixMp}
                    className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl text-xs font-black uppercase tracking-widest"
                  >
                    Fechar
                  </button>
                </>
              )}
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
                  <span className="text-lg mr-1">R$</span>{decimal2(maqModal.valor ?? total)}
                </p>
              </div>

              {maqModal.fase !== "erro" ? (
                <>
                  <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                  <p className="text-white text-sm font-bold mb-1">
                    {maqModal.fase === "criando"
                      ? "Acionando a maquininha..."
                      : maqModal.forma === "pix" ? "Peça o PIX na maquininha"
                      : maqModal.forma === "debito"
                        ? "Peça o cartão no débito"
                        : "Peça o cartão no crédito"}
                  </p>
                  <p className="text-slate-500 text-xs mb-8">
                    {maqModal.erro || ESTADO_MAQ[maqModal.estado || ""] || "Aguardando a maquininha..."}
                  </p>
                  <button
                    onClick={cancelarCobrancaMaq}
                    disabled={maqModal.fase === "criando"}
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
                    {!planoDivididoRef.current && <button
                      onClick={registrarCartaoManual}
                      disabled={loading}
                      className="w-full px-4 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl text-sm font-black uppercase tracking-widest transition-all shadow-lg shadow-emerald-900/20"
                    >
                      {loading ? "..." : "REGISTRAR CARTÃO MANUAL"}
                    </button>}
                    <button
                      onClick={cancelarCobrancaMaq}
                      className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-2xl text-sm font-black uppercase tracking-widest transition-all"
                    >
                      FECHAR
                    </button>
                  </div>
                  {!planoDivididoRef.current && <p className="text-slate-500 text-[11px] mt-4 leading-snug">
                    "Cartão manual" = você passou o cartão direto no aparelho; o sistema só registra a venda.
                  </p>}
                </>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

