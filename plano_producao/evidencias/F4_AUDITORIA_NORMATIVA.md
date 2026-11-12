# Conferência fiscal — 12/11/2026

Conferência inicial reconciliada com a revisão independente por GPT-6 Luna
(esforço alto) e com as notas técnicas do Portal Nacional.

| Contrato | Código / prova | Resultado |
|---|---|---|
| `ide`: chave, `cNF`, modelo, série, número, fuso, emissão e ambiente | X01–X03/X09/X10 | AAMM e `cDV` seguem chave local. NFC-e offline inclui `dhCont` e `xJust`. |
| `ide`: `indFinal`, `indPres`, `indIntermed` | `F4_IND_FINAL_GREEN.txt`, `F4_IND_INTERMED_GREEN.txt` | A NF-e doméstica com não contribuinte informa consumidor final (E16a-40). Os dois modelos descrevem venda presencial direta. |
| `emit` e `dest`: CNPJ/CPF, IE, CRT e endereço | X01–X03/X10 e precheck | XSD valida estrutura. Dados e credenciamento dependem da loja. |
| `det/prod`, `imposto`, `total` e `transp` | `test_fiscal_xsd.py`, `test_fiscal_direto.py` | NCM, CFOP, ICMS Simples, CEST/ST, PIS/COFINS, desconto e total conferidos nos cenários cobertos. CRT 2/3 recusados. |
| `pag`: dinheiro, cartão, PIX estático 20/dinâmico 17 e fiado | `F4_FIADO_GREEN.txt`, X01/X02/X19 | IT 2024.002 indica 05 para o crediário. A proibição geral de 99 na YA02-50 foi desativada na NT 2020.006 v1.20. |
| Beneficiário/terminal no pagamento integrado | `test_vinculo_mt_campos.py` | P51:3 RED→GREEN; só dados reais da transação/configuração |
| Identificação e limite NFC-e MT | `test_limites_nfce_mt.py` | P49:limites inclusivos corrigidos; suíte412 |
| Prazo após autorização em UTC/MT | `test_prazo_cancelamento.py`, `test_autorizacao_dhrecbto.py` | P50:dhRecbto preservado, suíte405 |
| `infAdic` e DANFE | F4.19, `F4_DANFE_COMPLEMENTO_GREEN.txt` | `vTotTrib` e `infCpl` dependem do percentual da loja. O DANFE exibe os dados que constam do XML. |
| `infNFeSupl` e `Signature` | X06–X08 | Assinatura, adulteração e parâmetros do QR Code 2.00 verificados offline. |
| Contingência e retomada | M03/M04/M05/M12, `F4_TIMEOUT_217_GREEN.txt`, Portaria 177 art. 18 | A consulta 217 permite reenviar o XML assinado da reserva. O conflito 539 fica preservado para conferência. |
| Inutilização | X05/M09/X12, Portaria 177 art. 33 | Contrato SOAP/XSD, API autenticada, faixa reservada, histórico e tela. |
| Datas futuras IBS/CBS | Portal Nacional, NT2025.002/2026.005 | Documento anterior afirmava abril/2027 sem fonte primária suficiente; removida a data, mantido escopo CRT1/4 em2026 |

Fontes primárias consultadas:

- [Portaria177/2021 consolidada](https://app1.sefaz.mt.gov.br/Sistema/Legislacao/legislacaotribut.nsf/07fa81bed2760c6b84256710004d3940/14a777e454d23f9f0425874b006641f7): arts.3/8/18/23/33.
- [Portaria262/2023 consolidada até43/2025](https://app1.sefaz.mt.gov.br/Sistema/legislacao/legislacaotribut.nsf/07fa81bed2760c6b84256710004d3940/881a0dd680e02be704258a8c006fd007): art.1 e anexoII.
- [IT2024.002, tabela de pagamento](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?AspxAutoDetectCookieSupport=1&conteudo=6KiYymMwdyQ%3D).
- [MOC 7.0, Anexo I](https://www.confaz.fazenda.gov.br/legislacao/arquivo-manuais/moc7-anexo-i-leiaute-e-rv.pdf) e [NT 2019.001 v1.60](https://www.nfe.fazenda.gov.br/Portal/exibirArquivo.aspx?conteudo=pGfPgyEaNGg%3D), regra E16a-40.
- [NT 2020.006 v1.31](https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=%2FRFndRUpZJw%3D), histórico, §2.4 e regras do intermediador.
- [Notas técnicas vigentes do Portal Nacional](https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?AspxAutoDetectCookieSupport=1&tipoConteudo=04BIflQt1aY%3D): catálogo informa NT2025.002 v1.53 e NT2026.005.
- XSD oficial SVRS: URLs e hashes em `F4_X05_XSD_ORIGEM.txt`.

O escopo fiscal é o checkout presencial direto da mercearia. Venda por entrega,
telefone, site ou intermediador exige os indicadores e dados correspondentes.
As transmissões reais, credenciamento e classificação fiscal dos produtos da
loja dependem do bloco C e do contador. O precheck de retomada retornou saída 2
com B1–B5 em `F4_PRECHECK_REVALIDADO.txt`.
