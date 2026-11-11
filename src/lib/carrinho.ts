import type { Produto } from './api';

export type CartItem = Produto & { qtd: number };

function itemValido(item: unknown): item is CartItem {
  if (!item || typeof item !== 'object') return false;
  const p = item as Partial<CartItem>;
  return Number.isInteger(p.id) && Number(p.id) > 0
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
