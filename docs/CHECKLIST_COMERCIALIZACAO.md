# 🧾 Checklist para comercializar o VendaFácil PDV

Estado honesto do que falta para vender o sistema para lojistas. Dividido por
prioridade. **Atualizado em 12/11/2026 (versão 1.0.13, plano de produção
`plano_producao/`).** O **código do produto** está bem encaminhado; a maior parte do que
falta é **negócio, distribuição e robustez de produção**, não funcionalidade.

## 🔴 Bloqueadores (sem isso não dá pra vender de verdade)

- [x] **Cobrança/bloqueio das lojas** — **decidido: MANUAL.** Você cobra por fora
      (PIX/boleto) e, no Painel, define a validade e bloqueia/exclui quem não
      pagar. Fluxo documentado em [`COBRANCA_MANUAL.md`](COBRANCA_MANUAL.md).
      (Cobrança automática fica como evolução futura — ver 🟡.)
- [x] **Gerar e testar o .exe no Windows** — 1.0.13 gerada e validada em
      12/11/2026: roteiro automático contra o `.exe` (49 requisições, zero erro
      5xx, contingência, reimpressão, reinício e conciliação) e cupons 58/80 mm
      em PDF com QR decodificado. Ver [`BUILD_WINDOWS.md`](BUILD_WINDOWS.md) e
      [`TESTE_WINDOWS.md`](TESTE_WINDOWS.md).
- [ ] **Teste do instalador com elevação** (instalar → atualizar → desinstalar):
      script pronto (`scripts/teste_instalador.ps1`), falta rodar como
      administrador numa máquina descartável (bloqueio B8, 12/11/2026).
- [x] **Instalador amigável** — **pronto**: script Inno Setup em
      `installer/vendafacil.iss` + `installer/build_installer.bat`. Só compilar
      no Windows (ver [`BUILD_WINDOWS.md`](BUILD_WINDOWS.md)).
- [x] **Assinatura de código** — **decidido: NÃO vamos assinar** (não é
      essencial). O Windows mostra aviso do SmartScreen na 1ª execução →
      "Mais informações → Executar assim mesmo". Detalhe em `BUILD_WINDOWS.md`.
- [~] **Termos de Uso + Política de Privacidade + LGPD** — **modelos prontos** em
      [`legal/`](legal/). Falta **revisar com advogado** e preencher os campos.
- [ ] **Empresa/CNPJ** para faturar o serviço (só você pode providenciar).

## 🟠 Importante (antes de escalar / primeiros clientes pagos)

- [ ] **Plano pago no Render** (ou outro host). O free dorme, tem cold start e
      limite de horas; o keep-alive ajuda mas não é SLA. Para produção, suba pra
      um plano sempre-ativo.
- [ ] **Backup do banco** (Supabase): no free o backup é limitado — defina
      rotina de backup/exportação.
- [ ] **Domínio próprio** (ex.: `painel.seudominio.com.br`) em vez de
      `onrender.com`/`vercel.app` — passa confiança.
- [~] **Recuperação de senha do admin**: já dá para **trocar a senha** logado
      (botão no painel). Falta o fluxo "esqueci a senha" por e-mail (precisa de
      SMTP) e avisos de vencimento por e-mail.
- [x] **Proteção de login (anti brute-force)** — **feito**: rate limiting no
      login do admin e na validação de conta do PDV (bloqueia após 5 falhas).
- [ ] **Testar a maquininha com hardware real** (Point física + conta Mercado
      Pago de produção; bloqueios B5/B6, 12/11/2026). O fluxo está pronto no código, mas o happy-path só se
      confirma com aparelho.
- [x] **Relatório Fiscal (Simples)** — separa receita com ICMS-ST/monofásico da
      tributada integral para apoiar o PGDAS-D do contador.
- [~] **NFC-e de ponta a ponta** (SEFAZ-MT direto): emissão, contingência
      offline, conciliação, cancelamento e inutilização prontos e testados com
      simulador local (12/11/2026). **Falta** a homologação real: certificado A1
      da loja, CSC de homologação, credenciamento e dados da empresa (bloqueios
      B1–B4). Produção só com o contador de acordo.
- [x] **Vínculo do pagamento eletrônico (MT)** — NFC-e de cartão/PIX monta o
      grupo `<card>` (tpIntegra/CNPJ/tBand/cAut) com os dados da maquininha
      Mercado Pago. Obrigatório p/ mercearia (CNAE 4712-1) desde 01/07/2024.
      Falta só informar o **CNPJ da credenciadora** em Maquininha → Vínculo
      fiscal. Ver [`VINCULO_PAGAMENTO_MT.md`](VINCULO_PAGAMENTO_MT.md).

## 🟡 Recomendado (qualidade e operação)

- [ ] **Monitoramento de erros** (ex.: Sentry) e uptime no backend.
- [x] **Testes automatizados** — **feito**: suíte pytest do PDV e do Painel
      (ver [`TESTES.md`](TESTES.md)).
- [x] **Manual do usuário** — **feito**: [`MANUAL.md`](MANUAL.md) (lojista + admin).
- [x] **Onboarding/ativação** — roteiro de implantação em
      [`IMPLANTACAO_MERCEARIA.md`](IMPLANTACAO_MERCEARIA.md), treinamento em
      [`TREINAMENTO_OPERADOR.md`](TREINAMENTO_OPERADOR.md) e folha de suporte em
      [`SUPORTE_LOJA.md`](SUPORTE_LOJA.md) (12/11/2026).
- [ ] **Teste em papel** com impressora térmica, leitor e gaveta reais (B7).
- [~] **Atualização do .exe** — processo claro documentado (Setup novo por cima,
      backup automático, migração aditiva validada); auto-update segue fora.
- [ ] **Política de preços e planos** definida.
- [~] **Canal de suporte** — folha [`SUPORTE_LOJA.md`](SUPORTE_LOJA.md) e
      "Copiar diagnóstico" prontos; falta preencher o contato e definir SLA.

## ✅ Já pronto (não precisa fazer)

- PDV offline-first completo (produtos, vendas, fiado, dashboard, PIX, cartão).
- Maquininha Mercado Pago integrada ao checkout, à prova de offline.
- **Estoque + importação de XML de NF-e** e entrada manual com histórico.
- **Fechamento de caixa** (abertura, sangria/suprimento, conferência).
- **Relatórios de vendas** (período, formas de pagamento, top produtos, lucro).
- **Recibo térmico** (58/80mm) e **backup local** (manual + automático).
- Painel SaaS: criar/editar/bloquear/excluir contas + validade de licença +
  vendas sincronizadas + **financeiro** + troca de senha + rate limit.
- Licença offline-first com carência.
- Deploy: Render (API) + Vercel (painel) + Supabase (banco) documentado.
- Anti-hibernação no Render free. Suíte de testes (pytest).
- Robustez (12/11/2026): dinheiro em `Decimal`, venda numa transação, backup
  com `integrity_check` e restauração validada, modo consulta com banco
  corrompido, log rotativo, segunda instância e diagnóstico protegido.
- Testes em 12/11/2026: backend 460, painel 23, Node 36, E2E 91 no navegador.

---

### Resumo em uma frase
O **produto técnico** está quase lá; para **comercializar** faltam, na ordem:
(1) homologação fiscal real com os dados da loja (B1–B5), (2) teste do
instalador elevado e em papel (B7/B8), (3) parte legal (LGPD/Termos/CNPJ). O resto é robustez e operação que dá pra
evoluir com os primeiros clientes.
