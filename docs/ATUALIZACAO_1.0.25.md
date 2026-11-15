# Atualização 1.0.25 — vídeo de importação dentro do PDV

Codex, 15/11/2026. Pedido do Álvaro: criar um vídeo ensinando a importar XML
e deixá-lo funcionando no sistema do James.

## Como assistir

**Produtos → Como importar XML? Assista ao vídeo** ou **Manual**, no topo.
O vídeo fica no próprio instalador: funciona sem internet, com narração em
português, legendas, controles de pausa/tela cheia e download. Os botões de
assunto pulam para produto cadastrado, caixa/unidade, preços e confirmação.
Ao escolher um assunto, a tela volta ao vídeo, inclusive no celular.

O tutorial de **283,66 s (aproximadamente 4min44)** mostra a interface real:
arquivo XML do fornecedor, selo de produto cadastrado, bebida que já veio
contada em UN, palheiro comprado em carteira, cerveja com dois preços,
seleção de itens, confirmação, estoque final, PDV e alteração de preço.
Usa dados sintéticos: bebida 54 + 54 = 108 UN; 2 carteiras com 20 = 40 palheiros;
2 caixas com 12 = 24 latas. Nenhuma gravação usa o estoque real do James.

## Arquivos

- `public/tutoriais/importar-xml.mp4`: 6.902.654 bytes, H.264 1600×900/20 fps,
  áudio AAC mono 48 kHz. SHA-256
  `4F67C5884C6F929104BACEA2597E018B719F8FC58BF9827FDB9215EA978D651E`.
- Pôster JPG, legendas/capítulos WebVTT e metadados JSON na mesma pasta.
- `scripts/tutorial_xml/`: roteiro, narração local Microsoft Maria, captura
  via Playwright CLI, montagem e verificação. Capturas e áudio brutos em
  `output/playwright/tutorial-xml/`.

## Validação

Decodificação integral do MP4 aprovada; 14 quadros de capítulos inspecionados;
formato, duração, trilha de voz e legendas conferidos. No player, reprodução
com som habilitado e avanço, seek de capítulo desktop/celular, vídeo com HTTP
206 e MIME `video/mp4`, legenda disponível. Rede externa bloqueada no teste.

| Verificação | Resultado |
|---|---|
| Navegador completo (inclui NF-e 446817 real, com banco temporário) | 105 aprovados |
| Build TypeScript/Vite e ESLint | aprovados; aviso anterior de tamanho do bundle permanece |
| Versão backend/instalador/roteiro | 3 testes aprovados |
| Player no fonte e no executável 1.0.25 | reprodução com avanço, capítulos desktop/celular, download por Range 206 e legendas aprovados |
| Áudio final | média −16,8 dBFS, pico −1,3 dBFS; faixa AAC presente, sem saturação |

O player começa pausado, com `preload="none"`. O teste do exe entrou pelo
atalho da tela Produtos, percorreu o capítulo de produto cadastrado e o de
caixa/unidade no celular; retornou ao início. Som estava habilitado e o tempo
avançou. Capturas: `output/playwright/tutorial-xml/player-*.png`.

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 46.265.575 | `0297DED8033129CB62A607816A0130D2A1D7D5F5DBDBBC375D258C03734833A6` |
| `dist_installer/VendaFacilPDV-Setup-1.0.25.exe` | 46.351.415 | `0170E0F2A66ACBF7AFABB63AF7365BC0B5DE055924EC98B59A11542223B24EC4` |

## Instalação e aceite no James

Instalada em **15/11/2026**, conferida às **00:27 -04 no cliente (01:27 -03)**.
Setup concluiu com código zero; exe/Setup com os mesmos hashes do build,
`/health` **1.0.25**, tarefa **Running**, 2 processos, licença ativa e sem bloqueio.

O cliente serviu o MP4 completo de 6.902.654 bytes com o mesmo SHA-256 do
arquivo revisado. Requisição parcial respondeu **206**, `video/mp4`,
`Content-Range: bytes 0-1023/6902654`; VTT começa com `WEBVTT`.
O JS servido contém o player e o atalho da tela Produtos.

Banco e backup íntegros. Contagens antes/depois iguais: 14 produtos (13 ativos),
1 usuário, 1 venda e 1 item; clientes/fiado vazios. **Todos os campos da tabela
de produtos foram comparados com o backup anterior e permaneceram idênticos**.

Backup: `%LOCALAPPDATA%\VendaFacilPDV\dados\backups\vendafacil-antes-1.0.25-20261115-002537.db`.
Evidência final no cliente: `C:\ProgramData\VendaFacil\evidencias-1.0.25\aceite-final.json`;
no desenvolvimento: `output/james/25-aceite-final.txt`.
A validação inicial parou numa comparação de texto acentuado do JS no
PowerShell; a validação final foi retomada sem reinstalar, conferindo os
arquivos/HTTP e comparando o banco com o backup.
