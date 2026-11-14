export type ComparacaoPrecos = {
  porUnidadeNaEmbalagem: number;   // preço da embalagem ÷ unidades dentro
  economiaNaEmbalagem: number;     // fator × preço da unidade − preço da embalagem
  lucroEmbalagem: number | null;   // por embalagem; null sem custo
  lucroUnidade: number | null;
  margemEmbalagem: number | null;  // % sobre o preço de venda
  margemUnidade: number | null;
  alertas: string[];
};

const arred = (n: number, casas = 2) => Math.round(n * 10 ** casas) / 10 ** casas;
const reais = (n: number) => n.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});

/** Conta de balcão para quem vende caixa e unidade com preços diferentes.
 * Ex.: caixa de 15 a R$ 60 = R$ 4,00 cada; avulsa a R$ 5 → quem leva a caixa economiza R$ 15. */
export function compararPrecos(p: {custo: number; fator: number; precoEmbalagem: number; precoUnidade: number; embalagem?: string}): ComparacaoPrecos {
  const fator = p.fator > 0 ? p.fator : 1;
  const custo = Number.isFinite(p.custo) && p.custo > 0 ? p.custo : 0;
  const emb = (p.embalagem || 'embalagem').toUpperCase();
  const lucroEmbalagem = custo ? arred(p.precoEmbalagem - custo * fator) : null;
  const lucroUnidade = custo ? arred(p.precoUnidade - custo) : null;
  const margem = (lucro: number | null, preco: number) => lucro === null || !(preco > 0) ? null : arred(lucro / preco * 100, 1);
  const alertas: string[] = [];
  if (p.precoEmbalagem > 0 && p.precoUnidade > 0 && p.precoEmbalagem >= fator * p.precoUnidade)
    alertas.push(`A ${emb} sai igual ou mais cara que ${fator} unidades soltas (${reais(arred(fator * p.precoUnidade))}).`);
  if (lucroEmbalagem !== null && p.precoEmbalagem > 0 && lucroEmbalagem < 0)
    alertas.push(`Preço da ${emb} abaixo do custo (${reais(arred(custo * fator))}).`);
  if (lucroUnidade !== null && p.precoUnidade > 0 && lucroUnidade < 0)
    alertas.push(`Preço da unidade abaixo do custo (${reais(arred(custo, 4))}).`);
  return {
    porUnidadeNaEmbalagem: arred(p.precoEmbalagem / fator, 4),
    economiaNaEmbalagem: arred(fator * p.precoUnidade - p.precoEmbalagem),
    lucroEmbalagem, lucroUnidade,
    margemEmbalagem: margem(lucroEmbalagem, p.precoEmbalagem),
    margemUnidade: margem(lucroUnidade, p.precoUnidade),
    alertas,
  };
}

/** Frases curtas para a tela (cadastro e importação). */
export function textoComparacao(p: {custo: number; fator: number; precoEmbalagem: number; precoUnidade: number; embalagem?: string}): string[] {
  if (!(p.precoEmbalagem > 0) || !(p.precoUnidade > 0) || !(p.fator > 0)) return [];
  const c = compararPrecos(p);
  const emb = (p.embalagem || 'embalagem').toUpperCase();
  const lucro = (v: number | null, m: number | null) => v === null ? '' : `; lucro ${reais(v)}${m === null ? '' : ` (${m.toLocaleString('pt-BR')}%)`}`;
  const linhas = [
    `${emb} com ${p.fator}: ${reais(p.precoEmbalagem)} = ${reais(arred(c.porUnidadeNaEmbalagem))} cada${lucro(c.lucroEmbalagem, c.margemEmbalagem)}.`,
    `Unidade avulsa: ${reais(p.precoUnidade)}${lucro(c.lucroUnidade, c.margemUnidade)}.`,
  ];
  if (c.economiaNaEmbalagem > 0) linhas.push(`Quem leva a ${emb} economiza ${reais(c.economiaNaEmbalagem)} frente a ${p.fator} soltas.`);
  return [...linhas, ...c.alertas.map(a => `⚠️ ${a}`)];
}

/** Embalagem provável pelo nome do item da nota (só para pré-preencher; o operador confirma). */
export function embalagemDoNome(nome: string): string {
  const n = ` ${nome.toUpperCase()} `;
  if (/\b(CX|CAIXA)\b/.test(n)) return 'CX';
  if (/\b(FD|FARDO)\b/.test(n)) return 'FD';
  if (/\b(PCT|PACOTE)\b/.test(n)) return 'PCT';
  if (/\bDISPLAY\b/.test(n)) return 'DISPLAY';
  if (/\bCARTEIRA\b/.test(n)) return 'CARTEIRA';
  return 'CX';
}

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
