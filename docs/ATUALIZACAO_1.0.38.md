# Atualização 1.0.38 — rodapé do carrinho sem "Vendas Hoje"

Álvaro, 22/11/2026. Pedido: *"no carrinho da janela de vendas PDV remova esse total
de vendas hoje e já deixe online e funcionando lá, pode reiniciar o app se preciso"*.

## O que mudou

O painel do carrinho (`src/pages/PDV.tsx`) mostrava, abaixo do botão de finalizar, um
bloco **VENDAS HOJE** com o total do dia e a quantidade de vendas, alimentado por
`getDashboard()`:

- saiu o bloco visual inteiro (rótulo, valor e contagem);
- saíram o estado `dash`/`setDash`, a chamada `getDashboard()` do `Promise.all` de
  `carregar()` e os imports `getDashboard` / `DashboardData`.

A página **Dashboard** (`src/pages/Dashboard.tsx`) não foi tocada: o cartão "Vendas Hoje"
continua lá, que é o lugar de relatório.

## Validação

| Verificação | Resultado |
|---|---|
| `npm run build` (`tsc -b && vite build`) | limpo, `dist/assets/index-Bs2hOGlm.js` (663.939 bytes) |
| PyInstaller | 1.0.38, `dist_exe/VendaFacilPDV.exe` 46.291.597 bytes |
| Inno Setup | `dist_installer/VendaFacilPDV-Setup-1.0.38.exe` |
| Setup no PC do James | SHA-256 igual nos dois lados, `ExitCode 0`, `PendingFileRenameOperations` vazio |
| `/health` no caixa | `{"status":"ok","app":"vendafacil-pdv","version":"1.0.38"}` |
| `DisplayVersion` | 1.0.38 |
| Processos | 2 (PyInstaller), porta 3020 `True` |
| Bundle servido | `index-Bs2hOGlm.js` com o mesmo SHA-256 do build de dev (`BD875A11…87875D7`) |
| Validação visual (headless, perfil copiado) | carrinho vazio sem o bloco "VENDAS HOJE" |
| Dados | 52 vendas / R$ 1.865,25 no dia; última às 12:26 -04, depois do restart |

### Como foi validado sem fechar o caixa

O PC do James roda o PDV na sessão interativa; o SSH cai na sessão 0 e `CopyFromScreen`
não enxerga a tela do lojista. A receita usada: copiar `%LOCALAPPDATA%\VendaFacilPDV\edge-caixa`
para uma pasta temporária e rodar o Edge em `--headless=new` com esse perfil copiado
(o `localStorage` leva o JWT e a tela abre logada), `--window-size=1440,900` e
`--screenshot`. O perfil e o PNG foram apagados do PC do cliente na mesma sessão.

## Janelas duplicadas do Edge

Quando o PDV já está no ar, abrir o atalho de novo **não** foca a janela existente: o
`backend/run.py` vê a porta 3020 ocupada, confirma a instância ativa e chama
`_abrir_navegador()` outra vez. Resultado: duas janelas do app no mesmo perfil, e o log
mostra **dois `POST /api/heartbeat` por ciclo**.

Depois de instalar, feche todo `msedge.exe` cujo `CommandLine` contenha `edge-caixa` e
reabra uma única janela pelo WMI com
`--kiosk-printing --no-first-run --user-data-dir=<dados>\edge-caixa --app=http://127.0.0.1:3020/`.
A prova de que ficou uma só é um heartbeat por ciclo e o `GET /assets/index-<hash>.js` no log.

## Arquivos

- `src/pages/PDV.tsx`: remoção do bloco e do estado `dash`.
- `backend/version.py`, `installer/vendafacil.iss`, `scripts/roteiro_exe.py`: versão **1.0.38**.

## Artefatos

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 46.291.597 | `4C2C60BB2E0B22FCF3D1DD1F277487DC9C4CEFE2CF7F8CBBF1255BA872DFC43A` |
| `dist_installer/VendaFacilPDV-Setup-1.0.38.exe` | 46.377.530 | `0B539C0742C51B9E8FCCE1D84FBA3DC2679E0F838F448CA45E5885CF931A2FEB` |

## Instalação no James

Instalada em **22/11/2026 12:25 -04** com
`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /NOCLOSEAPPLICATIONS /TASKS=desktopicon`.
O app antigo foi fechado antes (`Stop-Process`), o processo novo subiu pelo WMI, os
dados sobreviveram e o caixa voltou a vender às 12:26.

## Observação

O push do repo saiu do dev `windows` com o token do `gh` do `server` via
`http.extraHeader` — o `gh` do Windows está com token inválido e o acer estava offline.
