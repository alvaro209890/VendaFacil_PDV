# 🛒 VendaFácil PDV

Sistema de **Ponto de Venda (PDV)** para mercadinhos e pequenos comércios,
distribuído como **executável único (.exe)** com controle central de licenças.

> 📦 **Deploy e produção:** [`docs/DEPLOY_E_PRODUCAO.md`](docs/DEPLOY_E_PRODUCAO.md)
> · **Gerar o .exe no Windows:** [`docs/BUILD_WINDOWS.md`](docs/BUILD_WINDOWS.md)
> · **Cobrança/bloqueio manual:** [`docs/COBRANCA_MANUAL.md`](docs/COBRANCA_MANUAL.md)
> · **Custos & financeiro:** [`docs/CUSTOS.md`](docs/CUSTOS.md)
> · **Jurídico (Termos/Privacidade/LGPD):** [`docs/legal/`](docs/legal/)
> · **O que falta para comercializar:** [`docs/CHECKLIST_COMERCIALIZACAO.md`](docs/CHECKLIST_COMERCIALIZACAO.md)

## 🧩 Como o sistema é montado

São **dois componentes**:

1. **PDV (.exe)** — roda na máquina do caixa, **offline-first**. Tem o backend
   (FastAPI) e o frontend (React) embutidos e o banco local (SQLite). Vende mesmo
   sem internet. Veja [`docs/EMPACOTAMENTO_EXE.md`](docs/EMPACOTAMENTO_EXE.md).
2. **Painel SaaS** — roda na sua **VPS Linux** com domínio próprio. É onde **você**
   cria/bloqueia as contas (login+senha) de cada loja, define validade da licença
   e acompanha as vendas sincronizadas. Veja [`deploy/painel-vps/README.md`](deploy/painel-vps/README.md).

```
┌───────────────────────┐        valida licença / envia vendas
│   PDV .exe (loja A)    │ ───────────────────────────────────┐
│  FastAPI + SQLite +    │                                     │
│  React  (offline-first)│ <─── ativa/bloqueia, validade ──┐   ▼
└───────────────────────┘                                 │  ┌──────────────────────┐
┌───────────────────────┐                                 └──│   Painel SaaS (VPS)   │
│   PDV .exe (loja B)    │ ───────────────────────────────────│  você gerencia tudo   │
└───────────────────────┘                                    └──────────────────────┘
```

**Licença offline-first:** o PDV valida a conta no painel quando há internet e
guarda o resultado; sem conexão, continua vendendo por um período de carência
(padrão 30 dias). Se você bloquear a conta no painel, na próxima revalidação
online o PDV trava. Sem `VENDAFACIL_PAINEL_URL` configurado, o PDV roda em
**modo local** (sem controle central).

---

## ✨ Funcionalidades

### 🔐 Autenticação Local
- Login / Registro com e-mail e senha
- Senhas com hash PBKDF2-HMAC-SHA256 (200k iterações)
- Tokens JWT HS256 com 30 dias de validade
- Recuperação de senha via token

### 🛒 PDV / Ponto de Venda
- Busca de produtos por nome ou código de barras
- Carrinho de compras com ajuste de quantidade
- Cálculo automático de subtotal, desconto e total
- 4 formas de pagamento: Dinheiro, PIX, Débito, Crédito
- 💳 Cobrança no cartão pela **maquininha Mercado Pago (Point)** — veja
  [`docs/MAQUININHA_MERCADOPAGO.md`](docs/MAQUININHA_MERCADOPAGO.md)
- Baixa automática de estoque ao finalizar venda
- Validação de estoque insuficiente

### 📦 Gestão de Produtos
- Cadastro completo: nome, preço custo/venda, estoque, código de barras, unidade
- Edição inline
- Soft delete (desativar)
- Alerta visual de estoque baixo

### 📊 Dashboard
- Métricas em tempo real: produtos ativos, vendas do dia, total em vendas
- Alertas de estoque baixo
- Últimas vendas realizadas
- Produtos com estoque crítico

### 🧾 Histórico de Vendas
- Lista paginada de todas as vendas
- Detalhamento com itens, forma de pagamento, descontos
- Total do dia

---

## 🏗️ Arquitetura

```
vendafacil-pdv/
├── backend/                  # API Python (FastAPI + SQLite)
│   ├── main.py              # App principal + dashboard endpoint
│   ├── auth.py              # Autenticação (JWT, hash senhas)
│   ├── database.py          # SQLite (users, produtos, vendas, itens_venda)
│   ├── produtos.py          # CRUD de produtos
│   ├── vendas.py            # Checkout + histórico
│   └── requirements.txt     # fastapi, uvicorn
├── src/                     # Frontend React + TypeScript
│   ├── lib/api.ts          # Cliente HTTP (fetch-based)
│   ├── store/authStore.ts  # Zustand (auth state)
│   ├── components/
│   │   └── PrivateRoute.tsx
│   └── pages/
│       ├── Login.tsx       # Login / Registro
│       ├── Dashboard.tsx   # Métricas e alertas
│       ├── PDV.tsx         # Tela de venda
│       ├── Produtos.tsx    # Gestão de produtos
│       └── Vendas.tsx      # Histórico
├── deploy/
│   └── vendafacil-backend.service  # systemd unit
└── package.json
```

---

## 🚀 Rodando

### Pré-requisitos
- Python 3.10+
- Node.js 20+
- Linux (systemd)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3020
```

### Frontend

```bash
cp .env.example .env
# Edite .env com a URL da API
npm install
npm run dev        # dev → http://localhost:5173
npm run build      # produção → dist/
```

### Produção (systemd + Cloudflare Tunnel)

```bash
# Backend
sudo cp deploy/vendafacil-backend.service /etc/systemd/system/
sudo systemctl enable --now vendafacil-backend

# Frontend (servir com qualquer servidor HTTP)
# Ex: nginx, caddy, ou Vercel
```

---

## 🔌 API Endpoints

### Auth
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/registro` | Criar conta |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Perfil do usuário |

### Produtos
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/produtos` | Listar produtos |
| GET | `/api/produtos/:id` | Detalhes do produto |
| POST | `/api/produtos` | Criar produto |
| PUT | `/api/produtos/:id` | Atualizar produto |
| DELETE | `/api/produtos/:id` | Desativar (soft delete) |

### Vendas
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/vendas/checkout` | Finalizar venda |
| GET | `/api/vendas` | Listar vendas |
| GET | `/api/vendas/:id` | Detalhes da venda |

### Dashboard
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/dashboard` | Métricas gerais |

---

## 🗄️ Banco de Dados

SQLite armazenado em `Banco_de_dados/VendaFacil_PDV/vendafacil.db`

### Tabelas
- **users** — id, email, nome, senha_hash, criado_em, ultimo_login
- **produtos** — id, user_id, nome, preco_custo, preco_venda, estoque, estoque_minimo, codigo_barras, unidade, ativo
- **vendas** — id, user_id, total, desconto, forma_pagamento, status, observacao, criado_em
- **itens_venda** — id, venda_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal

---

## 🎨 Stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, React Router v7, Zustand
- **Backend:** Python FastAPI, SQLite, uvicorn
- **Segurança:** PBKDF2-HMAC-SHA256, JWT HS256, CORS configurado
- **Deploy:** systemd + Cloudflare Tunnel (backend), Vercel/estático (frontend)

---

## 📝 Licença

Projeto privado — uso interno.
