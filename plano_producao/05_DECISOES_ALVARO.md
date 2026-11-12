# Decisões do Álvaro

O agente **não decide** estes pontos. Aplica o padrão, registra na coluna "O que o agente fez" e segue. O Álvaro responde quando quiser, escrevendo na coluna "Resposta".

| # | Decisão | Padrão até ele responder | Pista | O que o agente fez | Resposta do Álvaro |
|---|---|---|---|---|---|
| D1 | Ir para `producao` | Ficar em `homologacao` | — | Ambiente mantido em `homologacao` em todas as fases; fixtures, simulador e roteiro do `.exe` só em homologação; precheck real com saída 2 (B1–B5) | 2026-11-12: confirmado. Homologação agora para os testes reais com os dados do contador da loja (cadastrados na tela Fiscal, não no chat); produção só depois da 1ª NFC-e autorizada em homologação. |
| D2 | Tirar os binários do git | Não mexer; não commitar binário novo | P16 | Binários antigos mantidos; nenhum binário novo commitado (`git status` só mostra `M dist_exe/VendaFacilPDV.exe`); CLAUDE.md passou a dizer isso (a60aa89) | 2026-11-12: **mudar** — remover do git os binários antigos (dist_exe/VendaFacilPDV.exe e Setups 1.0.3/1.0.10/1.0.11); entrega só pelo Setup validado. Pendente de implementação. |
| D3 | Produto com preço de venda 0 é vendido pelo custo | Manter como está | P11 | Caracterizado em 997dd69, sem mudar código: 2×custo 1,50 = 3,00; preço 2 permanece 2. Suíte 150/7 | 2026-11-12: **mudar** — bloquear a venda de produto com preço de venda 0 e pedir o preço. Pendente de implementação (com teste). |
| D4 | Venda sem caixa aberto | Manter permitido; mostrar aviso no PDV | P4 | Aviso "Caixa fechado" no PDV sem desabilitar a finalização; venda continua 201 | 2026-11-12: manter (vender com aviso de caixa fechado). |
| D5 | Impressão direta ESC/POS e abertura de gaveta | Não construir; impressão segue pelo navegador | P12 | Nada de ESC/POS; cupom do navegador validado em PDF 58/80 mm com QR decodificado (b41e946); papel fica em B7 | 2026-11-12: manter impressão pelo navegador; a térmica da loja já tem a gaveta, sem integração. |
| D6 | Criptografar o cofre fiscal dentro do SQLite | Não; documentar o risco em `docs/SEGURANCA.md` | P14 | Documentado em docs/SEGURANCA.md; S05/S06 travam o não vazamento na API e no log | 2026-11-12: manter sem criptografia (risco documentado em SEGURANCA.md). |
| D7 | Assinatura de código do `.exe` | Sem assinatura (aviso do SmartScreen é esperado) | — | 1.0.13 gerada sem assinatura; SmartScreen documentado em BUILD/INSTALACAO_WINDOWS | 2026-11-12: manter sem assinatura de código. |
| D8 | Venda fiada cancelada depois de já ter recebido parte | Recusar o cancelamento e orientar a estornar o recebimento antes | P2 | Aplicado em4a7ff3e: parcial0,50 recusa409 e preserva estoque/fiado; suíte132/7 | 2026-11-12: manter a recusa (estornar o recebimento antes de cancelar). |
| D9 | Mudar fluxo que o lojista já usa | Não mudar | — | Nenhum fluxo removido; só acréscimos: aviso de caixa fechado, reimpressão após contingência, botão Cancelar NFC-e, atalhos F3/F6/F7 | 2026-11-12: manter — só acrescentar, sem mudar fluxos que o lojista já usa. |

Decisão nova que aparecer no caminho: acrescente a linha (`D10`…), escolha o padrão **mais conservador** (o que não muda o comportamento atual) e registre.
