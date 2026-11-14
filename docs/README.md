# 📚 Documentação — VendaFácil PDV

Índice de toda a documentação, por público.

## 🏪 Implantação e operação na loja
- [IMPLANTACAO_MERCEARIA.md](IMPLANTACAO_MERCEARIA.md) — roteiro de instalação na loja, item a item, com evidência.
- [TREINAMENTO_OPERADOR.md](TREINAMENTO_OPERADOR.md) — treinamento de 20 minutos do operador de caixa.
- [SUPORTE_LOJA.md](SUPORTE_LOJA.md) — folha de 1 página para imprimir: luz, internet, nota pendente, diagnóstico.
- [SEGURANCA.md](SEGURANCA.md) — o que o PDV protege, riscos aceitos e o que fazer se o PC sair da loja.

## 📘 Uso do sistema (lojista)
- [**MANUAL.md**](MANUAL.md) — manual completo (lojista + administrador) e FAQ.
- [ESTOQUE_E_XML.md](ESTOQUE_E_XML.md) — estoque, entrada manual, importação de XML (NF-e) e venda de embalagem fechada com avulso.
- [**CAIXA_E_UNIDADE.md**](CAIXA_E_UNIDADE.md) — caixa e unidade com preços diferentes (1.0.16): cadastro, conta de preço, NF-e (custo real, dois códigos, "como a nota conta"), caixa, lucro, NFC-e e o caso real Kaiser.
- [CAIXA.md](CAIXA.md) — abertura/fechamento de caixa, sangria e suprimento.
- [RECIBO.md](RECIBO.md) — impressão de recibo/cupom na térmica (e bloco fiscal da NFC-e).
- [FISCAL_SIMPLES.md](FISCAL_SIMPLES.md) — CSOSN/CST por produto, XML fiscal e relatório para PGDAS-D.
- [CONTADOR.md](CONTADOR.md) — fluxo com o contador: quem emite, o que entregar (export de XMLs em ZIP) e o que ele configura.
- [VINCULO_PAGAMENTO_MT.md](VINCULO_PAGAMENTO_MT.md) — vínculo do pagamento eletrônico (cartão/PIX) na NFC-e — obrigatório em MT (Portaria 262/2023).
- [**LEGISLACAO_FISCAL_MT.md**](LEGISLACAO_FISCAL_MT.md) — revisão de legislação (2026-07, revisada em 2026-11-12): webservices/QR oficiais de MT, prazos de cancelamento (30 min/2 h), contingência, tPag (PIX 17/20, fiado), limites da NFC-e, CRT/Reforma Tributária (IBS/CBS 2027) e Lei 12.741.
- [TESTE_FISCAL_WINDOWS.md](TESTE_FISCAL_WINDOWS.md) — roteiro de teste fiscal de ponta a ponta no Windows (A1/CSC/CNPJ, homologação→produção, cartão e PIX).
- [IE_NFCE_AMBIENTES.md](IE_NFCE_AMBIENTES.md) — por que a IE ativa não basta: homologação x produção, o cStat 230 de 12/11 e o que pedir ao contador.
- [CONTINGENCIA_OFFLINE.md](CONTINGENCIA_OFFLINE.md) — contingência offline da NFC-e (tpEmis=9) e correções fiscais (QR Code 2.00, assinatura C14N, desconto, cNF, Lei 12.741) + checklist de homologação.
- [INTEGRACAO_STONE_TEF.md](INTEGRACAO_STONE_TEF.md) — como integrar Stone/outras maquininhas via TEF, esforço e estimativa de valor.
- [RESPONSAVEL_TECNICO.md](RESPONSAVEL_TECNICO.md) — grupo infRespTec/CSRT no XML (desligado por padrão; MT não exige).
- [MAQUININHA_MERCADOPAGO.md](MAQUININHA_MERCADOPAGO.md) — cartão e PIX pela maquininha (Point).
- [DIAGNOSTICO_MAQUININHA_POINT.md](DIAGNOSTICO_MAQUININHA_POINT.md) — diagnóstico do teste real neste PC e migração para Orders API.
- [BACKUP.md](BACKUP.md) — backup local (manual + automático) e restauração.
- Relatórios de vendas e Fiscal (Simples): ver [MANUAL.md › Relatórios](MANUAL.md#11-relatórios).

## 🛠️ Gerar e testar o .exe (Windows)
- [INSTALACAO_WINDOWS.md](INSTALACAO_WINDOWS.md) — instalar o PDV no computador do cliente.
- [BUILD_WINDOWS.md](BUILD_WINDOWS.md) — gerar o .exe + instalador (local ou via GitHub Actions).
- [EMPACOTAMENTO_EXE.md](EMPACOTAMENTO_EXE.md) — detalhes do empacotamento (PyInstaller).
- [TESTE_WINDOWS.md](TESTE_WINDOWS.md) — roteiro de teste antes de vender (automático contra o `.exe` + manual).
- [../CLAUDE.md](../CLAUDE.md) — instruções para um agente gerar o .exe (build automatizado).

## ☁️ Nuvem, licença e finanças
- [DEPLOY_E_PRODUCAO.md](DEPLOY_E_PRODUCAO.md) — arquitetura + deploy (Render + Supabase + Vercel).
- [LICENCA.md](LICENCA.md) — modelo de licença offline-first (contas liberadas, carência).
- [COBRANCA_MANUAL.md](COBRANCA_MANUAL.md) — cobrar e bloquear lojas manualmente pelo painel.
- [CUSTOS.md](CUSTOS.md) — quanto você paga (APIs/serviços) e a conta por loja.

## 🧑‍💻 Desenvolvimento
- [TESTES.md](TESTES.md) — como rodar as suítes de testes (pytest, Node, Playwright).
- [TESTES_NAVEGADOR.md](TESTES_NAVEGADOR.md) — testes de ponta a ponta no navegador (Playwright).
- [mobile-refactor.md](mobile-refactor.md) — notas da adaptação das telas para celular.
- [INTERFACE.md](INTERFACE.md) — calendário próprio, prévia de XML e janela de dados fiscais do produto.

## ⚖️ Jurídico (modelos — revisar com advogado)
- [legal/LEIA-ME.md](legal/LEIA-ME.md) — como usar os modelos e o que preencher.
- [legal/TERMOS_DE_USO.md](legal/TERMOS_DE_USO.md)
- [legal/POLITICA_DE_PRIVACIDADE.md](legal/POLITICA_DE_PRIVACIDADE.md)
- [legal/LGPD.md](legal/LGPD.md)

## ✅ Negócio
- [CHECKLIST_COMERCIALIZACAO.md](CHECKLIST_COMERCIALIZACAO.md) — o que está pronto e o que falta para vender.
