# 🧾 Checklist para comercializar o VendaFácil PDV

Estado honesto do que falta para vender o sistema para lojistas. Dividido por
prioridade. O **código do produto** está bem encaminhado; a maior parte do que
falta é **negócio, distribuição e robustez de produção**, não funcionalidade.

## 🔴 Bloqueadores (sem isso não dá pra vender de verdade)

- [x] **Cobrança/bloqueio das lojas** — **decidido: MANUAL.** Você cobra por fora
      (PIX/boleto) e, no Painel, define a validade e bloqueia/exclui quem não
      pagar. Fluxo documentado em [`COBRANCA_MANUAL.md`](COBRANCA_MANUAL.md).
      (Cobrança automática fica como evolução futura — ver 🟡.)
- [ ] **Gerar e testar o .exe no Windows** — você faz isto na sua máquina
      Windows. Pipeline pronto e documentado em [`BUILD_WINDOWS.md`](BUILD_WINDOWS.md).
      *(Não dá para gerar no Linux: PyInstaller não faz cross-compile.)*
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
      Pago de produção). O fluxo está pronto no código, mas o happy-path só se
      confirma com aparelho.
- [ ] **NFC-e de ponta a ponta**: o lojista precisa de certificado A1, CSC e
      credenciamento na SEFAZ do estado. Testar homologação → produção de
      verdade com pelo menos um estado-alvo (MT/GO já estão no código).

## 🟡 Recomendado (qualidade e operação)

- [ ] **Monitoramento de erros** (ex.: Sentry) e uptime no backend.
- [x] **Testes automatizados** — **feito**: suíte pytest do PDV e do Painel
      (ver [`TESTES.md`](TESTES.md)).
- [x] **Manual do usuário** — **feito**: [`MANUAL.md`](MANUAL.md) (lojista + admin).
- [ ] **Onboarding/ativação** simples para a loja (passo a passo no 1º uso).
- [ ] **Atualização do .exe** (auto-update ou processo claro de nova versão).
- [ ] **Política de preços e planos** definida.
- [ ] **Canal de suporte** (WhatsApp/e-mail) e SLA.

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

---

### Resumo em uma frase
O **produto técnico** está quase lá; para **comercializar** faltam, na ordem:
(1) cobrança recorrente automática, (2) empacotar/assinar o .exe + instalador,
(3) parte legal (LGPD/Termos/CNPJ). O resto é robustez e operação que dá pra
evoluir com os primeiros clientes.
