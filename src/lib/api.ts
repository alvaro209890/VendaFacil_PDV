// Sem VITE_API_URL, usa a mesma origem que serviu a página (caso do .exe local,
// onde o backend FastAPI serve o próprio frontend). Em nuvem/Render, defina
// VITE_API_URL no build apontando para o domínio da API.
const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

// ── Token ──

export function getToken(): string {
  return localStorage.getItem("vf_token") || "";
}

export function setToken(token: string) {
  localStorage.setItem("vf_token", token);
}

export function clearToken() {
  localStorage.removeItem("vf_token");
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await readJson(res);

  if (!res.ok) {
    throw new Error(errorMessageFromResponse(data, res.status));
  }
  return data;
}

async function readJson(res: Response) {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function errorMessageFromResponse(data: any, status?: number): string {
  const detail = data?.detail ?? data;
  const requestId = data?.request_id || detail?.request_id;
  let msg = "";

  if (typeof detail === "string") {
    msg = detail;
  } else if (Array.isArray(detail?.erros) && detail.erros.length) {
    msg = detail.erros.join(" ");
  } else if (typeof detail?.mensagem === "string") {
    msg = detail.mensagem;
  } else if (Array.isArray(detail)) {
    msg = detail.map((item) => item?.msg || item?.mensagem || String(item)).join(" ");
  } else {
    msg = status === 422 ? "Revise os campos informados." : "Erro na requisição.";
  }

  return requestId ? `${msg} Código: ${requestId}` : msg;
}

// ── Ativação / Licença ──

export interface AtivacaoStatus {
  obrigatoria: boolean;
  ativado: boolean;
  bloqueado: boolean;
  motivo: string;
  nome_loja?: string;
  licenca_expira_em?: string | null;
  dias_desde_validacao?: number;
  carencia_dias?: number;
}

export function getAtivacaoStatus(): Promise<AtivacaoStatus> {
  return request("/api/ativacao/status");
}

export function ativar(login: string, senha: string): Promise<AtivacaoStatus> {
  return request("/api/ativacao", {
    method: "POST",
    body: JSON.stringify({ login, senha }),
  });
}

// ── Auth ──

export interface User {
  id: number;
  usuario: string;
  email: string;
  nome: string;
}

export function login(usuario: string, senha: string) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ usuario, senha }),
  });
}

export function registro(usuario: string, nome: string, senha: string) {
  return request("/api/auth/registro", {
    method: "POST",
    body: JSON.stringify({ usuario, nome, senha }),
  });
}

export function getMe(): Promise<User | null> {
  if (!getToken()) return Promise.resolve(null);
  return request("/api/auth/me")
    .then((d) => d.user)
    .catch(() => null);
}

// ── Produtos ──

/** Campos fiscais (NFC-e) — todos opcionais. */
export interface CamposFiscais {
  ncm?: string;
  cest?: string;
  cfop?: string;
  origem?: string;
  unidade_tributavel?: string;
  cst_csosn?: string;
  aliquota_icms?: number;
  cst_pis?: string;
  aliquota_pis?: number;
  cst_cofins?: string;
  aliquota_cofins?: number;
}

export interface Produto extends CamposFiscais {
  id: number;
  user_id: number;
  categoria_id: number | null;
  categoria_nome?: string | null;
  nome: string;
  preco_custo: number;
  preco_venda: number;
  estoque: number;
  estoque_minimo: number;
  codigo_barras: string;
  unidade: string;
  unidade_compra: string;
  quantidade_por_embalagem: number;
  ativo: number;
  criado_em: string;
  atualizado_em: string;
}

export interface ProdutoInput extends CamposFiscais {
  nome: string;
  categoria_id?: number | null;
  preco_custo?: number;
  preco_venda?: number;
  estoque?: number;
  estoque_minimo?: number;
  codigo_barras?: string;
  unidade?: string;
  unidade_compra?: string;
  quantidade_por_embalagem?: number;
}

export interface ProdutoUpdate extends CamposFiscais {
  nome?: string;
  categoria_id?: number | null;
  preco_custo?: number;
  preco_venda?: number;
  estoque?: number;
  estoque_minimo?: number;
  codigo_barras?: string;
  unidade?: string;
  unidade_compra?: string;
  quantidade_por_embalagem?: number;
  ativo?: number;
}

export function listarProdutos(ativos = true): Promise<{ produtos: Produto[] }> {
  return request(`/api/produtos?ativos=${ativos}`);
}

