// Entrada numérica completa; o componente conserva o texto enquanto se digita.
// Retorna null em formato inválido em vez de truncar ou transformar em zero.
export function lerNumeroPtBr(texto: string, casas?: number): number | null {
  const valor = texto.trim().replace(',', '.');
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(valor)) return null;
  if (casas !== undefined && (valor.split('.')[1]?.length ?? 0) > casas) return null;
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : null;
}
