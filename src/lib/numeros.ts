// Entrada numérica completa; o componente conserva o texto enquanto se digita.
// Retorna null em formato inválido em vez de truncar ou transformar em zero.
export function lerNumeroPtBr(texto: string, casas?: number): number | null {
  const valor = texto.trim().replace(',', '.');
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(valor)) return null;
  if (casas !== undefined && (valor.split('.')[1]?.length ?? 0) > casas) return null;
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
}

/** Valor em duas casas no padrão brasileiro: 1.234,56. */
export function decimal2(v: number | null | undefined): string {
  return Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Dinheiro para exibição: "R$ 1.234,56" (espaço comum, para busca e testes). */
export function moeda(v: number | null | undefined): string {
  return `R$ ${decimal2(v)}`;
}
