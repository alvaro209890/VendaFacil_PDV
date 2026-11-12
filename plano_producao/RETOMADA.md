# Retomada — Fase 3 concluída em 12/11/2026

Fases0–3 concluídas e publicadas. Push d9038dc conferido por ls-remote igual ao HEAD. F3.22=342f3d6; F3.21=31541bd/1f52324/f54b125; F3.19=fb9f5b9.

Gate: backend327/painel23, E2E82 (28+20+19+14+1), Node29, build/lint0. Próximo: Fase4 do primeiro item aberto; fases5–7 depois em ordem.

Recursos: a pedido do usuário, apenas uma execução pesada por vez; Chromium1 worker; não encerrar apps alheios. Subagentes autorizados: GPT-6 Luna high (substitui modelo antigo da regra local).

Árvore inicial: executável modificado, rascunho antigo, logsScratch/ e test_fiscal_owner.py não trackeado; teste foi revisado e commitado, demais preservados.

Histórico e instruções operacionais anteriores (o estado abaixo foi superado pelo painel atual):

# Retomada — estado real em 12/11/2026 09:45 BRT

> Leia junto com `00_PAINEL.md` (placar), `01_REGRAS.md` (regras duras) e `06_DIARIO.md` (histórico).
> Este arquivo responde só uma pergunta: **onde parou e o que fazer agora.**

## Onde parou

| Campo | Valor |
|---|---|
| HEAD local | `b5db49c` ou posterior — a série de 12/11 só acrescenta docs; confira com `git log -1` |
| Remoto | `origin/master` sincronizado em 12/11 (push a pedido do Álvaro; exceção consciente à regra 4, o portão da Fase 3 continua aberto) |
| Fases 0–2 | ✅ concluídas e publicadas |
| Fase 3 | 🟨 21/24 — faltam **F3.19**, **F3.21**, **F3.22** |
| Fases 4–7 | ⬜ não iniciadas (27 + 12 + 14 + 12 itens) |
| Placar | Pistas 28/46 · Testes 67/126 · Bloqueios ativos 0 · Decisões respondidas 0/9 |

## O que a sessão do Hermes deixou pronto (11–12/11)

| Item | Prova | Commit |
|---|---|---|
| F3.10 teclado/atalhos | 13 Chromium + 24 repetições | `dc0858d` |
| F3.11 foco no leitor | 5 casos U04 + 15 repetições | `b480a4a` |
| F3.12 decimais no caixa | 19 casos / 38 repetições | `bb36365` |
| F3.13 erros de backend na tela | 7 casos / 21 repetições | `bd6013e` |
| F3.14/F3.15 automação + build/lint | 41 casos U01–U04, build e eslint 0 | `c3cc1a3` |
| F3.17 segredos mascarados | 31 casos | `6535b18` |
| F3.24 log sem corpo bruto | 10 casos | `5da31fa` |
| F2.23 + I08 chave da NF-e na UI | 67 Chromium, 409 na repetição | `41c9265` |
| F3.18 XSS na impressão | 7 DOM verdes, review aprovado | `95e2322` |
| **F3.16 parser pt-BR** | **81 E2E em 4 lotes + 22 unitários + 29 Node** | **`a6a90d5`** |

Detalhe do F3.16: o código estava no working tree sem commit desde 11/11. Em 12/11 foi revisado, o lote A (carrinho + decimais) foi reexecutado 2× (28/28) e os quatro lotes fecharam os 81 testes. Evidência: `evidencias/F3_16_LOTE_A_GREEN.txt`.

## Gate global medido em 12/11 09:12–09:30 BRT

| Comando | Saída |
|---|---|
| `backend: pytest -q --tb=short` | **315 passed**, 3 warnings (35,65 s) |
| `painel: pytest -q --tb=short` | **9 passed**, 3 warnings |
| `npm run build` | exit 0 |
| `npx eslint .` | exit 0 |
| `node --experimental-strip-types --test frontend-tests/*.test.mjs` | 29 passed (7 recibo + 22 números) |
| E2E Playwright | 81/81: lote A 28, B 20, C 19, XML 14 |

## O que falta na Fase 3 (fazer nesta ordem)

| Item | Pista/Teste | O que é | Onde |
|---|---|---|---|
| F3.22 | P42 / S14 | validar dono da nota antes de ler, consultar ou cancelar | `backend/.../fiscal_router.py` |
| F3.21 | P41 / S13 | bootstrap de admin atômico, senha mínima no painel, troca de senha revoga tokens | `painel/main.py`, `painel/static/index.html` |
| F3.19 | P34 / U07 | total diário vindo do backend, sem truncar em 100 vendas, fuso MT | `src/pages/Vendas.tsx` + backend |

Depois: portão da fase (suítes + plano + `git push origin master`).

## Depois da Fase 3

| Fase | Itens | Natureza |
|---|---|---|
| 4 — Fiscal MT | 27 | Blocos A/B offline e simulador são obrigatórios; bloco C (SEFAZ real) depende de B1–B5 |
| 5 — Robustez/suporte | 12 | backup com integrity_check, diagnóstico, watchdog, porta ocupada |
| 6 — Build/instalador/E2E | 14 | `.exe`, instalador, teste em máquina limpa (B8 UAC) |
| 7 — Documentação/entrega | 12 | manual, checklist de instalação, treinamento (B9 presencial) |

## Bloqueios de terceiro (não travar a fase por eles)

B1 certificado A1 + senha · B2 CSC/ID homologação · B3 credenciamento SEFAZ-MT · B4 dados da empresa · B5 Mercado Pago produção · B6 maquininha · B7 impressora/leitor/gaveta · B8 UAC · B9 instalação presencial.

Enquanto faltarem, marcar `[!]` com a prova e seguir. **Nunca** inventar dado fiscal, usar certificado que não seja o da mercearia ou sair de `homologacao`.

## Decisões do Álvaro ainda sem resposta

D1 produção · D2 binários no git · D5 ESC/POS · D7 assinatura do `.exe` · D9 mudar fluxo do lojista. Aplicar o padrão conservador de `05_DECISOES_ALVARO.md` e registrar.

## Comandos que fecham item (sem inventar nada)

```powershell
cd C:\GIS\VendaFacil_PDV\backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short

cd C:\GIS\VendaFacil_PDV\painel
.venv\Scripts\python.exe -X utf8 -I -m pytest -q --tb=short

cd C:\GIS\VendaFacil_PDV
npm run build
npx eslint .
$env:TEMP='C:\Users\Usuario\AppData\Local\Temp\opencode\e2e_tmp'; $env:TMP=$env:TEMP; $env:TMPDIR='C:/Users/Usuario/AppData/Local/Temp/opencode/e2e_tmp'
npx playwright test e2e/carrinho.spec.ts e2e/decimais.spec.ts --reporter=line
# demais lotes: erros+foco+teclado | locale+produtos-locale+xml-idempotencia | xml-locale
```

A suíte E2E completa (81 testes, 1 worker) **não cabe** no limite de 350–600 s de uma ferramenta: rode em 4 lotes, como acima, e guarde a saída em `evidencias/`.

## Push (helper do sd, sem gravar segredo)

```powershell
cd C:\GIS\VendaFacil_PDV
git -c credential.helper='!sh "C:/Users/Usuario/AppData/Local/Temp/opencode/git-cred-sd.sh"' push origin master
```

O helper repassa `git credential fill` ao `sd` por SSH (`IdentityAgent=none`) e entrega a credencial direto ao git. Não imprime nem persiste nada. Se o `sd` estiver fora, **não** inventar caminho alternativo: registrar no diário e seguir.
