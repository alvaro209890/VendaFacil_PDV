# 🪟 Gerar o VendaFácil PDV no Windows (passo a passo completo)

Guia de ponta a ponta para produzir o que o cliente recebe: do código até o
**instalador assinado**. Tudo isto roda **no Windows** (o `.exe` não pode ser
gerado no Linux/macOS — o PyInstaller não faz cross-compile, e o build do
frontend exige Node 20+).

> Resumo do pipeline: **build do .exe → empacotar no instalador → assinar →
> distribuir.**

---

## ⚡ Opção mais fácil: build automático na nuvem (GitHub Actions)

Você **não precisa instalar nada** na sua máquina. O repositório tem um workflow
(`.github/workflows/build-exe.yml`) que **gera o `.exe` + instalador a cada
push** num runner Windows da GitHub.

- **Onde baixar:** aba **Actions** do repositório → abra a execução mais recente
  → seção **Artifacts** → baixe **VendaFacilPDV** (contém o `VendaFacilPDV-Setup-*.exe`).
- **Release versionada:** crie uma tag `vX.Y.Z` (`git tag v1.0.0 && git push --tags`)
  → o instalador é anexado automaticamente em **Releases**.
- **Conectar ao painel:** em *Settings → Secrets and variables → Actions →
  Variables*, crie a variável **`PAINEL_URL`** com a URL do Render. O .exe sai
  já "conectado". Sem ela, sai em **modo local**.

Se preferir gerar localmente (ou ajustar detalhes), siga o passo a passo manual
abaixo.

---

## 0) Pré-requisitos (instalar uma vez)

| Ferramenta | Para quê | Link |
|---|---|---|
| **Node.js 20+** | buildar o frontend React | https://nodejs.org |
| **Python 3.10+** | backend + PyInstaller (marque "Add to PATH") | https://python.org |
| **Inno Setup 6** | gerar o instalador | https://jrsoftware.org/isdl.php |

Baixe o projeto (git clone ou ZIP) numa pasta, ex.: `C:\VendaFacil_PDV`.

---

## 1) (Opcional) Conectar ao Painel antes de buildar

Se cada `.exe` deve já sair "ligado" ao seu Painel (controle de licença), edite
**`backend/painel_config.py`** e ponha a URL do Render:

```python
PAINEL_URL = "https://vendafacil-painel.onrender.com"
```

Deixe `""` para distribuir em **modo local** (sem controle central de licença).

---

## 2) Gerar o executável (.exe)

Na raiz do projeto, dê dois cliques em **`build_exe.bat`** (ou rode no Prompt):

```bat
build_exe.bat
```

Ele faz: `npm install` → `npm run build` → cria a venv → instala
`requirements-build.txt` → roda o PyInstaller.

**Resultado:** `dist_exe\VendaFacilPDV.exe` (executável único).

> Já dá para testar aqui: dois cliques no `VendaFacilPDV.exe` → o sistema sobe e
> abre o navegador em `http://127.0.0.1:3020/`. O banco fica em
> `%LOCALAPPDATA%\VendaFacilPDV\dados\vendafacil.db`.

O executável já sai com o ícone oficial do VendaFácil PDV definido em
`installer\vendafacil.ico`.

---

## 3) Gerar o instalador (Inno Setup)

Dê dois cliques em **`installer\build_installer.bat`** (ou abra
`installer\vendafacil.iss` no Inno Setup e clique em *Compile*).

Antes, edite o topo do `installer\vendafacil.iss` com os seus dados:
`AppPublisher` (empresa), `AppURL` (site) e, se tiver, `SetupIconFile` (ícone).

**Resultado:** `dist_installer\VendaFacilPDV-Setup-1.0.2.exe` — **este é o
arquivo que você entrega ao lojista.** Ele instala em Program Files, cria
atalho no Menu Iniciar e na Área de Trabalho, e registra o desinstalador.
O instalador também usa o mesmo ícone oficial do app.
Em atualizações, ele reutiliza a pasta instalada anteriormente, encerra o
`VendaFacilPDV.exe` antigo se estiver aberto e copia a nova versão por cima.
Se o Windows ainda segurar o arquivo, agenda a substituição para o próximo
reinício em vez de quebrar a atualização.

> O banco do lojista fica em `%LOCALAPPDATA%\VendaFacilPDV\dados` — sobrevive a
> reinstalações/atualizações e **não** é apagado ao desinstalar (proposital,
> para não perder vendas).

---

## 4) Aviso do Windows SmartScreen (sem assinatura)

> **Decisão atual: NÃO assinamos o executável** (assinatura de código não é
> essencial agora).

Como o instalador não é assinado, na 1ª execução o Windows pode mostrar uma
tela azul do **SmartScreen** ("O Windows protegeu o seu PC"). É normal para apps
sem certificado. Para abrir: clique em **"Mais informações" → "Executar assim
mesmo"**. Vale orientar o lojista sobre isso (ou mande um print no manual).

Se um dia quiser eliminar esse aviso, basta comprar um **certificado de Code
Signing** e assinar o `.exe` e o instalador com o `signtool` — mas isso fica
para depois, não bloqueia a venda.

---

## 5) Distribuir

Entregue o **`VendaFacilPDV-Setup-x.y.z.exe`**.
Canais comuns: link de download no seu site, Google Drive, ou e-mail.

Ao instalar, o lojista:
1. Abre o sistema pelo atalho.
2. Informa o login/senha que **você** criou no Painel (se usar controle central).
3. Configura a maquininha em **Maquininha** e o fiscal em **Fiscal**, se for usar.

---

## 🔁 Lançar uma nova versão

1. Atualize a versão em `installer\vendafacil.iss` (`AppVersion`).
2. Refaça os passos 2 → 3 → 4.
3. Entregue o novo `Setup`. O instalador atualiza por cima, preservando os dados.

> Não há auto-update embutido ainda — a atualização é reinstalar por cima com o
> novo Setup. (Item da lista de evolução em `CHECKLIST_COMERCIALIZACAO.md`.)

---

## ❓ Por que não dá para gerar o .exe no Linux (onde o projeto foi desenvolvido)?

- O **PyInstaller não faz cross-compile**: ele gera um binário do **mesmo SO**
  em que roda. No Linux sai um binário Linux; só **no Windows** sai o `.exe`.
- O **build do frontend** exige **Node 20+** (o ambiente de desenvolvimento
  usado tinha Node 18, que o Vite recusa).

Por isso este guia: o código está pronto e testado; o empacotamento final é
feito por você, na máquina Windows.
