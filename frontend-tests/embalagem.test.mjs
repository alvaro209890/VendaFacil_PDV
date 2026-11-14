import test from 'node:test';
import assert from 'node:assert/strict';
import { estoqueBalcao } from '../src/lib/embalagem.ts';
test('65 palheiros são 3 carteiras e 5 avulsos; fator 30 preserva 65', () => {
  assert.equal(estoqueBalcao({estoque:65,quantidade_por_embalagem:20,unidade_compra:'CARTEIRA',nome:'Palheiros'}), '3 carteiras e 5 avulsos (65 palheiros)');
  assert.equal(estoqueBalcao({estoque:65,quantidade_por_embalagem:30,unidade_compra:'CARTEIRA',nome:'Palheiros'}), '2 carteiras e 5 avulsos (65 palheiros)');
});
