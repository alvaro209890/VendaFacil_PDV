# 🧾 Checklist para comercializar o VendaFácil PDV

Estado honesto do que falta para vender o sistema para lojistas. Dividido por
prioridade. O **código do produto** está bem encaminhado; a maior parte do que
falta é **negócio, distribuição e robustez de produção**, não funcionalidade.

## 🔴 Bloqueadores (sem isso não dá pra vender de verdade)

- [ ] **Cobrança recorrente das lojas (mensalidade).** Hoje a licença é
      **manual**: você define a validade no painel e bloqueia na mão. Para
      comercializar de verdade, precisa de pagamento recorrente (PIX
      recorrente / cartão via Mercado Pago/Stripe/Asaas) que **ative e bloqueie
      a licença automaticamente** ao pagar/vencer.
- [ ] **Gerar e testar o .exe no Windows** (Node 20+ → `npm run build` →
      PyInstaller). Ainda não foi empacotado/testado numa máquina Windows real.
- [ ] **Instalador amigável** para o lojista (Inno Setup / MSI), não só o .exe
      solto. Com atalho, ícone, e idealmente atualização.
- [ ] **Assinatura de código (code signing)** do executável. Sem isso, o
      Windows/SmartScreen mostra "app não confiável" e assusta o cliente.
      (Certificado pago, ~US$ 100–300/ano.)
- [ ] **Termos de Uso + Política de Privacidade + LGPD.** Você guarda dados de
      lojas e de vendas (e CPF em notas). Precisa de base legal, política
      publicada e tratamento adequado dos dados.
- [ ] **Empresa/CNPJ** para faturar o serviço e emitir nota da mensalidade.

## 🟠 Importante (antes de escalar / primeiros clientes pagos)

- [ ] **Plano pago no Render** (ou outro host). O free dorme, tem cold start e
      limite de horas; o keep-alive ajuda mas não é SLA. Para produção, suba pra
      um plano sempre-ativo.
- [ ] **Backup do banco** (Supabase): no free o backup é limitado — defina
      rotina de backup/exportação.
- [ ] **Domínio próprio** (ex.: `painel.seudominio.com.br`) em vez de
      `onrender.com`/`vercel.app` — passa confiança.
- [ ] **Recuperação de senha do admin do painel** (hoje não existe; se esquecer,
      trava). E e-mail transacional para isso e para avisos de vencimento.
- [ ] **Proteção de login**: rate limiting / bloqueio por tentativas no login
      do admin e na validação de conta (anti brute-force).
- [ ] **Testar a maquininha com hardware real** (Point física + conta Mercado
      Pago de produção). O fluxo está pronto no código, mas o happy-path só se
      confirma com aparelho.
- [ ] **NFC-e de ponta a ponta**: o lojista precisa de certificado A1, CSC e
      credenciamento na SEFAZ do estado. Testar homologação → produção de
      verdade com pelo menos um estado-alvo (MT/GO já estão no código).

## 🟡 Recomendado (qualidade e operação)

- [ ] **Monitoramento de erros** (ex.: Sentry) e uptime no backend.
- [ ] **Testes automatizados** (não há suíte hoje) — ao menos do checkout,
      licença e sync.
- [ ] **Manual do usuário** (lojista): instalar, configurar impressora,
      maquininha, emitir nota.
- [ ] **Onboarding/ativação** simples para a loja (passo a passo no 1º uso).
- [ ] **Atualização do .exe** (auto-update ou processo claro de nova versão).
- [ ] **Política de preços e planos** definida.
- [ ] **Canal de suporte** (WhatsApp/e-mail) e SLA.

## ✅ Já pronto (não precisa fazer)

- PDV offline-first completo (produtos, vendas, fiado, dashboard, PIX, cartão).
- Maquininha Mercado Pago integrada ao checkout, à prova de offline.
- Painel SaaS: criar/editar/bloquear/excluir contas + validade de licença +
  vendas sincronizadas.
- Licença offline-first com carência.
- Deploy: Render (API) + Vercel (painel) + Supabase (banco) documentado.
- Anti-hibernação no Render free.

---

### Resumo em uma frase
O **produto técnico** está quase lá; para **comercializar** faltam, na ordem:
(1) cobrança recorrente automática, (2) empacotar/assinar o .exe + instalador,
(3) parte legal (LGPD/Termos/CNPJ). O resto é robustez e operação que dá pra
evoluir com os primeiros clientes.
