# Recebimento do fiado — 1.0.19

Implementado e validado localmente em 14/11/2026 (Codex).

- Recebimento parcial/total com Dinheiro, PIX, Débito ou Crédito; histórico mantém a forma.
- Cartão/PIX na Point com cobrança vinculada à conta, validação de aprovação/valor/forma/referência,
  reserva persistente, chave de idempotência estável e conciliação atômica sem duplicar a baixa.
- Falha de conexão permite retomar. Cancelamento assíncrono da Point só libera após estado final.
  Operações remotas rodam fora do loop principal do servidor.
- PIX da chave da loja gera QR Code e copia e cola com referência própria e fica salvo.
  Fechar a janela, mudar para o PDV ou reiniciar não perde o código nem bloqueia o sistema/terminal.
  A baixa depende de conferência manual do crédito; código estático enviado não pode ser revogado.
- Somente recebimento em dinheiro entra no esperado da gaveta. O CRC do BR Code foi corrigido
  e conferido com o vetor oficial do Banco Central (1D3D).

## Verificação

- Backend: **539 passed**, 9 testes de homologação real desmarcados.
- Frontend Node: **46 passed**; navegador integral: **98 passed**.
- Build TypeScript/Vite e ESLint: aprovados.
- Playwright CLI: geração, cópia, fechamento, acesso ao PDV e reabertura do mesmo PIX salvo;
  imagem em `output/playwright/fiado-pix.png`.
- Binário: `scripts/verificar_fiado_exe.py`, **20 requisições, 0 erros 5xx**; recebimento nas
  quatro formas, repetição sem duplicação, venda durante espera, dinheiro esperado e
  código preservado após reinício. Banco descartável e painel desabilitado só no teste.

## Artefatos locais

| Arquivo | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 39.731.014 | `B772D976837F6D5D60C9450A014393FDBE1F364D6ACACC633851AB138BFBE80A` |
| `dist_installer/VendaFacilPDV-Setup-1.0.19.exe` | 40.017.739 | `7BBC9B37F0309ACD06D9310F892B828885D37D2DFB09346976287766C897B0C9` |

Esta validação local não usou terminal, certificado ou SEFAZ reais. Na rodada
seguinte de 14/11, o Setup foi instalado no James e houve configuração real de
Point, A1 e homologação: veja [aceite do James](ACEITE_JAMES_1.0.19.md).
Point Orders retornou 403, SEFAZ retornou 230 e o aceite físico continua pendente.
Não houve publicação no GitHub ou envio por WhatsApp nesta rodada.
