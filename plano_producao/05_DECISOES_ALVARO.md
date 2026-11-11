# Decisões do Álvaro

O agente **não decide** estes pontos. Aplica o padrão, registra na coluna "O que o agente fez" e segue. O Álvaro responde quando quiser, escrevendo na coluna "Resposta".

| # | Decisão | Padrão até ele responder | Pista | O que o agente fez | Resposta do Álvaro |
|---|---|---|---|---|---|
| D1 | Ir para `producao` | Ficar em `homologacao` | — | | |
| D2 | Tirar os binários do git | Não mexer; não commitar binário novo | P16 | | |
| D3 | Produto com preço de venda 0 é vendido pelo custo | Manter como está | P11 | Caracterizado em 997dd69, sem mudar código: 2×custo 1,50 = 3,00; preço 2 permanece 2. Suíte 150/7 | |
| D4 | Venda sem caixa aberto | Manter permitido; mostrar aviso no PDV | P4 | Aviso "Caixa fechado" no PDV sem desabilitar a finalização; venda continua 201 | |
| D5 | Impressão direta ESC/POS e abertura de gaveta | Não construir; impressão segue pelo navegador | P12 | | |
| D6 | Criptografar o cofre fiscal dentro do SQLite | Não; documentar o risco em `docs/SEGURANCA.md` | P14 | Documentado em docs/SEGURANCA.md; S05/S06 travam o não vazamento na API e no log | |
| D7 | Assinatura de código do `.exe` | Sem assinatura (aviso do SmartScreen é esperado) | — | | |
| D8 | Venda fiada cancelada depois de já ter recebido parte | Recusar o cancelamento e orientar a estornar o recebimento antes | P2 | Aplicado em4a7ff3e: parcial0,50 recusa409 e preserva estoque/fiado; suíte132/7 | |
| D9 | Mudar fluxo que o lojista já usa | Não mudar | — | | |

Decisão nova que aparecer no caminho: acrescente a linha (`D10`…), escolha o padrão **mais conservador** (o que não muda o comportamento atual) e registre.
