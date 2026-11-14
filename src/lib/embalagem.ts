export function estoqueBalcao(p: {estoque:number; quantidade_por_embalagem:number; unidade_compra:string; nome:string}): string {
  const fator = p.quantidade_por_embalagem || 1;
  const fechadas = Math.floor(p.estoque / fator);
  const avulsos = Number((p.estoque % fator).toFixed(4));
  const nome = p.unidade_compra.toLowerCase();
  const plural: Record<string,string> = {cx:'caixas',fd:'fardos',pct:'pacotes',display:'displays'};
  const embalagem = fechadas === 1 ? ({cx:'caixa',fd:'fardo',pct:'pacote'}[nome] || nome) : (plural[nome] || `${nome}s`);
  const fmt = (n:number) => n.toLocaleString('pt-BR', {maximumFractionDigits:4});
  return `${fmt(fechadas)} ${embalagem} e ${fmt(avulsos)} ${avulsos === 1 ? 'avulso' : 'avulsos'} (${fmt(p.estoque)} ${p.nome.toLowerCase()})`;
}
