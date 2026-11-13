# Migração do painel: Render + Supabase → VPS de canais

> Plano para outro agente executar de ponta a ponta. Escrito em 13/11/2026.
> Objetivo: o painel do VendaFácil sai do Render e do Supabase e passa a rodar
> **inteiro na `canais-vps`**, com HTTPS, banco local e backup — sem depender de
> serviço que hiberna ou pausa.

## 0. Resumo da decisão

| Peça | Antes | Depois |
|---|---|---|
| Aplicação | Render (free, hiberna) | `canais-vps`, systemd |
| Banco | Supabase (free, pausa por inatividade) | **SQLite** em `/opt/vendafacil/dados/painel.db` |
| HTTPS | Render | Cloudflare Tunnel (preferido) ou Caddy + Let's Encrypt |
| Backup | Supabase | cron diário + retenção 14 dias |
| URL do PDV | `https://vendafacil-painel.onrender.com` | `https://painel.<DOMINIO>` (embutida no `.exe` 1.0.14) |

Por que: o PDV espera **6 segundos** na ativação/revalidação (`backend/conta.py`,
`_TIMEOUT = 6`). Render dormindo estoura isso e o Supabase free pausa sozinho.
Máquina sempre ligada resolve os dois.

## 1. Estado atual medido (13/11/2026, 14:50 BRT)

> Nos comandos, `painel.<DOMINIO>` = **`painel.cursar.space`** (domínio da frota,
> Cloudflare). O hostname temporário da trilha C é `3-235-84-94.sslip.io`.

**`canais-vps`** — AWS Lightsail `us-east-1a`, Ubuntu 24.04, IP público IPv4
`3.235.84.94` (confirmar na execução), Tailscale `100.112.29.47`, usuário `ubuntu`
com sudo sem senha, Python 3.12.3, 2 vCPU, 1,9 GB de RAM (**1,37 GB livres**),
disco 58 GB em 19%, fuso `America/Cuiaba`.

O que já roda lá (não é nosso alvo, **não mexer**):

| Serviço | Função |
|---|---|
| `xvfb-canais`, `fluxbox-canais`, `x11vnc-canais`, `novnc-canais` | desktop virtual usado nos logins/publicação dos canais |
| `tailscaled` | rede da frota |
| `snap.amazon-ssm-agent` | acesso de emergência da AWS |

Não há nginx, Caddy, certbot, psql nem sqlite3 CLI instalados. `ufw` está ativo
liberando **só 22/tcp**. Nada escuta em 80/443/8080.

**Painel** (`painel/`): FastAPI + uvicorn (+ psycopg, usado só no modo Postgres).
Porta `PORT`/`PAINEL_PORT` (padrão 8080), host `PAINEL_HOST`. Com
`DATABASE_URL`/`SUPABASE_DB_URL` vazio ele usa **SQLite** em `PAINEL_DATA_DIR`.
O schema (`_SCHEMA` em `painel/database.py`) é criado no primeiro boot.

Contrato que o PDV consome (não pode mudar):

| Rota | Uso |
|---|---|
| `POST /api/conta/validar` | ativação (login/senha da loja) |
| `GET /api/conta/status` | revalidação a cada 12 h |
| `POST /api/sync/vendas` | espelho das vendas |
| `GET /health` | keep-alive/monitoramento |
| `GET /api/admin/precisa-setup`, `POST /api/admin/setup` | criação do admin master |
| `/` e `/assets` | UI estática do painel |

## 0.1 Autonomia (ordem do Álvaro, 13/11/2026)

O agente executa **tudo sozinho**, da Fase 0 ao corte, sem perguntar nada e sem
esperar resposta. Decisões já tomadas: SQLite, `canais-vps`, hostname
`painel.cursar.space`, `.exe` 1.0.14, Supabase **não** migra (sem dado real).

O único ponto que pode exigir terceiro é o **DNS/entrada pública** (ver Fase 3).
Resolver nesta ordem, sem parar: token da Cloudflare → registro A manual já
existente → hostname temporário `sslip.io`. Só reportar bloqueio se as três
falharem.

