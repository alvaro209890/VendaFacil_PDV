# VendaFácil PDV 🛒

Sistema de PDV web para mercadinhos brasileiros — rápido, moderno e independente.

---

## 🚀 Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 19 + TypeScript + Vite |
| Estilo | Tailwind CSS v4 |
| Backend | FastAPI (Python) |
| Auth | pbkdf2_hmac + JWT |
| Banco | SQLite |
| Deploy | Vercel (frontend) + Cloudflare Tunnel (backend) |

---

## 🏗️ Estrutura

```
vendafacil-pdv/
├── src/                    # Frontend React
│   ├── components/         # PrivateRoute
│   ├── pages/              # Login, Dashboard
│   ├── store/              # Zustand (authStore)
│   └── lib/                # API client
├── backend/                # FastAPI
│   ├── main.py             # App principal
│   ├── auth.py             # Login/registro JWT
│   ├── database.py         # SQLite
│   └── requirements.txt
├── deploy/                 # Serviços systemd
├── vercel.json             # SPA rewrites
└── vite.config.ts
```

---

## ⚡ Rodar local

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 3020

# Frontend
npm install
cp .env.example .env
# Edite .env: VITE_API_URL=http://localhost:3020
npm run dev
```

---

## 🌐 Deploy Vercel

1. Importe o repo no [Vercel](https://vercel.com)
2. Configure a env var: `VITE_API_URL=https://vendafacil-api.cursar.space`
3. Deploy automático a cada push

Ou via CLI:
```bash
npx vercel --env VITE_API_URL=https://vendafacil-api.cursar.space
```

---

## 🔐 Auth

- Login com e-mail/senha
- Senhas com hash pbkdf2_hmac (200k iterações, salt aleatório)
- JWT com validade de 30 dias
- Banco local: `Banco_de_dados/VendaFacil_PDV/vendafacil.db`

---

## 📡 Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/registro` | Criar conta |
| GET | `/api/auth/me` | Dados do usuário logado |
| GET | `/health` | Health check |

---

## 🔜 Próximas rodadas

- Cadastro de produtos (foto, código de barras)
- Tela PDV (busca de produto, carrinho)
- NFC-e (Integração Focus NFe)
- Controle de estoque com alertas
- Relatórios de vendas
- Sistema de planos/mensalidade (Stripe)
