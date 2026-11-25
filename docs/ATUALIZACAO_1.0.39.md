# Atualização 1.0.39 — extrato de compras do cliente (o que comprou, que dia)

Álvaro, 25/11/2026. Pedido: *"Deve ter como exportar um relatório em PDV do que a pessoa
comprou, que dia e etc, e ver no PDV também — atualize lá e já deixe online lá no sistema,
documente tudo e deixe no main do GitHub"*.

## O que mudou

Antes, o fiado guardava tudo (venda, itens e conta a receber amarrados por `venda_id`), mas a
consulta era cega: a tela de Contas a Receber mostrava só o valor e o nome, e achar "o que o
fulano levou" exigia abrir Vendas e paginar de 50 em 50, sem filtro por cliente.

Agora existe o **extrato por cliente**, com itens, período e exportação.

### Backend

- `database.extrato_cliente(user_id, cliente_id, inicio, fim)` — devolve o cliente, um resumo
  (compras, total comprado, total fiado, fiado em aberto, primeira e última compra) e a lista de
  compras com os itens de cada uma, a conta fiada vinculada e a última NFC-e. O filtro de data usa
  o **dia comercial de MT** (`date(criado_em, '-4 hours')`), o mesmo critério do resumo do dia.
- `GET /api/clientes/{id}/extrato?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` — rota autenticada, valida as
  datas (400 para formato inválido ou período invertido) e devolve 404 para cliente de outra conta.
- `GET /api/contas-receber/{id}` passou a trazer `itens` e a `venda` completa, para o atalho
  "ver o que foi comprado" direto da conta fiada.

### Frontend

- Componente novo `src/components/ExtratoCliente.tsx` (modal): filtros **Hoje / 7 dias / 30 dias /
  Tudo** ou duas datas, cartões de resumo, lista das compras com itens, total e situação do fiado,
  e os botões **Baixar PDF** e **Baixar CSV (Excel)**.
- **Contas a Receber**: botão **Extrato** ao lado do nome do cliente e o atalho **Ver o que foi
  comprado** em cada conta (abre os itens daquela venda com opção de abrir o extrato inteiro).
- **Clientes**: botão **Extrato** em cada cliente.
- `src/lib/extrato-export.ts` — exportação sem dependência nova:
  - **PDF A4** gerado no próprio navegador (PDF 1.4, fonte Courier base-14, paginação automática,
    cabeçalho com razão social/CNPJ/IE/endereço da loja). Não precisa de internet, impressora,
    LibreOffice ou biblioteca externa; o arquivo cai em Downloads.
  - **CSV** com `;` e vírgula decimal, BOM UTF-8 (o Excel abre com acentos), uma linha por item.

## Validação

| Verificação | Resultado |
|---|---|
| `npm run build` (`tsc -b && vite build`) | limpo — bundle `index-2ersqfMU.js` no build de dev |
| `pytest` backend completo | **579 passed**, 9 deselected (2 min 11 s) |
| Testes novos `tests/test_extrato_cliente.py` | 5 passed (resumo, itens, filtro de data, data inválida, isolamento por conta, conta com itens) |
| E2E `e2e/extrato-cliente.spec.ts` | 1 passed — abre Contas a Receber, clica em Extrato, confere itens/resumo e baixa o PDF (`%PDF`, > 1 KB) |
| PDF gerado (amostra com acentos, fiado e nota) | A4 595×842 pt, 1 página, texto conferido em `pdftotext` — acentos corretos |
| PyInstaller | 1.0.39, `dist_exe/VendaFacilPDV.exe` — 46.299.554 bytes |
| Inno Setup | `dist_installer/VendaFacilPDV-Setup-1.0.39.exe` — 46.384.695 bytes |
| Setup no PC do James | SHA-256 igual nos dois lados, `ExitCode 0`, `PendingFileRenameOperations` vazio |
| `/health` no caixa | `{"status":"ok","app":"vendafacil-pdv","version":"1.0.39"}` |
| `DisplayVersion` | 1.0.39 |
| Processos / porta | 2 processos PyInstaller, porta 3020 `True` |
| Bundle servido | `index-DHIbbegN.js` — contém `Extrato de compras`, `Baixar CSV (Excel)` e `/extrato` |
| Janelas do caixa | 1 janela com `--kiosk-printing` (a duplicada da reinstalação foi fechada) |
| Validação visual no caixa | modal aberto por CDP no Edge do James, com dados reais: 2 compras, R$ 89,50, itens e botões PDF/CSV |

## Como usar no balcão

1. **Contas a Receber** → **Extrato** (ao lado do nome) ou **Ver o que foi comprado** na conta.
2. Escolha o período nos atalhos ou nas datas → **Filtrar**.
3. **Baixar PDF** (comprovante/relatório para imprimir ou enviar) ou **Baixar CSV** (Excel).
4. Na tela **Clientes**, o botão **Extrato** abre o mesmo histórico, mesmo sem fiado aberto.

O extrato mostra **todas** as compras do cliente — fiado, dinheiro, PIX e cartão —, cada uma com
data/hora, forma de pagamento, itens e situação. Vendas canceladas aparecem marcadas e não entram
no total.

## Arquivos tocados

- `backend/database.py` — `extrato_cliente`.
- `backend/clientes.py` — rota `GET /{cliente_id}/extrato` + validação de datas.
- `backend/contas_receber.py` — detalhe da conta com `itens`/`venda`.
- `src/lib/api.ts` — tipos e `obterExtratoCliente`.
- `src/lib/extrato-export.ts` — novo (PDF e CSV).
- `src/components/ExtratoCliente.tsx` — novo (modal).
- `src/pages/ContasReceber.tsx`, `src/pages/Clientes.tsx` — botões e modais.
- `backend/tests/test_extrato_cliente.py` — novo.
- `e2e/extrato-cliente.spec.ts` — novo.
- `backend/version.py`, `installer/vendafacil.iss`, `scripts/roteiro_exe.py` — 1.0.39.
- `docs/MANUAL.md`, `README.md`, `docs/README.md` — textos e índice.

## Hashes

| Arquivo | Bytes | SHA-256 |
|---|---|---|
| `dist_exe/VendaFacilPDV.exe` | 46.299.554 | `56B06086A25327327011CD33460ABBD7324C4402E95DD68342A98DC83CEF4F09` |
| `dist_installer/VendaFacilPDV-Setup-1.0.39.exe` | 46.384.695 | `698DA0115BA5821BB503DBCDDBF8D9D5EFCC4BB37F3E2ACAF82961048203F732` |

## Observações

- O PDF é montado no navegador de propósito: adicionar `reportlab`/`fpdf` ao PyInstaller aumentaria
  o executável e criaria dependência nova para um relatório simples. O gerador usa as fontes
  base-14 do padrão PDF (Courier), então não embute arquivo de fonte e mantém o arquivo pequeno.
- Números de coluna/decimais seguem o padrão do app (vírgula decimal, `R$`).
- O extrato **não** altera nada no banco: é leitura pura.