## 2. Critérios de aceite (só termina quando tudo for verdade)

1. `curl -fsS https://painel.<DOMINIO>/health` → `{"status":"ok","app":"vendafacil-painel",...}`.
2. Certificado válido (Cloudflare ou Let's Encrypt) e HTTP redirecionando para HTTPS.
3. Admin master criado; login pela UI funciona; nova senha forte.
4. Conta da loja criada (mesmo login de antes) e `POST /api/conta/validar` devolve token.
5. Bloquear a conta na UI → `/api/conta/validar` recusa com motivo; desbloquear → volta.
6. Um PDV com `VENDAFACIL_PAINEL_URL=https://painel.<DOMINIO>` ativa com dados descartáveis.
7. `painel.db` existe, cresce e o cron de backup gerou arquivo do dia.
8. Memória da VPS continua abaixo de ~1,0 GB usada; VNC/noVNC seguem funcionando.
9. Render e Supabase **não** são desligados antes de 72 h de operação estável.

## 3. Pré-requisitos (situação em 13/11/2026)

| # | Item | Situação |
|---|---|---|
| P1 | **Supabase sem dado real** | ✅ confirmado pelo Álvaro: não há loja nem venda real. **Não migrar**; criar a conta na Fase 4 |
| P2 | **Subdomínio** | ✅ `painel.cursar.space` (domínio da frota, Cloudflare) |
| P3 | **DNS** | ⚠️ o agente resolve (ver Fase 3). O `cert.pem` do `server` responde `unauthorized` — não contar com ele |
| P4 | **Firewall 80/443** | só necessário no caminho Caddy (Fase 3, trilha B). O caminho por túnel não abre porta |
| P5 | **Snapshot da VPS** | tentar pelo console; se não houver acesso, seguir (a máquina não guarda dado crítico além do banco novo) |

Sem P2, usar o hostname temporário da trilha C e reportar.

## 4. Regras que não se negociam

- Segredo nunca aparece em comando colado, log, commit ou documento. O
  `PAINEL_JWT_SECRET` é gerado **na VPS** e só existe em
  `/etc/vendafacil/painel.env` (`chmod 600`, dono `root:vendafacil`).
- Não copiar para a VPS o cofre fiscal, certificado A1, `Dados_James/`, nem o
  banco do PDV. Ali só vai o painel.
- Não usar `git clone` do repositório na VPS (repo privado = token em disco).
  Copiar só a pasta `painel/` por `scp`.
- Não tocar nas units do desktop virtual (`xvfb-*`, `fluxbox-*`, `x11vnc-*`,
  `novnc-*`), no `tailscaled` nem nos cookies/publicação dos canais.
- Um passo por vez, com a saída real colada no registro (§12). Sem "deve funcionar".
- `ufw` **e** firewall do Lightsail: os dois precisam liberar 80/443.
- O painel escuta **só em 127.0.0.1:8080**. Nunca `0.0.0.0`.
- **Copiar `painel/` de uma árvore limpa.** Em 13/11/2026 havia trabalho de outro
  agente ainda não commitado (`painel/static/calendario.js` não rastreado e
  mudanças em `painel/static/index.html`, `src/pages/ContasReceber.tsx` e
  `src/pages/Produtos.tsx`). `scp` leva o que está no disco: antes de copiar,
  `git status --porcelain` tem que estar limpo, senão o WIP de outro agente vai
  para produção sem revisão.

## 5. Execução

### Fase 0 — Baseline e snapshot (10 min)

```bash
ssh canais 'free -m; df -h /; systemctl is-active xvfb-canais fluxbox-canais x11vnc-canais novnc-canais; curl -4 -s -m 5 https://ifconfig.me; echo'
```

Guardar a saída (é o "antes"). Criar o snapshot no console do Lightsail (P5).

### Fase 1 — Preparar sistema e código (15 min)

```bash
# na VPS
sudo apt update && sudo apt install -y python3-venv caddy
sudo useradd --system --create-home --home-dir /opt/vendafacil --shell /usr/sbin/nologin vendafacil
sudo mkdir -p /opt/vendafacil/dados /opt/vendafacil/backups /etc/vendafacil
sudo chown -R vendafacil:vendafacil /opt/vendafacil
```

Copiar o código do PC Windows (só a pasta do painel):

```powershell
scp -r C:\GIS\VendaFacil_PDV\painel ubuntu@canais:/tmp/painel
```

```bash
# na VPS
sudo rm -rf /opt/vendafacil/painel
sudo mv /tmp/painel /opt/vendafacil/painel
sudo chown -R vendafacil:vendafacil /opt/vendafacil/painel
sudo -u vendafacil python3 -m venv /opt/vendafacil/venv
sudo -u vendafacil /opt/vendafacil/venv/bin/pip install -q --upgrade pip
sudo -u vendafacil /opt/vendafacil/venv/bin/pip install -q -r /opt/vendafacil/painel/requirements.txt
/opt/vendafacil/venv/bin/python -c "import fastapi, uvicorn; print('ok', fastapi.__version__)"
```

Prova: `ok` + versão do FastAPI.

### Fase 2 — Ambiente e serviço (10 min)

```bash
sudo tee /etc/vendafacil/painel.env >/dev/null <<'EOF'
PAINEL_HOST=127.0.0.1
PAINEL_PORT=8080
PAINEL_DATA_DIR=/opt/vendafacil/dados
PAINEL_JWT_SECRET=TROCAR_AQUI
EOF
sudo chown root:vendafacil /etc/vendafacil/painel.env
sudo chmod 640 /etc/vendafacil/painel.env
```

Trocar `TROCAR_AQUI` por um segredo gerado **na VPS**, sem imprimir:

```bash
sudo sed -i "s|TROCAR_AQUI|$(openssl rand -hex 32)|" /etc/vendafacil/painel.env
```

> `DATABASE_URL` **não** entra: ausente = SQLite. Se entrar por engano, o painel
> tenta Postgres e cai.

Unit `/etc/systemd/system/vendafacil-painel.service`:

```ini
[Unit]
Description=VendaFacil Painel SaaS
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=vendafacil
Group=vendafacil
WorkingDirectory=/opt/vendafacil/painel
EnvironmentFile=/etc/vendafacil/painel.env
ExecStart=/opt/vendafacil/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8080 --workers 1
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/vendafacil/dados
MemoryMax=512M
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vendafacil-painel
systemctl status --no-pager vendafacil-painel | head -12
curl -fsS http://127.0.0.1:8080/health; echo
curl -fsS http://127.0.0.1:8080/api/admin/precisa-setup; echo
```

Esperado: `active (running)`, health `ok`, `{"precisa_setup":true}`.

> **Atenção:** enquanto não houver admin, `POST /api/admin/setup` é público.
> Não publique a porta antes de criar o admin (Fase 4).

### Fase 3 — Entrada pública e TLS (15–30 min)

Três trilhas, nesta ordem. Não parar para perguntar: tentar A, depois B, depois C.

**Trilha A — Cloudflare Tunnel (preferida; nenhuma porta aberta).**

```bash
# token criado no dashboard (Zero Trust -> Tunnels -> Create a tunnel -> Cloudflared)
sudo apt install -y cloudflared   # se o pacote não existir, baixar o .deb oficial
sudo cloudflared service install "$TUNNEL_TOKEN"     # NUNCA ecoar o token
sudo systemctl status --no-pager cloudflared | head -8
```

No dashboard, o hostname público `painel.cursar.space` deve apontar para
`http://localhost:8080`. Prova: `curl -fsS https://painel.cursar.space/health`.

> O `cert.pem` do `server` está sem autorização (`unauthorized` em 13/11), então
> `cloudflared tunnel create` **não** funciona sem token novo. Não insistir.

**Trilha B — Caddy + registro A** (se houver acesso à zona Cloudflare):

```bash
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
painel.cursar.space {
    encode zstd gzip
    header {
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
    }
    reverse_proxy 127.0.0.1:8080
}
EOF
sudo systemctl reload caddy || sudo systemctl restart caddy
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp  # + liberar 80/443 no console do Lightsail
```

Com a API da Cloudflare (token de zona, `DNS:Edit`):

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  --data '{"type":"A","name":"painel","content":"3.235.84.94","proxied":true,"ttl":1}' | head -c 300
```

**Trilha C — hostname temporário, sem DNS** (100% autônoma):

```bash
# 3-235-84-94.sslip.io resolve sozinho para o IP da VPS
# usar o mesmo Caddyfile da trilha B com server_name 3-235-84-94.sslip.io
curl -fsS https://3-235-84-94.sslip.io/health
```

Registrar no relatório qual trilha valeu. Se as três falharem, deixar o painel
rodando em `127.0.0.1:8080` e reportar **qual único clique** falta (DNS ou porta).

### Fase 4 — Admin e conta da loja (10 min)

1. Abrir `https://painel.<DOMINIO>` no navegador e criar o **admin master**.
2. Trocar a senha se ela foi digitada em qualquer lugar compartilhado.
3. Criar a conta da loja James: login igual ao de antes, senha nova (mínimo do
   painel), plano e validade conforme decisão do Álvaro.
4. Provar o contrato:

```bash
curl -s -X POST https://painel.<DOMINIO>/api/conta/validar \
  -H 'Content-Type: application/json' \
  -d '{"login":"<LOGIN_LOJA>","senha":"<SENHA_LOJA>"}' | head -c 300; echo
```

Esperado: objeto com `token` e status ativo. Depois, na UI, **desativar** a conta,
repetir o `curl` (deve recusar com motivo) e **reativar**.

### Fase 5 — Migração de dados (condicional, ver §6)

Se o Supabase só tem dado de teste, **pular**: cria-se a conta na Fase 4 e o
`vendas_sync` nasce vazio. Se houver dado real, executar §6 **com o serviço
parado** e conferir as contagens.

### Fase 6 — Recompilar o `.exe` 1.0.14 (no Windows)

```powershell
cd C:\GIS\VendaFacil_PDV
# 1) apontar o build para o painel novo
#    editar backend\painel_config.py: PAINEL_URL = "https://painel.<DOMINIO>"
# 2) subir a versão
#    backend\version.py: APP_VERSION = "1.0.14"
#    installer\vendafacil.iss: #define AppVersion "1.0.14"
```

```bat
build_exe.bat
installer\build_installer.bat
```

Depois, com `TEMP`/`TMP` fora do repositório:

```powershell
cd C:\GIS\VendaFacil_PDV\backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short
cd ..
backend\.venv\Scripts\python -X utf8 -I scripts\roteiro_exe.py --chromium --cupons output\fase6\notas-simuladas.json
py -3.12 -X utf8 -I scripts\verificar_cupons_pdf.py output\fase6\notas-simuladas.json
Get-FileHash dist_exe\VendaFacilPDV.exe,dist_installer\VendaFacilPDV-Setup-1.0.14.exe -Algorithm SHA256
```

Teste de ativação contra o painel novo, com dados descartáveis:

```powershell
# usar o launcher em Temp\opencode\pdv-teste\start.py como referência,
# trocando VENDAFACIL_PAINEL_URL para https://painel.<DOMINIO>
# e a pasta de dados para uma descartável; esperado: tela "Login da loja"
```

Registrar caminho, tamanho e sha256; commit por caminho explícito (um commit
para o novo endereço/versão, outro se houver correção). Nunca `git add -A`.

### Fase 7 — Corte

1. Instalar o 1.0.14 no PC do James e ativar com a conta da loja.
2. Primeira revalidação: fechar e abrir o PDV → deve entrar sem rede lenta.
3. Só então: desligar o Render (após 72 h) e pausar/remover o Supabase (após
   confirmar que `vendas_sync` no painel novo recebe as vendas).

### Fase 8 — Operação contínua (15 min)

Backup diário — `/usr/local/bin/vendafacil-backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
/usr/bin/python3 - <<'PY'
import datetime, sqlite3
origem = sqlite3.connect('/opt/vendafacil/dados/painel.db')
destino = sqlite3.connect(f"/opt/vendafacil/backups/painel-{datetime.date.today():%Y-%m-%d}.db")
origem.backup(destino)
destino.close(); origem.close()
PY
find /opt/vendafacil/backups -name 'painel-*.db' -mtime +14 -delete
```

```bash
sudo install -m 755 /dev/stdin /usr/local/bin/vendafacil-backup.sh <<'EOF'
...conteúdo acima...
EOF
echo '0 3 * * * root /usr/local/bin/vendafacil-backup.sh' | sudo tee /etc/cron.d/vendafacil-backup
sudo /usr/local/bin/vendafacil-backup.sh && ls -l /opt/vendafacil/backups
```

Monitoramento: um ping externo em `https://painel.<DOMINIO>/health` a cada 5 min
(UptimeRobot ou equivalente). Sem isso, um painel caído só aparece na ativação.

### Fase 9 — Rollback (se algo falhar)

1. `sudo systemctl stop vendafacil-painel` e `sudo systemctl disable vendafacil-painel`.
2. Reinstalar o `.exe` 1.0.13 (aponta para o Render) nas lojas afetadas.
3. Render continua no ar por 72 h justamente para isso — não apagar antes.
4. Se o problema for DNS/TLS, manter o Caddy e voltar depois; o banco local
   (`painel.db`) não é afetado.

## 6. Migração de dados do Supabase — **não se aplica**

O Álvaro confirmou em 13/11/2026 que **não há dado real** no Supabase (nenhuma
loja pagante, nenhuma venda). Portanto:

- **não** conectar no Supabase, **não** migrar, **não** copiar connection string;
- o `painel.db` nasce vazio e a conta da loja é criada na Fase 4;
- registrar no relatório a confirmação ("sem dado real — não migrado").

O script `migrar_supabase_para_sqlite.py` fica no repositório **só para o futuro**
(caso apareça dado real antes do corte). Se for usado algum dia:

```bash
sudo systemctl stop vendafacil-painel
sudo -u vendafacil /opt/vendafacil/venv/bin/python \
  /opt/vendafacil/migrar_supabase_para_sqlite.py \
  --origem "<connection string>" --destino /opt/vendafacil/dados/painel.db
sudo systemctl start vendafacil-painel
```

O script: cria o schema do próprio painel se faltar, copia `admins`, `contas`,
`vendas_sync`, `fin_config` e `fin_custos` preservando ids, **recusa destino com
dados** e imprime a contagem de origem e destino. Senhas continuam válidas
(PBKDF2 é a mesma função), mas os **tokens** antigos não — todos relogam.

> A connection string do Supabase é segredo: passar por variável de ambiente ou
> arquivo `600`, nunca por argumento que fique no histórico do shell. Se usar
> `--origem`, limpar o histórico depois.

## 7. Diagnóstico rápido

| Sintoma | Verificar |
|---|---|
| 502 no Caddy | `systemctl status vendafacil-painel`; `curl 127.0.0.1:8080/health` |
| Certificado não sai | `dig +short painel.<DOMINIO>`; portas 80/443 no ufw **e** no Lightsail; `journalctl -u caddy -n 50` |
| `permission denied` no banco | dono de `/opt/vendafacil/dados` e `ReadWritePaths` da unit |
| Painel cria admin sozinho? | `curl /api/admin/precisa-setup` — se `true` e o site está público, criar **agora** |
| PDV não ativa | `curl -X POST .../api/conta/validar`; conferir relógio da VPS (`timedatectl`) e cadeia do certificado |
| VNC lento/caiu | `free -m`; `MemoryMax` do painel; units do desktop virtual intactas |

## 8. O que NÃO fazer

- Não instalar Postgres "por garantia": SQLite é a decisão.
- Não rodar o painel com `--workers > 1` (SQLite + lock em processo único).
- Não copiar `Dados_James/`, `.pfx`, cofre ou banco do PDV para a VPS.
- Não apagar o Render nem o Supabase antes das 72 h.
- Não mexer no desktop virtual dos canais para "liberar RAM".

## 9. Registro de execução (preencher com saída real)

Execução de 13/11/2026 (autor: Claude), horário da VPS (`America/Cuiaba`, -04).

| Fase | Comando | Saída (resumo) | Hora | OK |
|---|---|---|---|---|
| 0 | baseline | IP `3.235.84.94`; RAM 535 MB usados / 1370 MB livres; disco 19%; `xvfb/fluxbox/x11vnc/novnc-canais` e `tailscaled` active; ufw só 22 + tailscale0; snapshot do Lightsail **não** feito (sem acesso ao console) | 14:39 | ✅ |
| 1 | venv + pip | `painel/` do commit `8692c36` via `git archive` (sem WIP); `caddy 2.6.2`; `ok 0.162.7 0.54.0` (FastAPI, uvicorn) | 14:41 | ✅ |
| 2 | health local | unit `active (running)`; `{"status":"ok","app":"vendafacil-painel","version":"1.0.0"}`; `{"precisa_setup":true}`; JWT de 64 hex gerado na VPS (`painel.env` 640 root:vendafacil) | 14:41 | ✅ |
| 3 | health HTTPS | Trilha A/B: sem token e `cert.pem` `unauthorized` (`cloudflared tunnel list`). Trilha C: Caddy obteve LE para `3-235-84-94.sslip.io` (válido até 11/02/2027), HTTP→HTTPS 308 de fora; **443 dá timeout de fora** — firewall do Lightsail (só 22/80). Dentro da VPS: `HTTP/2 200` + HSTS. `painel.cursar.space` já no Caddyfile, aguardando DNS | 14:43 | ⚠️ |
| 4 | admin + conta + bloqueio | admin criado **antes** de abrir porta (`precisa_setup:false`); contas `james` e `teste-ativacao`; validar → `ok:true` + token; senha errada → 401; bloqueada → `ok:false`, "Conta bloqueada…"; reativada → `ok:true`. Senhas só em `/etc/vendafacil/credenciais-iniciais` (600 root) | 14:42 | ✅ |
| 5 | migração | sem dado real — não migrado (decisão do Álvaro) | — | ✅ |
| 6 | build 1.0.14 + hashes | worktree limpo `6bb9821`; `VendaFacilPDV.exe` 39 694 841 B `BCFB3871…8785E`; `Setup-1.0.14.exe` 39 981 107 B `654A270A…FDE97`; backend 466 + 9 desmarcados, painel 23, Node 36, E2E 91, ESLint 0; `roteiro_exe --chromium` 49 req / 0×5xx (v1.0.14); cupons 4/4 | 15:50 | ✅ |
| 7 | ativação do PDV | `.exe` 1.0.14 com dados descartáveis contra o painel da VPS (túnel SSH, sem TLS público): ativa (`TESTE descartavel`), senha errada 401, conta bloqueada 401 "Conta bloqueada…", liberada ativa de novo. URL embutida → 503 "Sem conexão" até existir DNS | 14:52 | ✅ |
| 8 | backup + monitor | `/etc/cron.d/vendafacil-backup` 03:00 (usuário vendafacil, `integrity_check ok`, retenção 14 d); monitor externo = timer de usuário `vendafacil-painel-monitor` no `server` (5 min, log `~/logs/vendafacil-painel-monitor.log`) — hoje `ok=0` até abrir 443/DNS | 14:45 | ✅ |

Atualização 13/11 15:11: o Álvaro liberou **443/tcp** no Lightsail (origem `0.0.0.0/0`).
De fora: `curl https://3-235-84-94.sslip.io/health` → `{"status":"ok",...}`, HTTP → 308 HTTPS, HSTS.
`.exe` 1.0.14 com `VENDAFACIL_PAINEL_URL=https://3-235-84-94.sslip.io` e dados descartáveis: ativou
em 0,66 s, senha errada 401, conta bloqueada 401 "Conta bloqueada…", liberada ativa. Monitor `ok=1`.

Pendências: criar `painel.cursar.space`
(A `3.235.84.94`, **DNS only**) ou túnel com token; snapshot da VPS; Render/Supabase só
saem após 72 h estáveis no painel novo.
