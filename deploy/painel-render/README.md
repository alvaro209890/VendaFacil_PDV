# 🚀 Deploy do Painel SaaS no Render (banco Supabase)

O painel é o cérebro do controle: você gerencia as contas (login/senha) de cada
mercado, ativa/bloqueia e define a validade da licença. Os PDVs (.exe) validam
aqui e enviam as vendas sincronizadas.

Esta é a alternativa ao deploy em VPS (`deploy/painel-vps/`). No Render você não
precisa de Nginx, systemd nem certbot — HTTPS e proxy já vêm prontos. O banco
fica no **Supabase (Postgres)**, então os dados não dependem do disco do Render
e o serviço pode rodar no **plano free**.

## 1. Criar o banco no Supabase

1. Crie um projeto em <https://supabase.com>.
2. Em **Settings → Database → Connection string**, copie a string **URI**. Ela
   se parece com:
   ```
   postgresql://postgres:SUA_SENHA@db.<ref>.supabase.co:5432/postgres
   ```
   > Dica: para apps com poucas conexões, a connection string do **pooler**
   > (porta `6543`, host `...pooler.supabase.com`) também funciona e é mais
   > robusta sob carga. Qualquer uma das duas serve.
3. As tabelas (`admins`, `contas`, `vendas_sync`) são criadas automaticamente na
   primeira vez que o painel sobe — você não precisa rodar SQL manualmente.
   Se preferir preparar/conferir o banco antes, cole
   [`supabase_schema.sql`](./supabase_schema.sql) no **SQL Editor → New query →
   Run** (é idempotente, pode rodar de novo sem problema).

## 2. Deploy no Render

1. Faça push deste repositório para o GitHub (ou GitLab).
2. No Render: **New → Blueprint** e selecione o repositório. Ele lê o
   [`render.yaml`](../../render.yaml) da raiz e cria o serviço `vendafacil-painel`.
3. Quando pedir, preencha a variável **`DATABASE_URL`** com a connection string
   do Supabase (passo 1). Ela não é versionada (`sync: false`).
4. Clique em **Apply** e aguarde o build/deploy. A URL pública fica algo como
   `https://vendafacil-painel.onrender.com`.

> Sem usar Blueprint? Crie um **Web Service** manual apontando para a pasta
> `painel` com Build `pip install -r requirements.txt`, Start `python run.py`,
> Health check `/health`, e defina `DATABASE_URL` e `PAINEL_JWT_SECRET`.

## Variáveis de ambiente

| Variável            | De onde vem                | Função                                       |
|---------------------|----------------------------|----------------------------------------------|
| `PORT`              | Render (automático)        | Porta em que o serviço escuta.               |
| `DATABASE_URL`      | Você (string do Supabase)  | Conexão Postgres. Se ausente, o painel cai para SQLite local (só dev). |
| `PAINEL_JWT_SECRET` | `render.yaml` (gerado)     | Segredo fixo dos tokens JWT. **Não troque** — trocar invalida todos os tokens emitidos. |

## Primeiro acesso

Abra a URL do serviço → a tela pedirá para criar o **admin master** (você).
Depois você já cadastra as lojas.

## Conectar os PDVs ao painel

No `.exe` de cada loja, defina a variável de ambiente apontando para o Render:

```
VENDAFACIL_PAINEL_URL=https://vendafacil-painel.onrender.com
```

Sem essa variável, o PDV roda em **modo local** (sem controle central de licença).

## Backup

Os dados ficam no Supabase. Use o próprio painel do Supabase para backups
(planos pagos têm backup automático; no free, exporte periodicamente via
**Database → Backups** ou `pg_dump`).

## Observações

- No plano free o serviço **hiberna** após inatividade; a primeira requisição
  depois disso demora alguns segundos (cold start). Planos pagos ficam sempre on.
- O start command usa `python run.py`, que lê a porta de `$PORT` automaticamente.
- Em desenvolvimento local, sem `DATABASE_URL`, o painel usa SQLite em
  `painel/dados/painel.db` — nenhuma configuração extra necessária.
