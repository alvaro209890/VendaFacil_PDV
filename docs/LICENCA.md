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
2. **No uso diário:** a consulta de status tenta revalidar quando o cache exige
   (padrão **12h**, ou conta bloqueada/vencida). Login e ativação podem tentar
   validar online e usar o fallback offline já cadastrado se a rede falhar.
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

## O que bloqueia novas vendas

- Conta **bloqueada** no painel (aplica na próxima revalidação online).
- **Validade vencida** (checada no próprio cache — vale mesmo offline).
- Mais de **30 dias** sem nenhuma revalidação (pede para conectar uma vez).

## Configuração (no build do .exe)

- `VENDAFACIL_PAINEL_URL` (ou `PAINEL_URL` em `backend/painel_config.py`): URL do
  painel no Render. Modo local só quando `VENDAFACIL_PAINEL_URL` estiver definida como vazia ou quando `PAINEL_URL` em `backend/painel_config.py` estiver vazio no build. O valor versionado hoje aponta para `https://vendafacil-painel.onrender.com`, então o `.exe` padrão **exige o painel** (licença).
- `VENDAFACIL_CARENCIA_DIAS`: dias de carência offline (padrão 30).
- `VENDAFACIL_REVALIDA_HORAS`: intervalo de revalidação online (padrão 12).

## O que continua disponível

Licença bloqueada recusa novo checkout (403), mas não substitui a tela inteira.
Continuam disponíveis fechamento de caixa, leitura de produtos/vendas, backup e
exportação dos XMLs fiscais. O checkout usa só o cache (`online=False`): não
espera o painel fora do ar. Ativação/login continuam podendo consultar a rede.

## Validade e sincronização

- Data sem hora, como `2026-11-10`, vale até 23:59:59 no fuso UTC−4 de MT; não
  expira à meia-noite UTC. Data inválida é recusada pelo cadastro/edição (400) e
  um valor inválido legado bloqueia, não vira licença perpétua.
- Vendas são locais antes do envio em background. O ACK informa UUIDs aceitos;
  numa aceitação parcial, só essas vendas saem da fila. Resposta não-JSON, UTF-8
  inválido ou schema inválido do ACK mantém a fila para o próximo ciclo, sem
  exceção. Quando `aceitas` existe, precisa ser lista de strings: nunca cai no
  modo legado por ter tipo errado. Sem `aceitas`, o legado só aceita contagem
  inteira igual ao lote inteiro (não booleano/float). O checkout não depende
  dessa sincronização.
- Cobrança eletrônica aprovada sem venda permanece pendente de conciliação;
  outra cobrança é recusada (409) e o mesmo payment_id reutiliza a venda, sem
  nova baixa de estoque.
- PIX estático normaliza nome/cidade para ASCII e recalcula o CRC do payload.

> Sem internet, vende dentro da carência e da validade do cache. Bloqueio de
> licença não retém os dados do lojista.
