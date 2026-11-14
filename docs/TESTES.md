# ✅ Testes automatizados

Há uma suíte de testes (pytest) cobrindo a lógica crítica do **PDV** e do
**Painel**. Eles usam um banco temporário (não tocam nos seus dados) e o
`TestClient` do FastAPI.

## O que é coberto

**PDV** (`backend/tests/`): saúde da API, checkout baixando estoque, bloqueio por
estoque insuficiente, entrada manual de estoque, importação de XML (criar/repor),
fluxo de caixa (abertura → venda → sangria → fechamento com diferença),
relatório de vendas e exportação de backup.

**Painel** (`painel/tests/`): setup/login do admin, login incorreto, CRUD de
contas, validação de conta do PDV, contas da matemática financeira, troca de
senha e proteção contra força-bruta (rate limit).

## Como rodar

Instale as dependências de teste (arquivo `requirements-dev.txt` na raiz) em
cada venv e rode o pytest na respectiva pasta. No Windows, sem `PYTHONPATH`
herdado e com `-X utf8 -I`:

```bat
:: PDV
backend\.venv\Scripts\python.exe -X utf8 -I -m pip install -r requirements-dev.txt
cd backend && .venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short && cd ..

:: Painel
painel\.venv\Scripts\python.exe -X utf8 -I -m pip install -r requirements-dev.txt
cd painel && .venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short && cd ..

:: Front
npm run build && npx eslint .
node --test frontend-tests/*.test.mjs
npx playwright test --workers=1
```

`backend/pytest.ini` desmarca os testes `homologacao` (SEFAZ-MT real): eles só
rodam com `-m homologacao` e com o certificado, o CSC e os dados da própria loja
no cofre. Em 12/11/2026: backend 460 verdes e 9 desmarcados, painel 23, Node 36,
E2E 91 (Chromium, 1 worker). O `.exe` é validado por `scripts/roteiro_exe.py`
(ver `TESTE_WINDOWS.md`).

> Rode em cada pasta separadamente (PDV e Painel têm, cada um, seu próprio
> `main.py`).
# Aceitação da embalagem e avulso — 1.0.15

Plano ativo desta entrega: `plano_embalagem/` (o plano de produção anterior é
histórico). A suíte usa SQLite temporário e não acessa o banco da loja.

```powershell
# Na raiz do repo, para o aceite na porta 3021:
$env:TEMP = [IO.Path]::GetTempPath()
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
$env:VF_E2E_API_PORT = '3021'
$env:VF_EMBALAGEM_API = 'http://127.0.0.1:3021'
# Opcional: arquivo NF-e já baixado, nunca um certificado:
$env:VF_XML_REAL = Join-Path $env:TEMP 'vf-nota.xml'
npx playwright test e2e/embalagem.spec.ts --workers=1

# Binário Windows extraído do artefato do Actions (não executa o instalador):
$env:VF_TEST_EXE = 'C:\caminho\extraido\dist_exe\VendaFacilPDV.exe'
npx playwright test --config playwright.exe.config.ts --workers=1
```

O segundo comando inicia o executável com banco temporário, painel vazio,
`VENDAFACIL_NO_BROWSER=1` e porta 3021; valida `/health` na versão 1.0.15.
Ambos os fluxos cadastram os dois preços, importam duas carteiras, vendem
1 carteira + 3 avulsos por R$ 26 (saldo 17) e recusam nova carteira. Também
cobrem fator com saldo e entrada manual. Com `VF_XML_REAL`, a NF-e 446817
deve conservar 600 UN, custo 2,74 e sugestão de venda 3,56. Não há SEFAZ.
Na suíte geral, remova `VF_E2E_API_PORT` e `VF_EMBALAGEM_API` para usar o harness
padrão em 3121: `npx playwright test --workers=1`.

Conferência independente em 14/11/2026, no PDV 1.0.15 com banco temporário,
porta 3021 e painel desligado: cadastro do palheiro (carteira R$ 20, 20 unidades,
avulso R$ 2); compra de 2 carteiras virou 40 unidades a R$ 0,50, com os preços
de venda mantidos; venda de 1 carteira + 3 avulsos totalizou R$ 26 e deixou
17 avulsos; a carteira seguinte foi recusada. A NF-e 446817 perguntou se a
Kaiser era embalagem, veio desmarcada e gravou 600 UN a R$ 2,74, venda R$ 3,56.

### Caixa e unidade — 1.0.16 (14/11/2026)

- `backend/tests/test_embalagem_kaiser.py`: NF-e 446817 reduzida (600 UN,
  vOutro 12,36, cEAN do pacote e cEANTrib da lata). Nota em UN marcada como
  CX 12 continua 600 latas (a 1.0.15 gravava 7.200); custo de aquisição 2,7606;
  nota em CX multiplica quando o operador diz; os dois códigos; casamento pelo
  código da lata; 409 quando o código da unidade é de outro produto.
- `backend/tests/test_fiscal_gtin.py`: GTIN válido ou SEM GTIN nos dois campos;
  caixa com GTIN da caixa e cEANTrib da lata; lata avulsa com o GTIN da lata;
  XSD da NFC-e com código interno.
- `backend/tests/test_embalagem_vendas.py`: caixa de 15 a R$ 60 e unidade a
  R$ 5; mensagem "tem 11 UN, pedido 1 CX (12 UN)".
- `frontend-tests/embalagem.test.mjs`: conta da tela (R$ 4,00 cada, economia
  R$ 15, lucro/margem, alertas de caixa mais cara e abaixo do custo).
- `e2e/embalagem.spec.ts` com `VF_XML_REAL`: a NF-e real grava 600 UN a
  R$ 2,7606 e venda R$ 3,59; importação como CX 12 + lata sem multiplicar,
  PDV bipa o código da caixa e o da lata e cobra R$ 51,40 (estoque 585).

Roteiro de API fora do repositório usado na conferência (banco temporário,
porta 3031): 1.0.15 = 33/36, 1.0.16 = 36/36. Detalhes em
[CAIXA_E_UNIDADE.md](CAIXA_E_UNIDADE.md) §7.
