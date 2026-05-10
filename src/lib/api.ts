const API_BASE = import.meta.env.VITE_API_URL || "https://vendafacil-api.cursar.space";

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
  const data = await res.json();

  if (!res.ok) {
    // Handle validation errors (array of messages)
    const msg =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail?.erros)
          ? data.detail.erros.join(" ")
          : JSON.stringify(data.detail || "Erro na requisição");
    throw new Error(msg);
  }
  return data;
}

// ── Auth ──

export interface User {
  id: number;
  email: string;
  nome: string;
}

export function login(email: string, senha: string) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
}

export function registro(email: string, nome: string, senha: string) {
  return request("/api/auth/registro", {
    method: "POST",
    body: JSON.stringify({ email, nome, senha }),
  });
}

export function getMe(): Promise<User | null> {
  if (!getToken()) return Promise.resolve(null);
  return request("/api/auth/me")
    .then((d) => d.user)
    .catch(() => null);
}

// ── Produtos ──

export interface Produto {
  id: number;
  user_id: number;
  nome: string;
  preco_custo: number;
  preco_venda: number;
  estoque: number;
  estoque_minimo: number;
  codigo_barras: string;
  unidade: string;
  ativo: number;
  criado_em: string;
  atualizado_em: string;
}

export interface ProdutoInput {
  nome: string;
  preco_custo?: number;
  preco_venda?: number;
  estoque?: number;
  estoque_minimo?: number;
  codigo_barras?: string;
  unidade?: string;
}

export interface ProdutoUpdate {
  nome?: string;
  preco_custo?: number;
  preco_venda?: number;
  estoque?: number;
  estoque_minimo?: number;
  codigo_barras?: string;
  unidade?: string;
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
  ativo: number;
  criado_em: string;
}

export interface ClienteInput {
  nome: string;
  telefone?: string;
  email?: string;
  endereco?: string;
  observacao?: string;
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

export interface CheckoutInput {
  itens: ItemVenda[];
  desconto?: number;
  forma_pagamento?: string;
  observacao?: string;
}

export function checkout(data: CheckoutInput): Promise<{ venda: Venda; itens: ItemVendaProcessado[] }> {
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
