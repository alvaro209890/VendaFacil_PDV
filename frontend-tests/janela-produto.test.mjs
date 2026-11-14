import test from 'node:test';
import assert from 'node:assert/strict';
import { faltaParaVender, pareceCodigo, itemCarrinho } from '../src/lib/carrinho.ts';

const base = { id: 7, nome: 'Refri', codigo_barras: '7891000888001', preco_venda: 8, preco_custo: 5, estoque: 2, vende_por_unidade: 0, quantidade_por_embalagem: 1, unidade: 'UN', unidade_compra: 'UN' };

test('com estoque e preço vende direto; zerado ou sem preço abre a janela', () => {
  assert.deepEqual(faltaParaVender(base, 'unidade', []), { semPreco: false, semEstoque: false });
  assert.deepEqual(faltaParaVender({ ...base, estoque: 0 }, 'unidade', []), { semPreco: false, semEstoque: true });
  assert.deepEqual(faltaParaVender({ ...base, preco_venda: 0 }, 'unidade', []), { semPreco: true, semEstoque: false });
});

test('conta o que já está no carrinho', () => {
  const noCarrinho = [itemCarrinho(base, 'unidade', 2)];
  assert.equal(faltaParaVender(base, 'unidade', noCarrinho).semEstoque, true);
});

test('caixa precisa do fator inteiro; unidade avulsa segue', () => {
  const cx = { ...base, vende_por_unidade: 1, unidade_compra: 'CX', quantidade_por_embalagem: 12, preco_embalagem: 40, preco_unidade: 3.8, estoque: 11 };
  assert.equal(faltaParaVender(cx, 'embalagem', []).semEstoque, true);
  assert.equal(faltaParaVender(cx, 'unidade', []).semEstoque, false);
});

test('código de barras x nome digitado', () => {
  assert.equal(pareceCodigo('7891000888001'), true);
  assert.equal(pareceCodigo(' 1234 '), true);
  assert.equal(pareceCodigo('123'), false);
  assert.equal(pareceCodigo('coca 2l'), false);
  assert.equal(pareceCodigo('AVULSO-1'), false);
});
