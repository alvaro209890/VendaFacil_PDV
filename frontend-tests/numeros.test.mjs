// Cobertura de caracterização do parser já verde nos fluxos reais de caixa/fiado/PDV.
import test from 'node:test';
import assert from 'node:assert/strict';
import { lerNumeroPtBr } from '../src/lib/numeros.ts';

for (const [texto, casas, esperado] of [
  ['1,5', 2, 1.5],
  ['1.5', 2, 1.5],
  ['0,50', 2, 0.5],
  ['0.50', 2, 0.5],
  [' 1,50 ', 2, 1.5],
  [',5', 2, 0.5],
  ['.5', 2, 0.5],
  ['0', 2, 0],
  ['0,', 2, 0],
  ['1,', 2, 1],
  ['0,125', 3, 0.125],
  ['0,0001', undefined, 0.0001],
  ['', 2, null],
  [' ', 2, null],
  ['1,005', 2, null],
  ['0,0001', 3, null],
  ['1,2,3', 2, null],
  ['1.2.3', 2, null],
  ['12abc', 2, null],
  ['Infinity', undefined, null],
  ['1e3', undefined, null],
  ['-1', 2, null],
]) {
  test(`parser ${JSON.stringify(texto)} casas=${casas}`, () => {
    assert.equal(lerNumeroPtBr(texto, casas), esperado);
  });
}
