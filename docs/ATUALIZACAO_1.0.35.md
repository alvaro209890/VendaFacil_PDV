# Atualização 1.0.35 — recibo imprime direto, sem janela de pré-visualização

Álvaro, 19/11/2026. Pedido: *"toda vez que finaliza uma venda ele abre uma janela e
tem que clicar para imprimir; faça não abrir mais essa janela e já imprimir direto"*.

## O que estava errado

O `.exe` abria o PDV com `webbrowser.open()` (`backend/run.py`), que entrega a URL
ao Edge **normal** — perfil padrão, sem nenhuma flag de impressão. O recibo é
impresso por `window.print()` num iframe oculto (`src/lib/recibo.ts`), então o
Edge abria a **pré-visualização de impressão** e o caixa precisava clicar em
"Imprimir" a cada venda.

Existia um atalho manual na área de trabalho ("VendaFacil - caixa com impressao
direta") com `--kiosk-printing`, mas o caixa abria o PDV pelo `.exe`/Edge normal,
que não usa esse atalho.

## Correção

`backend/run.py` agora abre o PDV numa **janela de app do Edge** com:

- `--kiosk-printing` → `window.print()` vai direto para a impressora padrão, sem
  pré-visualização e sem clique;
- `--user-data-dir=<dados>\edge-caixa` → perfil separado, para um Edge já aberto
  não engolir a janela e ignorar a flag (o perfil existente do atalho antigo é
  reaproveitado, então as preferências locais continuam);
- `--app=http://127.0.0.1:3020/` → janela sem abas/barra de endereço, como caixa.

Se o Edge não estiver instalado, cai no navegador padrão (com diálogo), como antes.

## Validação

| Verificação | Resultado |
|---|---|
| Mesmo mecanismo do PDV (iframe oculto + `iframe.print()`) no Chrome 158 do acer, com impressora IPP virtual | **trabalho enviado à fila sem diálogo** (`TESTE-IFRAME-1017`, 86 KB no spool) |
| `build_exe.bat` | limpo, `dist_exe\VendaFacilPDV.exe` 1.0.35 |
| `.exe` 1.0.35 na porta 3022 com dados descartáveis | `/health` = **1.0.35** |
| Launcher no Windows | processo do Edge com `--kiosk-printing --app=http://127.0.0.1:3022/` confirmado na linha de comando |
| `installer\build_installer.bat` | instalador 1.0.35 gerado |

O teste do recibo na EPSON TM-T20 do James fica para a primeira venda depois da
instalação (o backend não registra impressão; o papel é a prova).

## Arquivos

- `backend/run.py`: `_caminho_edge()` e `_abrir_navegador()` em modo app +
  `--kiosk-printing`, com fallback para o navegador padrão.
- `backend/version.py`, `installer/vendafacil.iss`, `scripts/roteiro_exe.py`:
  versão **1.0.35**.

## Artefatos

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 46.281.736 | `9D570BCE671E1187B1725EBD5B2DFBEFAF02089EF62F6E1900F54E2204FC6269` |
| `dist_installer/VendaFacilPDV-Setup-1.0.35.exe` | 46.368.069 | `D776691E442A7753B350E61EC83A0BC9387C5782FDF4A220E04838CCB37566D9` |

## Instalação no James

Instalada em **19/11/2026 15:38** com `/VERYSILENT /FORCECLOSEAPPLICATIONS
/TASKS="desktopicon"`, hash conferido nos dois lados (mesmo SHA-256). A primeira
tentativa ficou presa no fechamento do processo antigo (rodava na sessão 0, sem
janela); a segunda, com `/FORCECLOSEAPPLICATIONS`, terminou com código 0.

O servidor foi aberto na sessão interativa do James (tarefa agendada
`VendaFacilAbrirJanela`, "somente quando o usuário está conectado"), então o
`/health` responde **1.0.35** e a janela é a de app:

| Janela | Processo | Título |
|---|---|---|
| Nova (kiosk) | 2944 | `VendaFácil PDV` |
| Antiga (Edge normal) | 5880 | `VendaFácil PDV - Pessoal - Microsoft Edge` |

A aba antiga do Edge normal deve ser fechada: nela a pré-visualização continua
aparecendo. A janela nova é a que imprime direto.

## Observação

`--kiosk-printing` manda o recibo para a **impressora padrão do Windows**. Se
alguém trocar a padrão para "Microsoft Print to PDF", a impressão para de sair
sem clique — mantenha a EPSON TM-T20 como padrão.
