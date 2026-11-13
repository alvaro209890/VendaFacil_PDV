# Bloqueios �?" o que depende de terceiro

**Lista fechada.** S�� o que estǭ aqui pode ser marcado `[!]`. Qualquer outra dificuldade Ǹ problema do agente e tem de ser resolvida.

Regra: verificar de verdade se o item falta, registrar a prova, e seguir para o pr��ximo item. **Nunca simular sucesso, nunca preencher com dado fict��cio, nunca usar certificado que nǜo seja o da loja.**

| # | Item | Dono | Como verificar que falta (sem expor valor) | Sem isso a loja nǜo�?� | Trava |
|---|---|---|---|---|---|
| B1 | Certificado A1 (`.pfx`) da mercearia + senha, gravado no cofre do PDV | Lojista | `scripts/fiscal_precheck.py` (criado na Fase 4): presen��a, validade e CNPJ do titular | transmite nota | H01�?"H09 |
| B2 | CSC + ID do CSC de **homologa��ǜo** | Lojista, no portal da SEFAZ-MT | mesmo script: presen��a | tem QR Code vǭlido | H02�?"H08 |
| B3 | Credenciamento da loja para NFC-e na SEFAZ-MT — a IE precisa constar no autorizador de **cada** ambiente (homologação e produção); em 12/11 foi rejeitada com **cStat 230** só em homologação (contexto e texto para o contador em `docs/IE_NFCE_AMBIENTES.md`) | Lojista/contador | resposta do `statusServico`/autorização | tem nota autorizada | H02-H09; teste real (12/11/2026 o Álvaro decidiu que não haverá mais teste simulado) |
| B4 | Dados da empresa: CNPJ, IE, CNAE, endere��o, regime (CRT) | Lojista | mesmo script: campos preenchidos e CNPJ igual ao do certificado | emite cupom com validade | H02�?"H09 |
| B5 | CNPJ da credenciadora + conta Mercado Pago de produ��ǜo | Lojista | configura��ǜo da maquininha: presen��a | emite nota de cartǜo/PIX sem rejei��ǜo | H03, H04 |
| B6 | Maquininha Point f��sica | Lojista | nǜo hǭ aparelho pareado neste PC | prova o fluxo de cartǜo no aparelho | parte f��sica de H03/H04 |
| B7 | Impressora tǸrmica, leitor de c��digo de barras e gaveta reais | Lojista | nǜo hǭ impressora tǸrmica instalada neste PC | prova o cupom em papel | s�� o teste f��sico (E07/E08 valem em PDF) |
| B8 | Eleva��ǜo (UAC) para instalar neste PC | �?lvaro (1 clique) | o Setup falha ou pede eleva��ǜo sem sessǜo interativa | �?" | E04�?"E06 |
| B9 | Instala��ǜo, treinamento e 1�� NFC-e na loja | �?lvaro + contador | Ǹ presencial | come��a a operar | itens de implanta��ǜo da Fase 7 |

## Registro de bloqueios ativos

O precheck e a execu��ǜo isolada H01�?"H09 de e037473 registraram B1�?"B5. O credenciamento ainda precisa de comprova��ǜo. EvidǦncias F4_PRECHECK_REAL.txt e F4_HOMOLOGACAO_BLOQUEADA.txt.

| Data | # | Item travado (ID) | Prova de que falta | O que pedir ao dono, em 1 frase |
|---|---|---|---|---|
| 2026-11-12 | B1 | H01�?"H09 / F4.23�?"24 | F4_PRECHECK_REAL.txt: certificado/senha ausentes; sa��da2 | Cadastrar o A1 da pr��pria mercearia e sua senha no cofre da tela Fiscal |
| 2026-11-12 | B2 | H02�?"H09 | Precheck: CSC/ID ausentes | Cadastrar CSC e ID de homologa��ǜo da loja |
| 2026-11-12 | B3 | H01�?"H09 | Precheck: credenciamento nǜo comprovado por autoriza��ǜo real armazenada; nenhum A1 permite verificar agora | Contador conferir o credenciamento e acompanhar a primeira autoriza��ǜo em homologa��ǜo |
| 2026-11-12 | B4 | H02�?"H09 | Precheck: campos da empresa ausentes e ambiente nǜo cadastrado | Preencher dados fiscais reais, CNAE e homologa��ǜo, com orienta��ǜo do contador |
| 2026-11-12 | B5 | H03/H04 | Precheck: token Mercado Pago e adquirente ausentes | Configurar conta Point e CNPJ correto da credenciadora |

| 2026-11-12 | B8 | E04�?"E06 / F6.11 | F6_INSTALADOR_B8.txt: sessǜo sem eleva��ǜo, script retornou 2 | Executar scripts/teste_instalador.ps1 em PowerShell elevado numa instala��ǜo descartǭvel |

| 2026-11-12 | B3 | H01�?"H09 | Status 107 OK e XML aceito pelo autorizador depois das corre����es de TLS, ASCII, assinatura e digest; a autoriza��ǜo para em cStat **230 �?" IE do emitente nǜo cadastrada** no ambiente de **homologa��ǜo**. A IE 13.876.189-2 estǭ ATIVA no CCE (emitido 12/11/2026), mas ausente no cadastro do autorizador de homologa��ǜo. | Contador pedir �� SEFAZ-MT a atualiza��ǜo do cadastro do contribuinte no ambiente de homologa��ǜo |

## Como destravar

Quando o dono entregar o item (por exemplo, o �?lvaro cadastrar o certificado e o CSC na tela Fiscal do PDV), reenvie o goal. O agente relǦ o painel, roda o `scripts/fiscal_precheck.py` e executa os itens `[!]`.