export function obterProduto(id: number): Promise<{ produto: Produto }> {
  return request(`/api/produtos/${id}`);
}

export function criarProduto(data: ProdutoInput): Promise<{ produto: Produto }> {
  return request("/api/produtos", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function atualizarProduto(id: number, data: ProdutoUpdate): Promise<{ produto: Produto }> {
  return request(`/api/produtos/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function desativarProduto(id: number): Promise<{ ok: boolean }> {
  return request(`/api/produtos/${id}`, { method: "DELETE" });
}

// ── Estoque: importação de XML (NF-e) e entrada manual ──

export interface ItemXml {
  nome: string;
  codigo_barras: string;
  unidade: string;
  unidade_xml?: string;
  unidade_compra: string;
  quantidade_por_embalagem: number;
  quantidade: number;
  quantidade_xml: number;
  valor_unitario: number;
  valor_unitario_xml?: number;
  ncm: string;
  cfop: string;
  produto_id: number | null;
  produto_nome: string | null;
  estoque_atual: number;
  preco_custo_atual: number | null;
  preco_venda_atual: number | null;
  acao: "atualizar" | "criar";
}

export interface PreviewXml {
  emitente: string;
  numero: string;
  chave: string;
  itens: ItemXml[];
}

export interface ItemConfirmarXml {
  produto_id: number | null;
  nome: string;
  codigo_barras: string;
  unidade: string;
  unidade_compra: string;
  quantidade_por_embalagem: number;
  quantidade: number;
  quantidade_xml?: number;
  preco_custo: number;
  preco_venda: number;
  atualizar_custo: boolean;
  ncm?: string;
  cfop?: string;
}

/** Envia o arquivo XML cru e recebe os itens já casados com o estoque. */
export async function importarXmlPreview(file: File | Blob): Promise<PreviewXml> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/produtos/importar-xml/preview`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: file,
  });
  const data = await readJson(res);
  if (!res.ok) throw new Error(errorMessageFromResponse(data, res.status) || "Não consegui ler o XML.");
  return data;
}

export function importarXmlConfirmar(documento: string, itens: ItemConfirmarXml[]): Promise<{ criados: number; atualizados: number; total: number }> {
  return request("/api/produtos/importar-xml/confirmar", {
    method: "POST",
    body: JSON.stringify({ documento, itens }),
  });
}

export function entradaEstoque(produtoId: number, quantidade: number, custo_unitario?: number, observacao?: string): Promise<{ produto: Produto }> {
  return request(`/api/produtos/${produtoId}/entrada`, {
    method: "POST",
    body: JSON.stringify({ quantidade, custo_unitario, observacao }),
  });
}

export type TipoAjuste = "perda" | "quebra" | "inventario";

export function ajustarEstoque(produtoId: number, tipo: TipoAjuste, quantidade: number, observacao?: string): Promise<{ produto: Produto }> {
  return request(`/api/produtos/${produtoId}/ajuste`, {
    method: "POST",
    body: JSON.stringify({ tipo, quantidade, observacao }),
  });
}

export interface Movimentacao {
  id: number;
  produto_id: number;
  produto_nome: string | null;
  tipo: "entrada" | "saida";
  quantidade: number;
  custo_unitario: number | null;
  origem: string;        // manual | xml | venda | perda | quebra | inventario
  documento: string;
  observacao: string;
  criado_em: string;
}

export function listarMovimentacoes(produtoId: number): Promise<{ movimentacoes: Movimentacao[] }> {
  return request(`/api/produtos/${produtoId}/movimentacoes`);
}

// ── Categorias ──

export interface Categoria {
  id: number;
  user_id: number;
  nome: string;
  cor: string;
  ativo: number;
  criado_em: string;
  total_produtos: number;
}

export interface CategoriaInput {
  nome: string;
  cor?: string;
}

export function listarCategorias(): Promise<{ categorias: Categoria[] }> {
  return request("/api/categorias");
}

export function criarCategoria(data: CategoriaInput): Promise<{ categoria: Categoria }> {
  return request("/api/categorias", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function atualizarCategoria(id: number, data: Partial<CategoriaInput>): Promise<{ categoria: Categoria }> {
  return request(`/api/categorias/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function removerCategoria(id: number): Promise<{ ok: boolean }> {
  return request(`/api/categorias/${id}`, { method: "DELETE" });
}

// ── Clientes ──

export interface Cliente {
  id: number;
  user_id: number;
  nome: string;
  telefone: string;
  email: string;
  endereco: string;
  observacao: string;
  documento: string;
  inscricao_estadual: string;
  indicador_ie: string;
  logradouro: string;
  numero: string;
  bairro: string;
  municipio: string;
  codigo_municipio: string;
  uf: string;
  cep: string;
  ativo: number;
  criado_em: string;
}

export interface ClienteInput {
  nome: string;
  telefone?: string;
  email?: string;
  endereco?: string;
  observacao?: string;
  documento?: string;
  inscricao_estadual?: string;
  indicador_ie?: string;
  logradouro?: string;
  numero?: string;
  bairro?: string;
  municipio?: string;
  codigo_municipio?: string;
  uf?: string;
  cep?: string;
}

export function listarClientes(): Promise<{ clientes: Cliente[] }> {
  return request("/api/clientes");
}

export function obterCliente(id: number): Promise<{ cliente: Cliente }> {
  return request(`/api/clientes/${id}`);
}

export function criarCliente(data: ClienteInput): Promise<{ cliente: Cliente }> {
  return request("/api/clientes", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function atualizarCliente(id: number, data: Partial<ClienteInput>): Promise<{ cliente: Cliente }> {
  return request(`/api/clientes/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function removerCliente(id: number): Promise<{ ok: boolean }> {
  return request(`/api/clientes/${id}`, { method: "DELETE" });
}

// ── Contas a Receber ──

export interface ContaReceber {
  id: number;
  user_id: number;
  venda_id: number | null;
  cliente_id: number | null;
  cliente_nome: string | null;
  valor_total: number;
  valor_pendente: number;
  data_vencimento: string | null;
  status: string;
  observacao: string;
  criado_em: string;
}

export interface ContaReceberInput {
  cliente_id?: number | null;
  venda_id?: number | null;
  valor_total: number;
  data_vencimento?: string | null;
  observacao?: string;
}

export function listarContasReceber(status?: string): Promise<{ contas: ContaReceber[] }> {
  const qs = status ? `?status=${status}` : "";
  return request(`/api/contas-receber${qs}`);
}

export function criarContaReceber(data: ContaReceberInput): Promise<{ conta: ContaReceber }> {
  return request("/api/contas-receber", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function pagarContaReceber(id: number, data: { valor: number }): Promise<{ conta: ContaReceber }> {
  return request(`/api/contas-receber/${id}/pagar`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function cancelarContaReceber(id: number): Promise<{ ok: boolean }> {
  return request(`/api/contas-receber/${id}/cancelar`, {
    method: "POST",
  });
}

// ── Vendas ──

export interface ItemVenda {
  produto_id: number;
  quantidade: number;
}

export interface ItemVendaProcessado {
  produto_id: number;
  nome_produto: string;
  quantidade: number;
  preco_unitario: number;
  subtotal: number;
}

export interface Venda {
  id: number;
  user_id: number;
  total: number;
  desconto: number;
  forma_pagamento: string;
  status: string;
  observacao: string;
  criado_em: string;
  itens?: ItemVendaProcessado[];
}

export interface PagamentoEletronico {
  tipo_integracao?: string;   // 1 integrado | 2 não integrado
  adquirente_cnpj?: string;
  bandeira?: string;          // tBand ou id da bandeira do Mercado Pago
  autorizacao?: string;       // cAut
  payment_id?: string;
  terminal?: string;
}

export interface CheckoutInput {
  itens: ItemVenda[];
  desconto?: number;
  forma_pagamento?: string;
  observacao?: string;
  cliente_id?: number | null;
  cpf_consumidor?: string | null;
  emitir_nota?: boolean;
  pagamento?: PagamentoEletronico;
}

export function checkout(data: CheckoutInput): Promise<{ 
  venda: Venda; 
  itens: ItemVendaProcessado[]; 
  nota?: NotaFiscal; 
  erro_nota?: string 
}> {
  return request("/api/vendas/checkout", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listarVendas(limit = 50, offset = 0): Promise<{ vendas: Venda[] }> {
  return request(`/api/vendas?limit=${limit}&offset=${offset}`);
}

export function obterVenda(id: number): Promise<{ venda: Venda }> {
  return request(`/api/vendas/${id}`);
}

// ── Dashboard ──

export interface DashboardData {
  total_produtos: number;
  alertas_estoque: number;
  vendas_hoje_qtd: number;
  vendas_hoje_total: number;
  vendas_total: number;
  ultimas_vendas: Venda[];
  produtos_baixo_estoque: { id: number; nome: string; estoque: number; estoque_minimo: number }[];
}

export function getDashboard(): Promise<DashboardData> {
  return request("/api/dashboard");
}

// ── Relatórios ──

export interface RelatorioVendas {
  inicio: string;
  fim: string;
  faturamento: number;
  qtd_vendas: number;
  ticket_medio: number;
  desconto_total: number;
  lucro_estimado: number;
  por_forma: { forma_pagamento: string; qtd: number; total: number }[];
  por_dia: { dia: string; qtd: number; total: number }[];
  top_produtos: { produto_id: number; nome_produto: string; qtd: number; total: number }[];
}

export function relatorioVendas(inicio: string, fim: string): Promise<RelatorioVendas> {
  return request(`/api/relatorios/vendas?inicio=${encodeURIComponent(inicio)}&fim=${encodeURIComponent(fim)}`);
}

export interface RelatorioFiscalItem {
  produto_id: number;
  nome_produto: string;
  ncm: string;
  csosn: string;
  cst_pis: string;
  cst_cofins: string;
  qtd: number;
  total: number;
  icms_substituicao: boolean;
  pis_cofins_concentrado: boolean;
}

export interface RelatorioFiscal {
  inicio: string;
  fim: string;
  total_geral: number;
  icms: { substituicao_tributaria: number; tributado_normal: number };
  pis_cofins: { monofasico_st: number; tributado_normal: number };
  receita_segregada: number;
  receita_tributada_integral: number;
  itens: RelatorioFiscalItem[];
}

export function relatorioFiscal(inicio: string, fim: string): Promise<RelatorioFiscal> {
  return request(`/api/relatorios/fiscal?inicio=${encodeURIComponent(inicio)}&fim=${encodeURIComponent(fim)}`);
}

// ── Caixa (abertura/fechamento) ──

export interface CaixaResumo {
  vendas_qtd: number;
  vendas_total: number;
  por_forma: Record<string, { qtd: number; total: number }>;
  vendas_dinheiro: number;
  suprimentos: number;
  sangrias: number;
  valor_abertura: number;
  dinheiro_esperado: number;
}

export interface CaixaSessao {
  id: number;
  valor_abertura: number;
  aberto_em: string;
  fechado_em: string | null;
  valor_fechamento: number | null;
  valor_esperado: number | null;
  diferenca: number | null;
  observacao: string;
}

export interface CaixaAtual {
  aberto: boolean;
  sessao?: CaixaSessao;
  resumo?: CaixaResumo;
}

export function caixaAtual(): Promise<CaixaAtual> {
  return request("/api/caixa/atual");
}

export function abrirCaixa(valor_abertura: number): Promise<CaixaAtual> {
  return request("/api/caixa/abrir", { method: "POST", body: JSON.stringify({ valor_abertura }) });
}

export function movimentoCaixa(tipo: "sangria" | "suprimento", valor: number, motivo: string): Promise<{ resumo: CaixaResumo }> {
  return request("/api/caixa/movimento", { method: "POST", body: JSON.stringify({ tipo, valor, motivo }) });
}

export function fecharCaixa(valor_fechamento: number, observacao: string): Promise<{ sessao: CaixaSessao; resumo: CaixaResumo }> {
  return request("/api/caixa/fechar", { method: "POST", body: JSON.stringify({ valor_fechamento, observacao }) });
}

export function historicoCaixa(): Promise<{ sessoes: CaixaSessao[] }> {
  return request("/api/caixa/historico");
}

// ── Backup local ──

export interface BackupItem {
  nome: string;
  tamanho_kb: number;
  data: string;
}

/** Gera e baixa um backup (.db) — dispara o download no navegador. */
export async function baixarBackup(): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/backup/exportar`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Falha ao gerar o backup.");
  const blob = await res.blob();
  const dispo = res.headers.get("Content-Disposition") || "";
  const m = dispo.match(/filename="?([^"]+)"?/);
  const nome = m ? m[1] : "vendafacil-backup.db";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  a.click();
  URL.revokeObjectURL(url);
}

export async function restaurarBackup(file: File | Blob): Promise<{ ok: boolean }> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/backup/restaurar`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: file,
  });
  const data = await readJson(res);
  if (!res.ok) throw new Error(errorMessageFromResponse(data, res.status) || "Falha ao restaurar.");
  return data;
}

export function listarBackups(): Promise<{ backups: BackupItem[]; pasta: string }> {
  return request("/api/backup/listar");
}

// ── PIX ──

export interface PixQrCodeResponse {
  payload: string;
  qr_base64: string;
}

export async function gerarPixQrCode(valor: number): Promise<PixQrCodeResponse> {
  return request("/api/pix/qrcode", {
    method: "POST",
    body: JSON.stringify({ valor }),
  });
}

export interface ConfigPix {
  pix_chave: string;
  pix_nome: string;
  pix_cidade: string;
}

export function getConfigPix(): Promise<{ config: ConfigPix }> {
  return request("/api/pix/config");
}

export function salvarConfigPix(data: Partial<ConfigPix>): Promise<{ config: ConfigPix }> {
  return request("/api/pix/config", { method: "PUT", body: JSON.stringify(data) });
}

// ── Fiscal (NFC-e) ──

export interface ConfigFiscal {
  habilitado?: number;
  razao_social?: string;
  nome_fantasia?: string;
  cnpj?: string;
  inscricao_estadual?: string;
  regime_tributario?: string;
  logradouro?: string;
  numero?: string;
  bairro?: string;
  municipio?: string;
  codigo_municipio?: string;
  uf?: string;
  cep?: string;
  csc?: string;
  csc_id?: string;
  ambiente?: string;
  gateway?: string;
  provedor_fiscal?: string;
  gateway_token?: string;
  certificado_a1_b64?: string;
  certificado_senha?: string;
  certificado_nome?: string;
  certificado_validade?: string;
  serie?: number;
  proximo_numero?: number;
  serie_nfce?: number;
  proximo_numero_nfce?: number;
  serie_nfe?: number;
  proximo_numero_nfe?: number;
  // QR Code da NFC-e: "2" (padrão, com CSC) ou "3" (NT 2025.001, sem CSC).
  qrcode_versao?: string;
  // % aproximado dos tributos (tabela IBPT) p/ a Lei 12.741/2012; 0 = não informa.
  ibpt_percentual?: number;
  // Responsável Técnico (infRespTec) — opcional, desligado por padrão.
  resp_tec_habilitado?: number;
  resp_tec_cnpj?: string;
  resp_tec_contato?: string;
  resp_tec_email?: string;
  resp_tec_fone?: string;
  resp_tec_csrt?: string;
  resp_tec_id_csrt?: string;
  gateway_token_preenchido?: boolean;
  csc_preenchido?: boolean;
  certificado_a1_b64_preenchido?: boolean;
  certificado_senha_preenchido?: boolean;
  resp_tec_csrt_preenchido?: boolean;
}

export interface NotaFiscal {
  id: number;
  venda_id: number;
  ref: string;
  modelo: string;
  numero: number | null;
  serie: number | null;
  ambiente: string | null;
  status: string;
  chave: string | null;
  protocolo: string | null;
  mensagem: string | null;
  xml_url: string | null;
  danfe_url: string | null;
  qrcode_url: string | null;
  qrcode_base64?: string | null;
  xml_assinado?: string | null;
  xml_autorizado?: string | null;
  tipo_emissao?: string | null;
  recibo?: string | null;
  motivo_rejeicao?: string | null;
  destinatario_snapshot?: string | null;
}

export function getConfigFiscal(): Promise<{ config: ConfigFiscal }> {
  return request("/api/fiscal/config");
}

export function salvarConfigFiscal(data: ConfigFiscal): Promise<{ config: ConfigFiscal }> {
  return request("/api/fiscal/config", { method: "PUT", body: JSON.stringify(data) });
}

export function getNotaDaVenda(vendaId: number): Promise<{ nota: NotaFiscal | null }> {
  return request(`/api/fiscal/nfce/venda/${vendaId}`);
}

export function emitirNfce(vendaId: number, cpf?: string): Promise<{ nota: NotaFiscal }> {
  return request(`/api/fiscal/nfce/venda/${vendaId}/emitir`, { 
    method: "POST", 
    body: JSON.stringify({ cpf_consumidor: cpf })
  });
}

export function consultarNfce(notaId: number): Promise<{ nota: NotaFiscal }> {
  return request(`/api/fiscal/nfce/${notaId}/consultar`, { method: "POST" });
}

export function cancelarNfce(notaId: number, justificativa: string): Promise<{ nota: NotaFiscal }> {
  return request(`/api/fiscal/nfce/${notaId}/cancelar`, {
    method: "POST",
    body: JSON.stringify({ justificativa }),
  });
}

// Baixa um arquivo de um endpoint autenticado (XML/ZIP) disparando o download.
async function baixarArquivo(path: string, nomePadrao: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let msg = "Erro ao baixar arquivo.";
    try { msg = (await res.json()).detail || msg; } catch { /* corpo não-JSON */ }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="?([^"]+)"?/);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = m ? m[1] : nomePadrao;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function baixarXmlNota(notaId: number): Promise<void> {
  return baixarArquivo(`/api/fiscal/nfce/nota/${notaId}/xml`, `NFCe-${notaId}.xml`);
}

export function exportarXmlsZip(inicio?: string, fim?: string): Promise<void> {
  const qs = new URLSearchParams();
  if (inicio) qs.set("inicio", inicio);
  if (fim) qs.set("fim", fim);
  const q = qs.toString();
  return baixarArquivo(`/api/fiscal/nfce/export/xml${q ? `?${q}` : ""}`, "xmls-nfce.zip");
}

export function getNfeDaVenda(vendaId: number): Promise<{ nota: NotaFiscal | null }> {
  return request(`/api/fiscal/nfe/venda/${vendaId}`);
}

export function emitirNfe(vendaId: number, clienteId: number): Promise<{ nota: NotaFiscal }> {
  return request(`/api/fiscal/nfe/venda/${vendaId}/emitir`, {
    method: "POST",
    body: JSON.stringify({ cliente_id: clienteId }),
  });
}

export function consultarNfe(notaId: number): Promise<{ nota: NotaFiscal }> {
  return request(`/api/fiscal/nfe/${notaId}/consultar`, { method: "POST" });
}

// ── Maquininha (Mercado Pago Point) ──

export interface ConfigMaquininha {
  habilitado?: number;
  provedor?: string;
  access_token?: string;
  device_id?: string;
  store_id?: string;
  pos_id?: string;
  imprimir_comprovante?: number;
  adquirente_cnpj?: string;
  pix_integrado?: number;
  access_token_preenchido?: boolean;
}

export interface DispositivoPoint {
  id: string;
  pos_id?: number | string;
  store_id?: string;
  external_pos_id?: string;
  operating_mode?: string;
}

export interface DiagnosticoMaquininha {
  config: {
    habilitado: boolean;
    device_id: string;
    access_token_preenchido: boolean;
  };
  terminal: DispositivoPoint | null;
  operating_mode?: string;
  ultimas_orders: string[];
  ultima_order_bruta?: Record<string, unknown> | null;
}

export function getConfigMaquininha(): Promise<{ config: ConfigMaquininha }> {
  return request("/api/maquininha/config");
}

export function salvarConfigMaquininha(data: ConfigMaquininha): Promise<{ config: ConfigMaquininha }> {
  return request("/api/maquininha/config", { method: "PUT", body: JSON.stringify(data) });
}

export function listarDispositivosMaquininha(): Promise<{ dispositivos: DispositivoPoint[] }> {
  return request("/api/maquininha/dispositivos");
}

export function diagnosticoMaquininha(): Promise<DiagnosticoMaquininha> {
  return request("/api/maquininha/diagnostico");
}

export interface CobrancaMaquininha {
  payment_intent_id: string;
  state: string;
  device_id?: string;
}

export interface CobrancaStatus {
  payment_intent_id: string;
  state: string;          // OPEN, ON_TERMINAL, PROCESSING, FINISHED, CANCELED, ERROR...
  pago: boolean;
  payment_id?: string;
  payment_status?: string;
  payment_type?: string;  // credit_card | debit_card
  pagamento_fiscal?: PagamentoEletronico;  // vínculo p/ a NFC-e (Portaria 262/2023-MT)
}

export function criarCobrancaMaquininha(valor: number, venda_uuid?: string, forma?: string): Promise<CobrancaMaquininha> {
  return request("/api/maquininha/cobranca", {
    method: "POST",
    body: JSON.stringify({ valor, venda_uuid, forma }),
  });
}

export function consultarCobrancaMaquininha(id: string): Promise<CobrancaStatus> {
  return request(`/api/maquininha/cobranca/${id}`);
}

export function cancelarCobrancaMaquininha(id: string): Promise<{ cancelado: boolean }> {
  return request(`/api/maquininha/cobranca/${id}`, { method: "DELETE" });
}
