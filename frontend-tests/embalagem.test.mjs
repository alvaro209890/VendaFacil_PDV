import test from 'node:test';
import assert from 'node:assert/strict';
import { estoqueBalcao, compararPrecos, textoComparacao, embalagemDoNome } from '../src/lib/embalagem.ts';
import { itemCarrinho, linhaCarrinho, limiteCarrinho } from '../src/lib/carrinho.ts';
test('65 palheiros são 3 carteiras e 5 avulsos; fator 30 preserva 65', () => {
  assert.equal(estoqueBalcao({estoque:65,quantidade_por_embalagem:20,unidade_compra:'CARTEIRA',nome:'Palheiros'}), '3 carteiras e 5 avulsos (65 palheiros)');
  assert.equal(estoqueBalcao({estoque:65,quantidade_por_embalagem:30,unidade_compra:'CARTEIRA',nome:'Palheiros'}), '2 carteiras e 5 avulsos (65 palheiros)');
});
test('carrinho separa linhas e soma o estoque compartilhado', () => {
  const p={id:1,nome:'Palheiros',estoque:40,vende_por_unidade:1,quantidade_por_embalagem:20,preco_embalagem:20,preco_unidade:2};
  const caixa=itemCarrinho(p,'embalagem'); const un=itemCarrinho(p,'unidade',3);
  assert.notEqual(linhaCarrinho(caixa),linhaCarrinho(un));
  assert.equal(caixa.preco_venda+3*un.preco_venda,26);
  assert.equal(limiteCarrinho(caixa,[caixa,un]),1);
  assert.equal(limiteCarrinho(un,[caixa,un]),20);
});

const sem = (t) => t.replace(/\u00a0/g, ' ');
test('caixa de 15 a R$ 60 sai R$ 4 cada; avulsa R$ 5; economia R$ 15', () => {
  const c = compararPrecos({custo:3.5,fator:15,precoEmbalagem:60,precoUnidade:5,embalagem:'CX'});
  assert.equal(c.porUnidadeNaEmbalagem, 4);
  assert.equal(c.economiaNaEmbalagem, 15);
  assert.equal(c.lucroEmbalagem, 7.5);
  assert.equal(c.lucroUnidade, 1.5);
  assert.equal(c.margemUnidade, 30);
  assert.deepEqual(c.alertas, []);
  const linhas = textoComparacao({custo:3.5,fator:15,precoEmbalagem:60,precoUnidade:5,embalagem:'CX'}).map(sem);
  assert.equal(linhas[0], 'CX com 15: R$ 60,00 = R$ 4,00 cada; lucro R$ 7,50 (12,5%).');
  assert.equal(linhas[2], 'Quem leva a CX economiza R$ 15,00 frente a 15 soltas.');
});
test('Kaiser: custo 2,7606, CX 12 a R$ 40 e lata a R$ 3,80', () => {
  const c = compararPrecos({custo:2.7606,fator:12,precoEmbalagem:40,precoUnidade:3.8,embalagem:'CX'});
  assert.equal(c.porUnidadeNaEmbalagem, 3.3333);
  assert.equal(c.economiaNaEmbalagem, 5.6);
  assert.equal(c.lucroEmbalagem, 6.87);
  assert.equal(c.lucroUnidade, 1.04);
});
test('alerta caixa mais cara que as soltas e preço abaixo do custo', () => {
  const c = compararPrecos({custo:4,fator:12,precoEmbalagem:48,precoUnidade:3.8,embalagem:'CX'});
  assert.equal(c.alertas.length, 2);
  assert.match(sem(c.alertas[0]), /CX sai igual ou mais cara que 12 unidades soltas \(R\$ 45,60\)/);
  assert.match(sem(c.alertas[1]), /unidade abaixo do custo/);
  assert.deepEqual(textoComparacao({custo:1,fator:12,precoEmbalagem:0,precoUnidade:3,embalagem:'CX'}), []);
});
test('embalagem pelo nome da nota', () => {
  assert.equal(embalagemDoNome('CX 00050 KAISER LT 350ML'), 'CX');
  assert.equal(embalagemDoNome('FARDO AGUA 12X500'), 'FD');
  assert.equal(embalagemDoNome('Carteira palheiro'), 'CARTEIRA');
  assert.equal(embalagemDoNome('Refrigerante'), 'CX');
});
