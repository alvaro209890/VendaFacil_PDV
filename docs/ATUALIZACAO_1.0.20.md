# Alertas de estoque e leitor USB — 1.0.20

Codex, 14/11/2026. Solicitação do Álvaro durante o aceite no PC do James.

O card **Alertas Estoque** do dashboard abre **Produtos** com o filtro
**Somente produtos em alerta de estoque** marcado. A lista inclui todos os
produtos ativos com estoque menor ou igual ao mínimo, inclusive estoque zero,
usando a mesma regra do contador do dashboard. O filtro fica na URL, persiste
ao recarregar e pode ser desmarcado para voltar à lista completa. A lista
inferior do dashboard continua sendo apenas a prévia dos cinco primeiros.

O leitor conectado no James foi identificado no próprio Windows como
**DM13 USB POS KBW**, USB `VID_1EAB&PID_1D22`, com interfaces Keyboard e
POS HID Barcode scanner. Driver Microsoft, Status OK e ProblemCode 0.
O PDV já aceita teclado USB: foco na busca, código seguido de Enter, adição
ao carrinho e retorno do foco. F4 volta à busca. Não foi instalado driver de
terceiro nem enviada configuração de firmware de modelo desconhecido.

Álvaro confirmou no chat em 14/11 que, ao bipar no campo do PDV, o leitor
**adiciona o item ou abre o cadastro**. Isso confirma leitura física e envio do
terminador aceito pelo PDV; não foi necessário alterar firmware ou driver.

## Validação e artefatos

Build TypeScript/Vite e ESLint aprovados; 46 testes Node, 13 testes de foco e
teclado no navegador e 3 testes de embalagem/versão aprovados. Playwright CLI
conferiu o clique no card, seis alertas (mais que a prévia de cinco), produto
zerado, estoque exatamente no mínimo, exclusão de abastecido/inativo, remoção
do filtro, recarregamento e versão mobile. Imagens em `output/james/alerta-estoque-1.0.20.png`
e `alerta-estoque-mobile-1.0.20.png`. Aceite no binário com banco descartável:
20 requisições, 0 erros 5xx, fiado/PIX persistidos após reinício.

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| Exe | 39.731.957 | `FE64B494C06EAF1251C48125AD0F1D9A7EE8DF907B3A47DF8B8B53A7E0F8FD42` |
| Setup 1.0.20 | 40.018.348 | `DA0285AC5A09B2CDC1451541B4AA46B124EED9CB03C4188A2E5D64DA2569B274` |

O [aceite da instalação inicial 1.0.19](ACEITE_JAMES_1.0.19.md) registra
Point 403, SEFAZ 230 e o diagnóstico da Epson. Esta atualização não altera
essas integrações nem elimina os aceites físicos pendentes.

Sobre QR em sites: Álvaro testou uma nota e informou **não lê QR, só o código
da nota**; o aparelho não tem marca/modelo identificáveis na etiqueta. A API POS
do driver também não informou suporte a QR, EAN13 ou Code128; essa consulta não
substitui o teste no modo teclado, que já funcionou para código de barras.
QR permanece sem aceite. É necessário identificar o fabricante/configuração
ou usar hardware com leitura QR/2D confirmada. O modo teclado preenche o campo
selecionado em sites com o código lido; o site decide a consulta/abertura após
Enter. Não há navegação global ou captura de teclado fora do campo escolhido.
