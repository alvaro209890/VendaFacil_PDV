# F1.4 — revisão e provas de totais fiscais

Revisor independente Gemini high `deleg_4caf6711`: aprovado, sem security_concerns, logic_errors ou sugestões. Revisou os dois arquivos staged; não acessou SEFAZ nem certificado real.

Provas do orquestrador:
- `F1_4_RED_rateio.txt`: cestas de 7/13 itens de R$0,01 produziam parcela negativa no último item.
- `F1_4_RED_xml.txt`: total da NFC-e divergente do checkout em preço2,675/desconto0,005.
- `F1_4_RED_impostos.txt`: PIS/COFINS/IBPT com2,675 arredondado para2,67.
- `F1_4_GREEN.txt`: 101 passed; `F1_4_PAINEL.txt`: 7 passed.
- `F1_4_FISCAL_EXISTENTE.txt`: 49 passed nos dois módulos fiscais originais.

Correção: maiores restos em centavos transitórios para o rateio, cálculos e somas fiscais em Decimal com HALF_UP. Limites: nenhuma mudança no schema REAL, provedor, ambiente, assinatura, XSD ou configuração da loja. A homologação real ainda não foi realizada.

Commit de código/testes/manual: `2a9b689`.
