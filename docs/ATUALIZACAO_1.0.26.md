# Atualização 1.0.26 — revisão visual do front

Claude, 15/11/2026. Pedido do Álvaro: analisar o front visualmente, corrigir
todo bug encontrado, documentar, publicar e atualizar o PC do James.

## Como foi a revisão

O sistema subiu com banco descartável (`e2e/servidor.cjs`) e dados de mercearia
inventados: 48 produtos (nomes longos, caixa + unidade, KG, sem preço, estoque
zerado), 4 clientes, vendas em todas as formas de pagamento, fiado e uma venda
cancelada. As 15 telas foram capturadas em 1366×768, 1024×768 e 390×844, mais os
fluxos com janela aberta (carrinho, pagamento, edição de produto, importação de
XML, detalhe de venda, recebimento de fiado). Cada captura passou por uma
checagem automática (texto fora da tela, rolagem horizontal, `NaN`/`undefined`,
erros de console) e foi olhada uma a uma.

## O que estava errado e foi corrigido

| # | Tela | Defeito | Correção |
|---|---|---|---|
| 1 | Todas | Dinheiro com ponto: `R$ 181.49`, `R$ 3.33 cada`, botões `50.00` | `moeda()` única em `src/lib/numeros.ts`: `R$ 1.234,56` em todas as telas |
| 2 | PDV | Um `0` solto aparecia em todo card de produto simples | `{p.vende_por_unidade && …}` renderizava o número 0; agora é booleano |
| 3 | PDV | Todo card dizia `GERAL`, mesmo com categoria cadastrada | A API de produtos não devolvia `categoria_nome`; `list_produtos` passou a trazer |
| 4 | Produtos | Estoque de caixa + unidade mostrava o nome do produto como unidade: `585 cx 00050 kaiser lt 350ml` | `47 caixas e 8 avulsos (572 UN no total)`; `CART` vira `carteiras` |
| 5 | Produtos | Tabela espremida: `R$` numa linha e o valor na outra, `+` e `Estoque` quebrados, nome cortado em 160 px | Colunas sem quebra, nome em até 2 linhas com o nome inteiro no `title`, subtítulo só quando há embalagem (`CX com 12 UN`) |
| 6 | Produtos | Com o formulário aberto a lista ficava ilegível e o formulário com ~200 px | Formulário com largura fixa (320 px); a lista rola de lado em vez de amassar |
| 7 | Produtos | Não havia como achar um produto numa lista de 234 itens | Campo **Buscar produto** (nome ou código de barras, da caixa ou da unidade) |
| 8 | Produtos (celular) | Card mais largo que a tela: nome cortado e botões fora | Card limitado à largura da tela, nome quebra linha |
| 9 | Importar XML | Ao marcar “em embalagem fechada” o custo caía para o da unidade, mas o **preço de venda sugerido** continuava o da caixa | O preço sugerido acompanha o custo (mesma margem). Preço digitado pelo operador não é tocado |
| 10 | Vendas | Venda cancelada aparecia igual às outras na lista | Etiqueta **Cancelada** e total riscado |
| 11 | Vendas, Dashboard | `Debito`, `Credito`, `Pix` sem acento | Rótulo único em `src/lib/rotulos.ts`: Débito, Crédito, PIX |
| 12 | Relatórios | Erro de chave duplicada no console quando o mesmo produto saía em caixa e avulso | Chave por posição |
| 13 | Relatórios, Backup (celular) | Valores e tabela fora da tela | Colunas com largura mínima zero; caminho da pasta quebra linha |
| 14 | Menu lateral | Em tela de 768 px de altura o mascote e o balão “Boas vendas!” cobriam os últimos itens do menu | Mascote só aparece em telas com 900 px ou mais de altura |
| 15 | PDV | Nome do item no carrinho cortado em uma linha (`CX 00050 KAISER LT 3…`) | Até 2 linhas |
| 16 | Vários | `1 item(ns)`, `4 cliente(s) cadastrado(s)`, `5 categoria(s)`; placeholder do desconto `0.00` | Singular/plural corretos; placeholder `0` |

Contas a Receber antigas guardam a descrição já gravada (`1 item(ns)`); só as
novas saem com o texto corrigido.

## O que não mudou, de propósito

- Campos de digitação continuam aceitando vírgula e ponto e mostram o número
  como foi salvo (`3.8`). Os testes de localização fixam esse comportamento.
- `+ Estoque` e `Ajustar` continuam usando a caixa de pergunta do navegador.
- O fator da caixa não é deduzido de `C/12` no nome: o operador informa.

## Arquivos

- Front: `src/lib/numeros.ts` (`moeda`, `decimal2`), `src/lib/rotulos.ts` (novo),
  `src/lib/embalagem.ts`, `src/App.tsx`, `src/pages/{PDV,Produtos,Vendas,Dashboard,Relatorios,Backup,Caixa,ContasReceber,Categorias,Clientes}.tsx`,
  `src/components/ReceberFiadoModal.tsx`.
- Backend: `backend/database.py` (`list_produtos` com `categoria_nome`; texto do fiado).
- Testes: `e2e/visual-1.0.26.spec.ts` (novo, 4 testes); textos em pt-BR em
  `carrinho`, `contagem-formato`, `decimais`, `embalagem`, `teclado`,
  `total-diario`; `frontend-tests/embalagem.test.mjs`.

## Validação

| Verificação | Resultado |
|---|---|
| Backend (`pytest`) | 557 aprovados, 9 de homologação desmarcados |
| Node (`frontend-tests`) | 46 aprovados |
| Navegador, suíte inteira com a NF-e 446817 real em banco temporário | **109 aprovados** (105 + 4 novos) |
| `tsc -b` e ESLint | limpos |
| Roteiro do `.exe` (`scripts/roteiro_exe.py`) | 45 requisições, 0 respostas 5xx, `/health` 1.0.26 |
| Navegador contra o `.exe` (`playwright.exe.config.ts`) | 11 aprovados |

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 46.267.375 | `EEF452116C4F502CB8ED51ED10F681681FFB294F8B0009A7355BEC2450183327` |
| `dist_installer/VendaFacilPDV-Setup-1.0.26.exe` | 46.353.793 | `84C52ACFC6E963FBC4CD8FA25A75201812D809D88F679E8A2AEB821EC7809C55` |

## Instalação no James

Instalada em **15/11/2026 às 16:22 (-04)**. Setup copiado por `scp`, hash
conferido no cliente, instalação silenciosa com **ExitCode 0**, processo criado
por WMI. Em sessão nova: `/health` **1.0.26**, `DisplayVersion` 1.0.26,
2 processos, exe com o mesmo SHA-256 do build, JS servido com a busca de
produtos. Instalador apagado da pasta Downloads do cliente.

Antes de instalar, o banco (`vendafacil.db` + WAL) foi copiado para
`%LOCALAPPDATA%\VendaFacilPDV\dados\backups\antes-1.0.26-20261115-162233`.
Contagens e impressão digital dos produtos (16 campos de cada um dos 234
cadastros, SHA-256) **iguais antes e depois**: 234 produtos, 233 ativos,
1 venda, 0 clientes.

As telas Produtos, PDV, Dashboard, Vendas e Relatórios do PDV real foram
abertas por túnel depois da instalação: nenhum valor com ponto, nenhum `0`
solto nos cards, nenhum erro de console.

O navegador que já estava aberto no caixa precisa de **F5** para carregar a
versão nova.
