# Tutorial de importação de XML

Produção local no Windows, com a interface real e dados sintéticos. Nenhuma
nota ou imagem da loja real faz parte do vídeo. Voz: Microsoft Maria Desktop,
pt-BR, pelo System.Speech instalado no Windows. Sem serviço externo de TTS.

Os arquivos finais em `public/tutoriais/` são distribuídos no instalador e
funcionam sem internet. MP4 H.264/AAC, 1600×900, 20 fps; legendas gravadas na
imagem e também em WebVTT; capítulos e pôster locais. Sem música de fundo.

## Regravar

Na raiz do repositório, inicie `node e2e/servidor.cjs` (usa banco temporário
na porta 3121 e Vite na 5173). Não use a instância real da porta 3020.

1. `python -X utf8 scripts/tutorial_xml/preparar.py` cria a conta de
   demonstração, a bebida com 54 UN e o XML sintético. Exige banco novo.
2. `powershell -File scripts/tutorial_xml/narrar.ps1` gera as falas por frase.
3. Abra a sessão `tutorial-pdv` com `npx --package @playwright/cli playwright-cli`,
   viewport 1440×720, faça login com a conta descartável e abra Produtos.
4. Use `video-start <arquivo> --size=1440x720 --fps=20 --cursor` e
   `video-stop`. Cena 01: lista inicial. Cena 02: botão Importar XML e comando
   `upload output/playwright/tutorial-xml/nota-demonstracao.xml`.
5. Inspecione o snapshot da prévia antes de usar os snippets. Rode `acoes.py`
   e `gravar.ps1 -Cenas 03,04,...` em ordem. Confira a lista após a cena 10 e
   os botões CX/unidade no PDV antes das cenas 13–14.
6. `python -X utf8 scripts/tutorial_xml/renderizar.py` monta o vídeo, equaliza
   a voz, gera legendas, pôster e `src/lib/tutorialXml.ts` com os atalhos.
7. `python -X utf8 scripts/tutorial_xml/verificar.py` decodifica todo o MP4,
   confere formato/duração/legendas e gera a folha de quadros para revisão.
8. Abra `/manual#tutorial-xml`, inspecione o snapshot e rode o snippet
   `validar-player.js` via `playwright-cli run-code --filename`. Verifica
   reprodução sem autoplay, avanço, capítulos, celular e HTTP Range 206,
   bloqueando acesso à rede externa. Repita no executável com banco temporário.

As capturas, WAVs e relatórios ficam em `output/playwright/tutorial-xml/`,
fora do Git. O vídeo final e o roteiro são versionados com o produto.
