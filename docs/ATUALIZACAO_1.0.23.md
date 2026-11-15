# Atualização 1.0.23 — tela de importação de XML mais simples

Data: 14/11/2026. Pedido do Álvaro depois de abrir a prévia no PC do James:
*"a tela de cadastro por XML está muito confusa"*. Conferido com o XML real da
**NF 9294 (N. Bevilacqua Junior, 15 linhas)** e com a **NF-e 446817 (Kaiser,
600 UN)**.

## O que confundia (1.0.22)

- Tabela de 9 colunas técnicas (*Un. venda, Un. compra, Qtd XML, Qtd/emb.,
  Entra, Custo R$, Venda R$*) e cada item ocupando meia tela.
- A mesma pergunta duas vezes: rádio *Caixa fechada e unidade* **e** checkbox
  *Vende a embalagem fechada e também a unidade*.
- Frases sem informação (*5 UN viram 5 UN*), custo com 4 casas, aviso de `UN1`
  em todo item.
- Produto repetido na nota (mesmo código, duas linhas) aparecia como dois
  *Criar produto*.

## O que mudou

- **Um cartão por produto**: nome, selo *NOVO* / *JÁ CADASTRADO*, a linha da
  nota com desconto/frete por extenso e quatro campos: *Na nota*, *Entra no
  estoque*, *Custo por unidade*, *Preço de venda* com **lucro %** ao lado.
- **“Como vende?”** uma vez só, em três botões. Item simples (nota em UN, sem
  sinal de embalagem) deixa a pergunta recolhida em *“Vende em caixa também?
  Trocar”*. Itens com cara de caixa/fardo ficam **amarelos** e um aviso no topo
  diz quantos são.
- **Margem dos novos** + **Aplicar aos novos**: mesmo lucro para todos.
- **Linhas repetidas juntadas** (mesmo código, unidade e produto): quantidades
  somadas, custo médio ponderado, texto *“veio em 2 linhas na nota (1 + 7)”*.
- Rodapé com **custo total** da entrada.
- Escolher *Caixa fechada e unidade* pelo rádio agora também distribui os
  códigos de barras (caixa = `cEAN`, unidade = `cEANTrib`), como o checkbox fazia.
- A lógica de quantidade, custo, validação e o payload enviado ao backend não
  mudaram. Backend sem alteração além da versão.

## Provas

| Etapa | Resultado |
|---|---|
| `tsc -b` e ESLint | limpos |
| Backend (`pytest`) | **547 passed**, 9 deselected |
| Navegador (`npx playwright test`, `VF_XML_REAL` = NF-e 446817) | **101 passed**, inclui o novo teste de linhas repetidas |
| Roteiro do `.exe` (`scripts/roteiro_exe.py --chromium --cupons …`) | 49 requisições, **0 respostas 5xx** |
| Prévia da NF 9294 real | 15 linhas → **13 cartões**, custo total R$ 1.216,17 (= vNF) |

O roteiro do `.exe` estava quebrado desde a 1.0.21: `getByLabel('Quantidade de
Açúcar de teste')` passou a achar também os botões *Diminuir/Aumentar quantidade
de …*. Corrigido com `exact: true` em `scripts/roteiro_exe_chromium.mjs`.

## Artefatos

| Arquivo | Bytes | SHA-256 |
|---|---|---|
| `dist_installer/VendaFacilPDV-Setup-1.0.23.exe` | 40.025.121 | `1BC3AF12E6B643BCACC6CE5112ED48C777FA8D987AC45B65783E0E5514ABC1DE` |
| `dist_exe/VendaFacilPDV.exe` | 39.737.884 | `A59559AD17154B8C25B83EC928A119AAD9F6327DA329FE8BBC9FC16ED8327D4F` |

## Instalação no James (14/11/2026, ~23:11 -04)

Setup copiado por `scp`, hash conferido no PC da loja, app fechado, instalação
silenciosa (`/VERYSILENT … /TASKS="desktopicon"`) com **ExitCode 0**, subida pelo
WMI (`Win32_Process Create`). Em sessão nova: `/health` → `1.0.23`, 2 processos,
`DisplayVersion` 1.0.23, hash do exe igual ao do build, conta `james` ativa,
banco preservado e backup automático novo (29 no total). Instalador apagado da
pasta Downloads do cliente depois da conferência.
