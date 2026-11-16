# Atualização 1.0.28 — formulário de produto não vaza mais do cartão

Álvaro, 16/11/2026. Pedido: *"lá onde edita os produtos, nos dados dele, no canto
direito tá saindo do local correto e ficando vazado pra baixo. Corrige também"*.

## O que estava errado

O formulário de **Novo/Editar Produto** (`src/pages/Produtos.tsx`) é a coluna
direita da tela. O cartão não tinha rolagem própria: com o cadastro completo
("Caixa e unidade", dois preços, resumo de lucro) o conteúdo passa de **1.500 px**
de altura e vazava para fora da borda do cartão, empurrando a página para baixo.

Medido no navegador (1366×768, dado de teste):

| | antes | depois |
|---|---|---|
| altura do cartão | 720 px | 720 px |
| conteúdo dentro do cartão | **1.517 px** (sem rolagem) | 1.533 px **com rolagem** |
| rolagem da página (`main`) | 1.542 px (vazava) | **768 px** (= a tela) |

## Correção

- Cartão do formulário: `lg:min-h-0 lg:overflow-y-auto custom-scrollbar` — o
  conteúdo rola **dentro** do cartão e a página não cresce mais.
- No celular nada muda: em uma coluna o formulário continua crescendo normal.

## Arquivos

- `src/pages/Produtos.tsx`: classes do cartão do formulário.
- `e2e/layout-produtos.spec.ts` (novo): mede em 1366×768 e 1366×640 que o
  conteúdo rola no cartão (`overflow-y: auto`, `scrollHeight > clientHeight`) e
  que a página não passa da tela.
- `backend/version.py`, `installer/vendafacil.iss`, `scripts/roteiro_exe.py`:
  versão **1.0.28**.

## Validação

| Verificação | Resultado |
|---|---|
| `npm run build` (`tsc -b` + Vite) | limpo, `dist/assets/index-CUqfe0Nb.js` |
| `npx playwright test e2e/layout-produtos.spec.ts` | **2 aprovados** (768 e 640 px) |
| `pytest backend/tests/test_embalagem_versao.py` | 3 aprovados |
| Capturas antes/depois | `output/captura-editar-{768,640}.png` |

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 46.267.416 | `B198D7941F60F26AE5164070B51FD9B77E06F27C6E22C2B99F820F2B675097B3` |
| `dist_installer/VendaFacilPDV-Setup-1.0.28.exe` | 46.355.181 | `25F6D55147EA275D05E65549A78284CAD752C34A5614395540C36D1C82189202` |

## Instalação no James

Instalada em **16/11/2026** (mesmo dia, depois da 1.0.27), hash conferido nos dois
lados, instalação silenciosa, processo criado por WMI e `/health` **1.0.28**.
O navegador do caixa precisa de **F5**.
