# 🚀 Deploy & Produção — VendaFácil PDV (estado atual)

Documento-mestre de como o sistema está montado e o que falta para colocar em
produção/comercializar. Para detalhes de cada parte, veja os docs específicos
linkados ao longo do texto.

## 🧩 Arquitetura

```
┌─────────────────────────────┐
│  PDV (.exe na loja)          │  React + FastAPI + SQLite, offline-first.
│  - vende sem internet         │  Cartão pela maquininha Mercado Pago (online).
│  - sincroniza quando online   │
└──────────────┬──────────────┘
               │ valida licença / envia vendas (quando online)
               ▼
┌─────────────────────────────┐      ┌──────────────────────────┐
│  Painel API (Render, free)   │◀────▶│  Painel admin UI (Vercel) │
│  FastAPI + keep-alive        │ CORS │  estático (painel/static) │
└──────────────┬──────────────┘      └──────────────────────────┘
               ▼
┌─────────────────────────────┐
│  Supabase (Postgres)         │  contas das lojas + vendas sincronizadas
└─────────────────────────────┘
```

- **PDV** = só `.exe` (nunca web). Veja [`EMPACOTAMENTO_EXE.md`](EMPACOTAMENTO_EXE.md).
- **Painel admin** = web. API no Render, UI no Vercel.
- **Banco** = Supabase (Postgres).

---

## 1) Supabase (banco)

1. Criar projeto; anotar a **senha do banco**.
2. **Connect → Connection string → Session pooler** → copiar a URI e trocar a senha.
   Formato: `postgresql://postgres.<ref>:SENHA@aws-<n>-<regiao>.pooler.supabase.com:5432/postgres`
   - ⚠️ Usar **Session pooler** (não Direct connection — IPv6, não conecta no Render free).
   - ⚠️ Sem colchetes na senha; sem espaços no host.
3. SQL: as tabelas são criadas automaticamente no 1º boot. Para rodar à mão:
   `deploy/painel-render/supabase_schema.sql` no SQL Editor.

> Não usamos Auth/API/JWT keys do Supabase — só a connection string (Postgres puro).

## 2) Render (Painel API)

Web Service (ou Blueprint via `render.yaml`):

| Campo | Valor |
|---|---|
| Root Directory | `painel` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python run.py` |
| Health Check Path | `/health` |
| Instance Type | `Free` |

Variáveis de ambiente (**3**):

| Key | Value |
|---|---|
| `DATABASE_URL` | connection string Session pooler do Supabase |
| `PAINEL_JWT_SECRET` | botão **Generate** (não trocar depois) |
| `PYTHON_VERSION` | `3.12.6` |

- **Anti-hibernação**: automático. `keepalive.py` pinga `/health` a cada 10 min
  quando a Render injeta `RENDER_EXTERNAL_URL`. Nada a configurar.
- Teste: `https://<servico>.onrender.com/health` → `{"status":"ok"}`.

Detalhes: [`deploy/painel-render/README.md`](../deploy/painel-render/README.md).

## 3) Vercel (Painel admin UI)

| Campo | Valor |
|---|---|
| Root Directory | `painel/static` |
| Framework Preset | `Other` |
| Build / Output / Install | (vazios) |
| Environment Variables | **nenhuma** |

- A UI acha a API pelo `painel/static/config.js` (já aponta para o Render).
  Se a URL do Render for outra, editar o `config.js` ou usar o botão
  **"Configurar URL da API"** na tela.

Detalhes: [`deploy/painel-vercel/README.md`](../deploy/painel-vercel/README.md).

## 4) PDV (.exe — montar no Windows)

1. **Node 20+** + `npm install` + `npm run build` (gera `dist/`).
2. `pip install -r backend/requirements-build.txt` e empacotar com
   `backend/vendafacil.spec` (PyInstaller) — há `build_exe.bat`.
3. Variável opcional `VENDAFACIL_PAINEL_URL=https://<servico>.onrender.com`
   (liga o controle de licença pelo painel; sem ela roda em modo local).
4. Maquininha: configurar na tela **Maquininha** dentro do .exe.

Detalhes: [`EMPACOTAMENTO_EXE.md`](EMPACOTAMENTO_EXE.md) e
[`MAQUININHA_MERCADOPAGO.md`](MAQUININHA_MERCADOPAGO.md).

---

## ✅ Funcionalidades prontas

- PDV offline-first: produtos, categorias, clientes, vendas, fiado, dashboard.
- Pagamentos: dinheiro, PIX (QR), débito, crédito, fiado.
- Maquininha Mercado Pago (Point) no checkout, à prova de offline.
- NFC-e (via gateway Focus NFe/PlugNotas).
- Painel SaaS: criar / editar / bloquear / **excluir** contas; validade de licença;
  vendas sincronizadas por loja.
- Licença offline-first com carência.

## 🚧 O que falta para comercializar

Veja a lista detalhada em [`CHECKLIST_COMERCIALIZACAO.md`](CHECKLIST_COMERCIALIZACAO.md).
