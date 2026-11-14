# Instalação e aceite no PC do James — 1.0.19

Responsável: Codex, 14/11/2026. Autorizado pelo Álvaro nesta sessão.

## Escopo e situação inicial

Atualizar o PDV, preservar banco/backups e configurar EPSON TM-T20, Mercado Pago
Point e fiscal em homologação. Produção fiscal depende de Álvaro e contador.
Segredos permanecem no PC James e não integram este relatório.

Conexão SSH confirmou hostname James. Na inspeção inicial, a porta 3020 estava
fechada e não havia processo VendaFacilPDV. A ação da tarefa existente tinha
`Execute=C:\Program` e o restante do caminho em Arguments; foi corrigida para
o caminho completo. Banco e backup existentes foram encontrados.

A fila `EPSON TM-T20 Receipt5` já existia em USB001 com o driver correto; foi
renomeada e definida como padrão, evitando criar uma fila duplicada.

Álvaro informou que não há pessoa no local para aprovar um débito e conferir
fisicamente o cupom. Esses dois aceites exigem presença e não serão simulados.

## Artefatos conferidos antes da instalação

| Artefato | SHA-256 |
|---|---|
| Setup 1.0.19 | `7BBC9B37F0309ACD06D9310F892B828885D37D2DFB09346976287766C897B0C9` |
| Executável 1.0.19 | `B772D976837F6D5D60C9450A014393FDBE1F364D6ACACC633851AB138BFBE80A` |

Build e testes desta versão: [validação do fiado](VALIDACAO_FIADO_1.0.19.md).
Fonte registrada no `master`: `76c8cc1` (CRC PIX) e `4a0ea66` (fiado 1.0.19).
Sem PR ou push nesta rodada.

## Aceite observado

| Item | Resultado e prova |
|---|---|
| 1. Versão e hash | **1.0.19 instalada**. Hashes locais e no James iguais aos da tabela; Setup terminou `ExitCode=0`. `02-instalar-evidencia.txt`. |
| 2. Porta | `Test-NetConnection 127.0.0.1 -Port 3020 -InformationLevel Quiet = True`; `GET /health` retorna `version=1.0.19`. `13-aceite-final-evidencia.txt`. |
| 3. Tarefa | `VendaFacilPDV`: **Running**, habilitada, um gatilho de logon; Execute aponta para o caminho completo do exe. Mesmo arquivo de evidência. |
| 4. Banco e backups | Integridade SQLite **ok**. Contagens antes/depois da instalação iguais; backup anterior preservado por hash. Backup novo `vendafacil-apos-1.0.19-20261114-134342.db`, 249.856 bytes, integridade **ok**, no PC do cliente. `02` e `13`. |
| 5. Token | API local retorna `access_token_preenchido=true`; comparação no próprio James confirmou token do banco igual ao arquivo canônico. Valor nunca exportado. `03`, `04` e `09`. |
| 6. Terminal | `NEWLAND_N950__N950NCC904676430`, modo **PDV**, confirmado após `PATCH /terminals/v1/setup` e diagnóstico local. A PAX da conta não foi alterada. `04-point-impressora-evidencia.txt`. |
| 7. Débito de R$ 1 | **Bloqueado**: API local e chamada direta a `POST /v1/orders` retornaram HTTP **403**, `PA_UNAUTHORIZED_RESULT_FROM_POLICIES`, `blocked_by=PolicyAgent`, `At least one policy returned UNAUTHORIZED.` **Nenhuma order/ID foi criada**, nem débito aprovado ou cancelado. `07` e `09`. |
| 8. Impressora | `EPSON TM-T20`, driver `EPSON TM-T20 Receipt5`, porta `USB001`. `SetDefaultPrinter` retornou sucesso e `GetDefaultPrinter` retornou o nome da Epson. PrintTicket **80000 × 297000 µm**. `04` e `14`. |
| 9. Cupom | Cupom não fiscal da venda de teste nº 1, R$ 1,00/dinheiro, gerado pelo mesmo código do app e conferido em PNG/PDF de 80 mm. Diagnóstico enviado ao spooler como imagem: evento **307**, job **2**, **38.744 bytes**, USB001, fila vazia ao final. Evento informa 0 páginas; **não substitui foto nem leitura do papel**. Foto, chave/QR no papel e impressão pelo Edge permanecem sem aceite físico. `12-impressao-evidencia.txt`, `14-spooler-evidencia.txt`, `cupom-teste.png` e `cupom-teste.pdf`. |
| 10. Pendências | Autorização de criação de orders no Mercado Pago; aprovação/estorno de R$ 1 na Point com pessoa no local; cadastro da IE no ambiente de homologação da SEFAZ; foto e leitura do cupom/QR na Epson. Produção fiscal depende de Álvaro e contador. |

