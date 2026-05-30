# 📦 Gerar o VendaFácil PDV como executável (.exe)

O sistema foi adaptado para rodar **100% local** num único executável: o
backend FastAPI sobe embutido, serve o próprio frontend React e abre o
navegador no PDV. **Funciona offline** — ideal para o caixa de um mercado.

- Banco de dados: arquivo `dados/vendafacil.db`, criado **ao lado do executável**.
- Segredo de login (JWT): `dados/jwt_secret.key`, gerado no primeiro uso e
  reaproveitado (ninguém é deslogado ao reiniciar).
- Porta padrão: `3020` → o app abre `http://127.0.0.1:3020/`.

---

## ⚠️ Importante: o .exe é gerado NO Windows

O PyInstaller **não faz cross-compile**. Cada sistema gera o binário do seu
próprio SO:

| Onde você roda o build | Artefato gerado |
|------------------------|-----------------|
| **Windows**            | `VendaFacilPDV.exe`  ✅ (o que o mercado usa) |
| Linux                  | binário Linux `VendaFacilPDV` |
| macOS                  | binário/app macOS |

Para entregar o `.exe` ao mercado, **rode o build numa máquina Windows**.

---

## 🔗 Antes de buildar: conectar ao Painel SaaS

Se você usa o **Painel SaaS** (controle central de login/licença na VPS), edite
**`backend/painel_config.py`** e coloque a URL do seu painel **antes** de gerar
o `.exe`:

```python
PAINEL_URL = "https://painel.seudominio.com"
```

Assim cada `.exe` já sai "conectado" — a loja só precisa informar o login/senha
que você criou no painel. Deixe `""` para distribuir em **modo local** (sem
controle central). Veja `deploy/painel-vps/README.md` para subir o painel.

---

## 🪟 Gerar o .exe no Windows

Pré-requisitos (instalar uma vez):
- [Node.js 20+](https://nodejs.org)
- [Python 3.10+](https://python.org) (marque "Add to PATH" no instalador)

Depois, na raiz do projeto:

```bat
build_exe.bat
```

Pronto. O arquivo final fica em **`dist_exe\VendaFacilPDV.exe`**. Esse é o
único arquivo que você entrega — dois cliques e o sistema abre.

> Na primeira execução o Windows SmartScreen pode avisar que é de "editor
> desconhecido" (normal para apps sem assinatura digital). Basta
> "Mais informações" → "Executar assim mesmo". **Decidimos não assinar** o .exe
> por enquanto — não é essencial.

---

## 🐧 Gerar/testar no Linux

```bash
./build_exe.sh        # precisa de Node 20+ ativo (ex: nvm use 20)
./dist_exe/VendaFacilPDV
```

---

## ⚙️ Variáveis de ambiente (opcionais)

| Variável | Padrão | Para quê |
|----------|--------|----------|
| `VENDAFACIL_PORT` | `3020` | Trocar a porta |
| `VENDAFACIL_HOST` | `127.0.0.1` | Use `0.0.0.0` para acessar de outro PC da rede |
| `VENDAFACIL_NO_BROWSER` | — | `=1` não abre o navegador automaticamente |
| `VENDAFACIL_DATA_DIR` | `dados/` (ao lado do exe) | Mudar onde fica o banco |
| `VENDAFACIL_JWT_SECRET` | gerado em arquivo | Fixar o segredo (útil no Render) |
| `VENDAFACIL_PIX_KEY` | vazio | Chave PIX para gerar QR Code |
| `VENDAFACIL_MERCHANT_NAME` / `_CITY` | VendaFacil PDV / Querencia | Dados do recebedor PIX |

---

## ☁️ E o Render + domínio (acesso remoto opcional)

O mesmo código roda no Render sem alterações. Lá você define no ambiente:

- `VENDAFACIL_DATA_DIR` apontando para um disco persistente
- `VENDAFACIL_JWT_SECRET` (um valor fixo seu)
- `VENDAFACIL_HOST=0.0.0.0` e a porta que o Render injeta

E aponta **seu domínio** direto para o serviço do Render (CNAME). Nesse cenário
o **Cloudflare Tunnel não é necessário** — ele só serviria se você fosse
hospedar o backend na sua própria máquina em vez do Render.

> Atenção: a versão local (.exe) e a versão no Render têm **bancos separados**.
> Sincronizar os dois é um passo extra (modelo híbrido) que ainda não existe.
