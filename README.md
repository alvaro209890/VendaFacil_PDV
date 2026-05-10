# 🛒 VendaFácil PDV

Sistema de **Ponto de Venda (PDV)** para mercadinhos e pequenos comércios.

**100% independente** — autenticação local (SQLite), sem dependência de Firebase ou serviços externos. Roda até em Raspberry Pi.

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