Evidências sanitizadas em `C:\GIS\VendaFacil_PDV\output\james` (fora do Git).
No James, relatórios JSON e log do instalador estão em
`C:\ProgramData\VendaFacil\evidencias-1.0.19`, sem token, CSC ou senha do A1.
Os bancos/backups com a configuração continuam somente no James.

## Fiscal em homologação

Dados empresariais conferidos visualmente no CCE: CNPJ 42.115.849/0001-50,
IE 13.876.189-2, CNAE 4729699, CRT 1, Querência-MT 5107065, CEP 78643-000,
R LOCAL 04, 750, GREENVILLE II. A1 importado do arquivo original no James, com
chave privada, CNPJ correspondente e validade até **01/04/2027**. Senha obtida
somente em memória no próprio PC; nome do arquivo e segredo não foram exportados.

`GET /api/fiscal/servicos/status`: **cStat 107**, Serviço em Operação.
NFC-e nº 1/série 1 em homologação: lote **104**, documento **230**,
**Rejeição: IE do emitente não cadastrada** (códigos extraídos do XML de retorno
persistido no banco). Não houve autorização fiscal. Venda nº 1 cancelada e
produto de teste desativado; histórico preservado.

Configurado **QR Code v3**, suportado pelo emissor e sem uso de CSC. O JPEG do
CSC teve OCR inconclusivo e seu conteúdo não foi importado nem copiado para fora
do PC. Chave/QR em cupom autorizado dependem de resolver o cadastro da IE; o
recibo de diagnóstico é explicitamente não fiscal e de venda cancelada.

## Impressão, inicialização e limpeza

O cupom do app usa `@page margin:0`, largura 80 mm, e chave em blocos de quatro
quando há nota. O Edge foi configurado sem cabeçalho/rodapé, com a impressora
padrão do sistema. Criado no desktop o atalho **VendaFacil - caixa com impressao
direta**, com `--kiosk-printing` e perfil dedicado em
`%LOCALAPPDATA%\VendaFacilPDV\edge-caixa` (80 mm, margem zero). Iniciar o PDV
antes de usar esse atalho; o perfil pede login da loja no primeiro uso.

O teste de abertura/impressão pelo Edge retornou código 0, mas sem evento de
impressão: esse caminho não foi declarado aprovado. O diagnóstico posterior
pelo spooler confirmou o envio da imagem do cupom à fila/driver.

Fuso alterado de Brasília (-03) para `Central Brazilian Standard Time` (Cuiabá,
-04). Login James feito pelo Álvaro; ativação **ativa e não bloqueada**. A senha
não foi trocada.

Limpeza confirmada: **EdgeCDP removida**, sem listener em **9222**, pastas
`C:\Temp\apd_extract` e `C:\Temp\drivers` removidas após verificar os caminhos,
**7-Zip desinstalado (ExitCode=0)**, tarefas temporárias removidas. Nenhum arquivo
com nome de token em `C:\Temp`; arquivo canônico protegido preservado. Banco,
backups, documentos originais e Edge interativo do cliente preservados.

## Retomada dos aceites físicos

1. Resolver a autorização da aplicação/conta para `POST /v1/orders` com suporte
   do Mercado Pago usando o 403 registrado. Listagem de terminais, `users/me` e
   configuração PDV funcionam; a mesma credencial retorna 403 na criação tanto
   pelo PDV quanto por PowerShell independente.
2. Com operador/cartão, aprovar R$ 1 no débito e confirmar no PDV; guardar
   order/payment ID. Pagamento já aprovado exige reembolso pelo provedor;
   cancelar a venda local não estorna o cartão. A resposta ao `/cancel` de uma
   order não prova reembolso de pagamento aprovado.
3. Regularizar a IE de homologação com SEFAZ/contador e repetir a emissão;
   cancelar a nota de teste se for autorizada.
4. Abrir o atalho de impressão direta, entrar no perfil e imprimir um teste.
   Conferir loja, itens, total, forma, chave completa em blocos de quatro e QR
   lido por celular; guardar foto e cancelar a venda de teste.
