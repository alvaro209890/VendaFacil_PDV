# Remover produtos antes do pagamento — 1.0.21

Codex, 14/11/2026. Solicitação do Álvaro para a venda durante a leitura do leitor.

- Cada linha do carrinho tem botão visível **− Remover**, para retirar toda a
  linha da compra, seja produto antigo ou cadastrado na hora.
- O **−** da quantidade diminui um passo; ao chegar a zero, retira a linha.
- Totais e rascunho são atualizados, sem baixar estoque ou registrar venda.
  O foco retorna ao campo do leitor para continuar escaneando.
- Ao remover o último item, limpa desconto e dados de pagamento da compra vazia.
- Na janela de produto não cadastrado/sem estoque/sem preço, **− Não vender este
  produto** pula o código atual e mantém os demais produtos da compra, sem criar
  cadastro nem dar entrada de estoque. Esc também fecha a janela. Enquanto uma
  gravação iniciada está em andamento, o fechamento aguarda seu término.
- Retirar da compra não apaga o cadastro do produto ou a entrada já feita.
  Caixa e avulso são linhas separadas; remover uma preserva a outra.
- Os controles de edição ficam bloqueados durante pagamento e após aprovação
  pendente de concluir a venda. O cancelamento da cobrança Point continua sendo
  um fluxo separado; esta entrega não altera o bloqueio externo 403.

O usuário esclareceu que "online" significa fechar e reabrir o PDV no PC com a
atualização; não solicitou hospedagem web ou alteração do painel administrativo.

## Entrega e provas

**James:** instalada em `C:\Program Files\VendaFacilPDV`, Setup **ExitCode 0**,
hashes conferidos localmente e após SCP, tarefa **VendaFacilPDV Running**, porta
3020 **True** e `/health` **1.0.21**. Banco com integridade **ok**, contagens
antes/depois iguais e backups anteriores preservados por SHA-256. Novo backup
`vendafacil-apos-1.0.21-20261114-145021.db`, 249.856 bytes, integridade ok.
Licença, token, A1 e homologação preservados. O bundle servido pelo próprio James
contém os novos controles do carrinho. Provas em `output/james/18-instalar-1.0.21-evidencia.txt`
e `19-aceite-1.0.21-evidencia.txt`; JSON/log também no cliente em
`C:\ProgramData\VendaFacil\evidencias-1.0.21`.

**PCQUE001IMAP:** o serviço aberto na 3020 ainda era 1.0.14, usando Python 3.11.
Foi parado e reiniciado na **1.0.21** com `backend/.venv/Scripts/python.exe`,
mantendo `C:\GIS\VendaFacil_PDV\dados` e o launcher local existente. Integridade
ok, contagens preservadas e backups antes/depois em `dados/backups`. O Python
antigo não tinha qrcode; a troca usa as dependências do projeto já validadas,
sem instalar pacotes globais. `/health` e o bundle atualizado conferidos.
A abertura no desktop foi solicitada pelo próprio exe em tarefa temporária
com InteractiveToken do mesmo usuário, ExitCode 0; tarefa removida. Controle
visual indisponível nesta sessão, portanto sem foto da janela real. Provas:
`output/james/local-1.0.21-evidencia.json` e `abertura-local-21.json`.

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| Executável | 39.732.482 | `1A5F42A790A5755188F4FA75C4A4760951C5D6F505FA155EE4A00DDE51968605` |
| Setup 1.0.21 | 40.019.380 | `0D705A7E4052126A3EF34BD3774D1CBE6460B1D56E8396854D0EE025C92AF6D9` |

## Validação

- Build TypeScript/Vite e ESLint aprovados.
- Navegador: **48 testes** de carrinho, cadastro rápido, foco/leitor, teclado,
  quantidades, decimais e embalagem aprovados; **46 Node** e **3 versão/embalagem**.
- Playwright CLI no fonte e no **exe real**, com banco temporário: compra mista,
  pular desconhecido sem gravar, cadastro em andamento protegido, remoção do novo
  preservando cadastro/estoque, diminuir/remover última unidade, fracionado,
  caixa/avulso separados, rascunho sem ressuscitar removidos, foco no leitor,
  mobile e checkout contendo somente o produto mantido. Estoque só baixou no
  checkout do item mantido, sem terminal/certificado/SEFAZ reais.
- Aceite do binário para fiado/PIX: **20 requisições, 0 erros 5xx**, incluindo
  persistência após reinício. Suite integral da 1.0.19 não repetida nesta rodada.
- Imagens de interface em `output/james/remover-1.0.21-binario-desktop.png` e
  `remover-1.0.21-binario-mobile.png` (fixtures, não dados do cliente).

As pendências anteriores de Point 403, IE de homologação 230 e leitura QR do
aparelho não foram reabertas nesta entrega. Nenhuma venda real foi criada ou
cancelada nos bancos do usuário nesta rodada. Fonte e docs serão registrados
no master, sem PR/push.
