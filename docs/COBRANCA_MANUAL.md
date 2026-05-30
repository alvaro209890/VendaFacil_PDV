# 💰 Cobrança e bloqueio manual das lojas

O controle de licença do VendaFácil é **manual** pelo Painel admin — você cobra
o lojista por fora (PIX, boleto, etc.) e, no painel, define até quando a licença
vale e bloqueia quem não pagar. Não há cobrança automática (decisão de projeto;
fica como evolução futura em [`CHECKLIST_COMERCIALIZACAO.md`](CHECKLIST_COMERCIALIZACAO.md)).

## Como funciona a licença

Cada loja tem uma conta no Painel com:
- **Ativo / Bloqueada** — liga/desliga o acesso.
- **Licença válida até** — data de expiração.

No PDV (offline-first): quando há internet, o `.exe` revalida a licença no Painel
e guarda o resultado. Se a conta estiver **bloqueada** ou a **licença vencida**,
na próxima revalidação online o PDV trava. Sem internet, segue por um período de
**carência** (padrão 30 dias) e depois trava.

## Fluxo mensal (sugestão)

1. **Cobre o lojista** pelo canal que preferir (PIX/boleto), fora do sistema.
2. Ao confirmar o pagamento, no Painel admin:
   - **Nova loja** (1ª vez): crie a conta com login/senha e a **validade**
     (ex.: 1 mês à frente).
   - **Renovação**: clique em **Editar** na loja e atualize **"Licença válida até"**.
3. **Quem não pagou**:
   - **Bloquear** (botão) → trava o acesso, mas mantém os dados. Reative quando pagar.
   - ou deixe a **licença vencer** na data — trava sozinho.
4. **Cancelou o serviço de vez**: use **Excluir** (apaga a conta e as vendas
   sincronizadas dela — ação irreversível).

## Onde fica cada botão

No Painel admin (web), na linha de cada loja:
- **Editar** — muda nome, plano, validade e senha.
- **Bloquear / Ativar** — desliga/liga o acesso na hora.
- **Excluir** — remove a conta de vez (pede confirmação).

E **+ Nova loja** no topo, para cadastrar.

## Dica de controle

Padronize a **validade** sempre na data de vencimento do plano (ex.: todo dia 10).
Assim, quem não renovar trava automaticamente na data, sem você precisar bloquear
manualmente — você só **renova** quem pagou.
