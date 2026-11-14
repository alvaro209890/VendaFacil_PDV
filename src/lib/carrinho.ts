import type { Produto } from './api';

export type CartItem = Produto & { qtd: number; modo_venda?: 'embalagem' | 'unidade' };

export const linhaCarrinho = (p: CartItem) => `${p.id}:${p.modo_venda || 'unidade'}`;
export const fatorCarrinho = (p: CartItem) => p.vende_por_unidade && p.modo_venda === 'embalagem' ? p.quantidade_por_embalagem : 1;
export const unidadeCarrinho = (p: CartItem) => p.vende_por_unidade && p.modo_venda === 'embalagem' ? p.unidade_compra : p.unidade;
export function itemCarrinho(p: Produto, modo: 'embalagem' | 'unidade' = 'unidade', qtd = 1): CartItem {
  return {...p, qtd, modo_venda: p.vende_por_unidade ? modo : undefined,
    preco_venda: p.vende_por_unidade ? Number(modo === 'embalagem' ? p.preco_embalagem : p.preco_unidade) : p.preco_venda};
}
export function limiteCarrinho(p: CartItem, itens: CartItem[]): number {
  const outros = itens.filter(i => i.id === p.id && linhaCarrinho(i) !== linhaCarrinho(p))
    .reduce((s,i) => s + i.qtd * fatorCarrinho(i), 0);
  const limite = Math.max(0, (p.estoque - outros) / fatorCarrinho(p));
  return p.vende_por_unidade ? Math.floor(limite) : limite;
}

function itemValido(item: unknown): item is CartItem {
  if (!item || typeof item !== 'object') return false;
  const p = item as Partial<CartItem>;
  return (p.modo_venda === undefined || p.modo_venda === 'unidade' || p.modo_venda === 'embalagem')
    && Number.isInteger(p.id) && Number(p.id) > 0
    && typeof p.nome === 'string' && typeof p.codigo_barras === 'string'
    && typeof p.qtd === 'number' && Number.isFinite(p.qtd) && p.qtd > 0
    && typeof p.preco_venda === 'number' && Number.isFinite(p.preco_venda) && p.preco_venda >= 0
    && typeof p.preco_custo === 'number' && Number.isFinite(p.preco_custo) && p.preco_custo >= 0
    && typeof p.estoque === 'number' && Number.isFinite(p.estoque) && p.estoque >= 0;
}

export function lerCarrinho(chave: string): CartItem[] {
  try {
    const itens: unknown = JSON.parse(localStorage.getItem(chave) || '[]');
    return Array.isArray(itens) ? itens.filter(itemValido) : [];
  } catch {
    return [];
  }
}

export function salvarCarrinho(chave: string, itens: CartItem[]): boolean {
  try {
    if (itens.length) localStorage.setItem(chave, JSON.stringify(itens));
    else localStorage.removeItem(chave);
    return true;
  } catch {
    return false;
  }
}
