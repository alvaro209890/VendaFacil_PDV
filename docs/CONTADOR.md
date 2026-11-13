# Fluxo com o contador (quem emite o quê)

## Quem faz o quê

Nesta entrega, todos os procedimentos fiscais permanecem em homologação.
Em **Fiscal**, informe também o CNAE principal da loja (sete dígitos).

| Conferência | Como acompanhar |
|---|---|
| Pré-requisitos | `scripts/fiscal_precheck.py`: presença e validade; B1–B5 impedem testes reais |
| Serviço da SEFAZ | O botão de consulta em Fiscal exibe 107 quando o serviço está em operação. O credenciamento é verificado à parte. |
| Quebra de numeração | Histórico de inutilizações em Fiscal, com faixa, cStat e protocolo |
| Pedido de inutilização | Somente faixa sem uso; não inutilizar contingência, nem número futuro |
| Arquivo fiscal | Pedidos/retornos de inutilização e XMLs das notas são guardados no SQLite local; a exportação ZIP mensal de notas não inclui as inutilizações |

Na rejeição normal, o número anterior é preservado no histórico; a próxima
emissão recebe o seguinte. O contador deve conferir a rejeição e orientar o
tratamento da faixa sem uso pela inutilização. Contingência rejeitada mantém
tratamento separado e não pode ser inutilizada.

Se a nota ficar pendente com cStat 539, confira a chave informada pela SEFAZ
no portal antes de orientar outra ação sobre a numeração da venda.

- **O sistema (loja) EMITE** a NFC-e automaticamente em cada venda, direto na
  SEFAZ-MT, e **guarda o XML autorizado**. O contador **não** emite as notas.
- **O contador APURA e DECLARA**: usa os XMLs para a escrita fiscal/SPED, calcula
  o imposto do Simples (**PGDAS-D**) e devolve a **guia (DAS)** para a loja pagar.

## O que entregar ao contador (todo mês)

1. **XMLs das notas de saída** (todas as NFC-e/NF-e do período).
   - Em **Relatórios → Fiscal (Simples)**, escolha o período e clique
     **"Exportar XMLs do período (ZIP)"** → baixa um `.zip` com todos os XMLs
     autorizados/cancelados. Entregue esse arquivo ao contador.
   - Para uma nota específica: **Vendas → abrir a venda → "Baixar XML"**.
2. **XMLs das compras (entrada)**: as NF-e dos fornecedores (a loja recebe por
   e-mail/da SEFAZ; também são usadas no **Importar XML** do estoque).
3. **Resumo do faturamento segregado** (para o PGDAS-D): os números da própria
   aba **Relatórios → Fiscal (Simples)** — separa receita com ICMS-ST/monofásico
   da tributada integral. Ver [`FISCAL_SIMPLES.md`](FISCAL_SIMPLES.md).

## O que o contador precisa configurar/fornecer (antes)

- **Classificação fiscal por produto**: NCM, CFOP, **CSOSN**, **CST PIS/COFINS** —
  preenchidos no cadastro do produto, com orientação do contador.
- **Regime** (Simples/CRT), **CNAE** e confirmação de obrigatoriedades (ex.: o
  vínculo de pagamento em MT — ver [`VINCULO_PAGAMENTO_MT.md`](VINCULO_PAGAMENTO_MT.md)).
- Apoio para **certificado A1, IE, CSC e credenciamento** na SEFAZ.
  IE ativa não é o mesmo que IE habilitada no autorizador de NFC-e (que tem
  cadastro separado por ambiente): ver [`IE_NFCE_AMBIENTES.md`](IE_NFCE_AMBIENTES.md).

## Resumo

A loja emite e guarda os XMLs; uma vez por mês exporta o **ZIP de XMLs** + o
**relatório Fiscal (Simples)** e manda ao contador, que apura o DAS. Simples assim.
