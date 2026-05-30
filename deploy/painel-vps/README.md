# 🚀 Deploy do Painel SaaS na VPS (Linux)

O painel é o cérebro do controle: você gerencia as contas (login/senha) de cada
mercado, ativa/bloqueia e define a validade da licença. Os PDVs (.exe) validam
aqui e enviam as vendas.

## Pré-requisitos
- VPS Linux (Ubuntu/Debian recomendado)
- Python 3.10+
- Nginx
- Um domínio apontando para o IP da VPS (ex: `painel.seudominio.com`)

## Passo a passo

```bash
# 1. Usuário e pastas
sudo useradd -r -m -d /opt/vendafacil vendafacil || true
sudo mkdir -p /opt/vendafacil/dados

# 2. Copiar o código do painel (deste repositório)
sudo cp -r painel /opt/vendafacil/painel

# 3. Ambiente Python
cd /opt/vendafacil/painel
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt

# 4. Segredo do JWT (fixo!)
openssl rand -hex 32     # copie o valor para PAINEL_JWT_SECRET no .service

# 5. systemd
sudo cp deploy/painel-vps/vendafacil-painel.service /etc/systemd/system/
sudo nano /etc/systemd/system/vendafacil-painel.service   # ajuste o JWT_SECRET
sudo chown -R vendafacil:vendafacil /opt/vendafacil
sudo systemctl daemon-reload
sudo systemctl enable --now vendafacil-painel

# 6. Nginx + HTTPS
sudo cp deploy/painel-vps/nginx-painel.conf /etc/nginx/sites-available/vendafacil-painel
sudo ln -s /etc/nginx/sites-available/vendafacil-painel /etc/nginx/sites-enabled/
# edite o server_name com seu domínio
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d painel.seudominio.com
```

## Primeiro acesso
Abra `https://painel.seudominio.com` → a tela pedirá para criar o **admin master**
(é você). Depois você já pode cadastrar as lojas.

## Conectar os PDVs ao painel
No `.exe` de cada loja, defina a variável de ambiente apontando para o painel:

```
VENDAFACIL_PAINEL_URL=https://painel.seudominio.com
```

Sem essa variável, o PDV roda em **modo local** (sem controle central de licença).

## Backup
Faça backup periódico de `/opt/vendafacil/dados/painel.db` (contém contas e
vendas sincronizadas).
