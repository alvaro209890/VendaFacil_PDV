import test from 'node:test';
import assert from 'node:assert/strict';
import { estoqueBalcao } from '../src/lib/embalagem.ts';
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
