# 📚 Documentação — VendaFácil PDV

Índice de toda a documentação, por público.

## 📘 Uso do sistema (lojista)
- [**MANUAL.md**](MANUAL.md) — manual completo (lojista + administrador) e FAQ.
- [ESTOQUE_E_XML.md](ESTOQUE_E_XML.md) — estoque, entrada manual e importação de XML (NF-e).
- [CAIXA.md](CAIXA.md) — abertura/fechamento de caixa, sangria e suprimento.
- [RECIBO.md](RECIBO.md) — impressão de recibo/cupom na térmica (e bloco fiscal da NFC-e).
- [FISCAL_SIMPLES.md](FISCAL_SIMPLES.md) — CSOSN/CST por produto, XML fiscal e relatório para PGDAS-D.
- [VINCULO_PAGAMENTO_MT.md](VINCULO_PAGAMENTO_MT.md) — vínculo do pagamento eletrônico (cartão/PIX) na NFC-e — obrigatório em MT (Portaria 262/2023).
- [TESTE_FISCAL_WINDOWS.md](TESTE_FISCAL_WINDOWS.md) — roteiro de teste fiscal de ponta a ponta no Windows (A1/CSC/CNPJ, homologação→produção, cartão e PIX).
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
- [TESTE_WINDOWS.md](TESTE_WINDOWS.md) — roteiro de teste manual antes de vender.
- [../CLAUDE.md](../CLAUDE.md) — instruções para um agente gerar o .exe (build automatizado).

## ☁️ Nuvem, licença e finanças
- [DEPLOY_E_PRODUCAO.md](DEPLOY_E_PRODUCAO.md) — arquitetura + deploy (Render + Supabase + Vercel).
- [LICENCA.md](LICENCA.md) — modelo de licença offline-first (contas liberadas, carência).
- [COBRANCA_MANUAL.md](COBRANCA_MANUAL.md) — cobrar e bloquear lojas manualmente pelo painel.
- [CUSTOS.md](CUSTOS.md) — quanto você paga (APIs/serviços) e a conta por loja.

## 🧑‍💻 Desenvolvimento
- [TESTES.md](TESTES.md) — como rodar a suíte de testes (pytest).

## ⚖️ Jurídico (modelos — revisar com advogado)
- [legal/LEIA-ME.md](legal/LEIA-ME.md) — como usar os modelos e o que preencher.
- [legal/TERMOS_DE_USO.md](legal/TERMOS_DE_USO.md)
- [legal/POLITICA_DE_PRIVACIDADE.md](legal/POLITICA_DE_PRIVACIDADE.md)
- [legal/LGPD.md](legal/LGPD.md)

## ✅ Negócio
- [CHECKLIST_COMERCIALIZACAO.md](CHECKLIST_COMERCIALIZACAO.md) — o que está pronto e o que falta para vender.
