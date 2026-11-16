# Atualização 1.0.27 — carrinho vazio mais curto

Álvaro, 16/11/2026. Pedido: *"essa parte do carrinho tá muito longo, deixe mais
curto para baixo e já deixe online no do James"* — a coluna do carrinho, quando
está vazia, esticava até o fim da tela e deixava um bloco azul enorme sem
conteúdo.

## O que mudou

- **PDV, coluna do carrinho vazia**: o painel deixou de esticar na vertical.
  Com o carrinho vazio ele fica alinhado ao topo (`lg:self-start`) e do tamanho
  do conteúdo (cabeçalho + mascote + "Adicione produtos para começar a
  vender"), em vez de ocupar a altura inteira da janela.
- Espaçamento interno do estado vazio reduzido (`py-12` → `py-8`).
- **Com itens no carrinho nada muda**: o painel continua ocupando a altura toda
  e a lista rola por dentro, como já era — o total e o pagamento ficam presos
  embaixo, que é o que o operador precisa no balcão.

## Arquivos

- `src/pages/PDV.tsx`: constante `carrinhoVazio` e classe condicional
  `lg:self-start` na coluna direita; `py-8` no bloco vazio.
- `backend/version.py`, `installer/vendafacil.iss`, `scripts/roteiro_exe.py`:
  versão **1.0.27**.

## Validação

| Verificação | Resultado |
|---|---|
| `npm run build` (`tsc -b` + Vite) | limpo, `dist/assets/index-mqv8syu-.js` |
| `pytest backend/tests/test_embalagem_versao.py` | 3 aprovados |
| `pytest` (suíte do backend) | 557 aprovados, 9 de homologação desmarcados |
| `/health` no PC do James | **1.0.27** |
| Dados preservados (backups automáticos antes/depois) | 241 produtos, 3 vendas, 1 cliente, iguais |

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 46.267.129 | `8C359F36AA21EA990F07ACF62029C8A1C66E30E820A8C0B2AA86CBCD8F922191` |
| `dist_installer/VendaFacilPDV-Setup-1.0.27.exe` | 46.353.568 | `E0C635E19DB79A7ED1EAEE99B0427A09074EC64630AF4CD2E07808783CB50DCD` |

## Instalação no James

Instalada em **16/11/2026 às 17:15 (-04)**. Setup baixado por HTTP na tailnet,
hash conferido no cliente (`E0C635…0DCD`), instalação silenciosa com
**ExitCode 0**, `DisplayVersion` 1.0.27, processo criado por WMI (2 processos) e
porta 3020 respondendo. Backup automático da subida em
`dados\backups\vendafacil-auto-20261116-171530-618057.db`.

O navegador que já estava aberto no caixa precisa de **F5** para carregar a
versão nova.
