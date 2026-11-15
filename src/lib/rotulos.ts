// Rótulos de exibição compartilhados entre as telas.
const FORMAS: Record<string, string> = {
  dinheiro: "Dinheiro", pix: "PIX", debito: "Débito", credito: "Crédito", fiado: "Fiado",
};

/** Forma de pagamento como o lojista lê: "Débito", "PIX"... */
export function rotuloForma(forma: string | null | undefined): string {
  const chave = String(forma || "").toLowerCase();
  return FORMAS[chave] || (chave ? chave[0].toUpperCase() + chave.slice(1) : "—");
}

/** "1 cliente" / "3 clientes". */
export function plural(n: number, um: string, varios: string): string {
  return `${n} ${n === 1 ? um : varios}`;
}
