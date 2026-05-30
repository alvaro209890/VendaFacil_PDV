# 🔼 Painel admin (UI) no Vercel

A interface do Painel (`painel/static/`) é estática (HTML + Tailwind via CDN).
Dá para hospedá-la no Vercel apontando para a **API no Render**.

> Você **não precisa** do Vercel para usar o painel: a própria API no Render já
> serve essa tela na URL raiz. O Vercel é só uma forma de expor a UI num domínio
> separado "por enquanto".

## Como a UI acha a API

O `index.html` resolve a URL da API nesta ordem:
1. `window.PAINEL_API_URL` (definido em `config.js`);
2. `localStorage.painel_api_url` (botão "Configurar URL da API" na tela);
3. vazio = mesma origem (caso seja servida pela própria API no Render).

A API já libera CORS (`allow_origins=["*"]`), então o navegador no Vercel pode
chamar o Render sem ajuste extra.

## Deploy no Vercel

1. Vercel → **Add New → Project** → selecione este repositório.
2. Configure:
   - **Root Directory**: `painel/static`
   - **Framework Preset**: `Other`
   - **Build Command**: (vazio)
   - **Output Directory**: (vazio — servir como estático)
3. Aponte para a API do Render, de um dos jeitos:
   - **(recomendado)** edite `painel/static/config.js` e coloque
     `window.PAINEL_API_URL = "https://SEU-SERVICO.onrender.com";` antes do deploy; ou
   - deixe `config.js` vazio e, ao abrir a página, clique em
     **"Configurar URL da API"** e cole a URL do Render (fica salva no navegador).
4. Deploy. Abra a URL do Vercel → cria o admin master (se for o 1º acesso) e usa.

## Resumo da arquitetura atual

```
Painel UI (Vercel, estática)  ──CORS──▶  Painel API (Render)  ──▶  Supabase (Postgres)
```

Os PDVs (.exe) continuam falando direto com a **API no Render**
(`VENDAFACIL_PAINEL_URL`), não com o Vercel.
