# 🔑 Licença e vinculação com o painel (offline-first)

Como o PDV (.exe) se vincula às **contas liberadas** sem travar quando falta
internet.

## Arquitetura

```
.exe (loja)  ──▶  API do Painel (Render)  ──▶  Supabase (contas liberadas)
```

O `.exe` **não acessa o Supabase diretamente** — ele fala só com a **API do
painel**, que por sua vez lê o Supabase. A loja só precisa saber a **URL do
painel**.

## Como funciona

1. **Ativação (1 vez, com internet):** a loja informa login/senha → o painel
   valida → o `.exe` salva localmente (`dados/conta.json`): token, se está
   **ativo**, a **validade da licença** e a data da última validação.
2. **No uso diário:** o `.exe` revalida online **periodicamente** (padrão a cada
   **12h**). Entre uma revalidação e outra, o login usa o **cache** — instantâneo
   e sem depender de rede.
3. **Sem internet:** continua vendendo normalmente, usando o cache, por um
   **período de carência** (padrão **30 dias**).
4. **Cache bloqueado/vencido:** se a conta aparece bloqueada ou vencida no cache,
   o `.exe` passa a **revalidar sempre** — assim, quando você desbloqueia/renova
   no painel, aplica assim que a loja reconectar.

## Quando a internet é necessária

- Na **1ª ativação** da loja.
- **Pelo menos 1 revalidação a cada 30 dias** (reseta a carência) — basta a loja
  ficar online por um instante de vez em quando.
- Na **renovação**: ao estender a validade no painel, a loja precisa ficar online
  uma vez para puxar a nova data.

## O que faz travar

- Conta **bloqueada** no painel (aplica na próxima revalidação online).
- **Validade vencida** (checada no próprio cache — vale mesmo offline).
- Mais de **30 dias** sem nenhuma revalidação (pede para conectar uma vez).

## Configuração (no build do .exe)

- `VENDAFACIL_PAINEL_URL` (ou `PAINEL_URL` em `backend/painel_config.py`): URL do
  painel no Render. **Sem isso = modo local** (vende sem controle de licença).
- `VENDAFACIL_CARENCIA_DIAS`: dias de carência offline (padrão 30).
- `VENDAFACIL_REVALIDA_HORAS`: intervalo de revalidação online (padrão 12).

> Resumo: sem wi-fi **não trava** — vende com o cache por até 30 dias, e os
> logins são instantâneos (só vai à rede no máximo a cada 12h, ou na hora de
> recuperar de um bloqueio/renovação).
