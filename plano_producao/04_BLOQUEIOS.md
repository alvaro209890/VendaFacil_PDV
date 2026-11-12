# Bloqueios — o que depende de terceiro

**Lista fechada.** Só o que está aqui pode ser marcado `[!]`. Qualquer outra dificuldade é problema do agente e tem de ser resolvida.

Regra: verificar de verdade se o item falta, registrar a prova, e seguir para o próximo item. **Nunca simular sucesso, nunca preencher com dado fictício, nunca usar certificado que não seja o da loja.**

| # | Item | Dono | Como verificar que falta (sem expor valor) | Sem isso a loja não… | Trava |
|---|---|---|---|---|---|
| B1 | Certificado A1 (`.pfx`) da mercearia + senha, gravado no cofre do PDV | Lojista | `scripts/fiscal_precheck.py` (criado na Fase 4): presença, validade e CNPJ do titular | transmite nota | H01–H09 |
| B2 | CSC + ID do CSC de **homologação** | Lojista, no portal da SEFAZ-MT | mesmo script: presença | tem QR Code válido | H02–H08 |
| B3 | Credenciamento da loja para NFC-e na SEFAZ-MT | Lojista/contador | resposta do `statusServico`/autorização | tem nota autorizada | H02–H09 |
| B4 | Dados da empresa: CNPJ, IE, CNAE, endereço, regime (CRT) | Lojista | mesmo script: campos preenchidos e CNPJ igual ao do certificado | emite cupom com validade | H02–H09 |
| B5 | CNPJ da credenciadora + conta Mercado Pago de produção | Lojista | configuração da maquininha: presença | emite nota de cartão/PIX sem rejeição | H03, H04 |
| B6 | Maquininha Point física | Lojista | não há aparelho pareado neste PC | prova o fluxo de cartão no aparelho | parte física de H03/H04 |
| B7 | Impressora térmica, leitor de código de barras e gaveta reais | Lojista | não há impressora térmica instalada neste PC | prova o cupom em papel | só o teste físico (E07/E08 valem em PDF) |
| B8 | Elevação (UAC) para instalar neste PC | Álvaro (1 clique) | o Setup falha ou pede elevação sem sessão interativa | — | E04–E06 |
| B9 | Instalação, treinamento e 1ª NFC-e na loja | Álvaro + contador | é presencial | começa a operar | itens de implantação da Fase 7 |

## Registro de bloqueios ativos

O precheck e a execução isolada H01–H09 de e037473 registraram B1–B5. O credenciamento ainda precisa de comprovação. Evidências F4_PRECHECK_REAL.txt e F4_HOMOLOGACAO_BLOQUEADA.txt.

| Data | # | Item travado (ID) | Prova de que falta | O que pedir ao dono, em 1 frase |
|---|---|---|---|---|
| 2026-11-12 | B1 | H01–H09 / F4.23–24 | F4_PRECHECK_REAL.txt: certificado/senha ausentes; saída2 | Cadastrar o A1 da própria mercearia e sua senha no cofre da tela Fiscal |
| 2026-11-12 | B2 | H02–H09 | Precheck: CSC/ID ausentes | Cadastrar CSC e ID de homologação da loja |
| 2026-11-12 | B3 | H01–H09 | Precheck: credenciamento não comprovado por autorização real armazenada; nenhum A1 permite verificar agora | Contador conferir o credenciamento e acompanhar a primeira autorização em homologação |
| 2026-11-12 | B4 | H02–H09 | Precheck: campos da empresa ausentes e ambiente não cadastrado | Preencher dados fiscais reais, CNAE e homologação, com orientação do contador |
| 2026-11-12 | B5 | H03/H04 | Precheck: token Mercado Pago e adquirente ausentes | Configurar conta Point e CNPJ correto da credenciadora |

## Como destravar

Quando o dono entregar o item (por exemplo, o Álvaro cadastrar o certificado e o CSC na tela Fiscal do PDV), reenvie o goal. O agente relê o painel, roda o `scripts/fiscal_precheck.py` e executa os itens `[!]`.
