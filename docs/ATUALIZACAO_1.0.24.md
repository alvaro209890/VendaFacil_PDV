# Atualização 1.0.24 — contagem da nota, formato de venda e preços

Codex, 15/11/2026. Continuação do pedido interrompido da Claude: separar a
caixa entregue pelo fornecedor da quantidade escrita na nota, facilitar
palheiro/cerveja avulsos e a edição dos produtos já cadastrados.

## Uso no balcão

Na prévia de XML, **Como a nota conta esta compra?** é uma pergunta separada
de **Como vende?**, disponível também nas reposições com estoque em UN.

| Compra | Resposta | Entrada |
|---|---|---|
| Bebida láctea, 54 UN a R$ 1,59, entregue em caixas | Em unidades soltas | 54 unidades; não multiplica |
| Palheiro, 2 carteiras a R$ 10, 20 palheiros em cada | Em embalagem fechada; 20 dentro | 40 unidades; custo R$ 0,50 |
| Cerveja, 600 UN a R$ 2,74, entregue em 50 caixas | Em unidades soltas | 600 latas; pode vender caixa e unidade |
| Venda apenas da caixa, nota já conta 24 unidades | Só a embalagem fechada; conferir estoque/custo | Ex.: 2 CX a R$ 24 por CX |

A reposição mantém os preços e o formato cadastrados. O operador vê essa
informação na prévia; para mudar esses dados, usa **Produtos → Editar**.
Nos produtos com dois formatos, o fator do cadastro aparece como leitura,
sem oferecer uma edição que o backend ignoraria.

Em **Produtos → Editar**, a pergunta **Como o cliente compra?** apresenta
**Somente unidade**, **Caixa e unidade** e **Somente embalagem fechada**.
Com dois formatos aparecem apenas os dois preços aplicáveis. Ao ativá-los
num produto cadastrado em UN, o código que já vendia a unidade continua
ligado à unidade; o código da caixa é preenchido separadamente.

Trocar apenas o preço mantém o formato e o estoque. Uma troca de unidade de
estoque (CX ↔ UN) exige conferir a contagem e o custo; o botão **Converter
estoque e custo pela embalagem** prepara a conta e só grava ao salvar.
Ex.: 2 CX com 12, custo R$ 24/CX → 24 UN a R$ 2/UN. A conversão inversa
recusa saldo com unidades soltas. Se há vendas não canceladas, o backend
impede mudar a unidade de estoque para preservar estornos; com base UN,
os formatos unidade e caixa+unidade e seus preços continuam editáveis.

## Verificação e entrega

| Verificação | Resultado |
|---|---|
| Backend completo | 557 aprovados; 9 de homologação real desmarcados |
| Navegador no fonte, com NF-e 446817 real | 105 aprovados |
| Testes auxiliares Node | 46 aprovados |
| Build TypeScript/Vite e ESLint | aprovados; aviso de tamanho do bundle permanece |
| Navegador no executável 1.0.24 | 13 aprovados, incluindo os quatro cenários novos e NF-e real |
| Roteiro comercial do executável | 49 requisições HTTP; zero respostas 5xx; reinício e carrinho conferidos |

Os testes usam bancos descartáveis e não importam notas nem criam vendas no
banco real do James. A rodada adicional dos quatro cenários novos passou após
acrescentar a conferência de reposição de produto com dois preços. O servidor
E2E do binário passou a ler a versão de `backend/version.py`, em vez de exigir
a antiga 1.0.21.

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `dist_exe/VendaFacilPDV.exe` | 39.737.023 | `21D0E5C3BC7AE21510A7E03C8419DF9F42F2A01EED47C94A62F491E86B9798D0` |
| `dist_installer/VendaFacilPDV-Setup-1.0.24.exe` | 40.023.893 | `38EA37F883F532BB9280391453242A73BF78168DA064229106A1EFDA2EA739A0` |

Manuais atualizados: tela **Manual**, `MANUAL.md`, `ESTOQUE_E_XML.md`,
`CAIXA_E_UNIDADE.md` e `TREINAMENTO_OPERADOR.md`.

## Instalação no James

Conferida em 15/11/2026 às 00:56 (-03), **14/11 às 23:56 no PC do James (-04)**:
Setup com hash conferido no cliente, instalação silenciosa **ExitCode 0**,
executável com o mesmo SHA-256 do build. `/health` retorna **1.0.24**; tarefa
`VendaFacilPDV` **Running**, logon **Interactive**, licença ativa e sem bloqueio.
O JS efetivamente servido contém as duas perguntas novas.

Antes/depois: **14 produtos (13 ativos), 1 usuário, 1 venda, 1 item de venda**;
clientes e contas/pagamentos de fiado vazios. A comparação de **todos os campos
dos produtos** foi idêntica. A bebida láctea segue com **54 UN**, custo exato
**R$ 1,5907**, venda **R$ 2,07**. Nenhuma conversão nem alteração de preço foi
aplicada aos produtos reais sem a escolha do operador.

Backup prévio íntegro:
`%LOCALAPPDATA%\VendaFacilPDV\dados\backups\vendafacil-antes-1.0.24-20261114-235527.db`.
Os backups anteriores também foram preservados por SHA-256 em
`C:\ProgramData\VendaFacil\evidencias-1.0.24\backups-anteriores`, inclusive para
preservar cópias que a retenção automática normal poderia rotacionar.

Guia rápido no desktop do James: **`Guia-caixa-unidade-1.0.24.txt`**. O manual
completo atualizado está no menu **Manual** do PDV. Evidência sanitizada no
cliente em `C:\ProgramData\VendaFacil\evidencias-1.0.24\instalacao-evidencia.json`;
no PC de desenvolvimento, `output/james/24-instalacao-evidencia.txt` e os logs
`output/qa-24-*.log`. O uso humano posterior continua sendo escolha do operador;
os testes de importação/venda foram executados em bancos descartáveis.
