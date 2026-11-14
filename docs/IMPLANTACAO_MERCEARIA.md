# Implantação na mercearia — roteiro item a item

Para quem vai instalar o VendaFácil PDV 1.0.17 no caixa da loja. Cada item tem a
**evidência a colher** (foto, print ou anotação). Guarde as evidências numa pasta
com a data da implantação.

Tempo estimado: 2 a 3 horas, sem contar o cadastro completo de produtos.

| # | Etapa | Como fazer | Evidência a colher |
|---|---|---|---|
| 1 | Conferir o instalador | No PC, em PowerShell: `Get-FileHash .\VendaFacilPDV-Setup-1.0.17.exe -Algorithm SHA256`. O hash do build local conferido em 14/11/2026 é `E892829B0D836644D7CC3B68A134F141EFECC3ADB43ED1614117352A2B8FBC68` | Print do hash igual |
| 2 | Instalar | Botão direito → **Executar como administrador**. SmartScreen: "Mais informações → Executar assim mesmo" (o programa não é assinado, decisão do projeto). Detalhes: `INSTALACAO_WINDOWS.md` | Print do atalho na Área de Trabalho |
| 3 | Primeiro acesso | Abra o atalho. O navegador abre em `http://127.0.0.1:3020/`. Com painel: entre com o usuário e a senha criados no painel (o primeiro login precisa de internet). Modo local: crie o primeiro usuário com senha forte | Print da tela do PDV logado |
| 4 | Senha | Troque a senha provisória e anote-a só com o dono da loja (nunca em papel colado no caixa) | Confirmação verbal do dono |
| 5 | Cadastro mínimo de produtos | **Produtos**: nome, código de barras, preço de custo, preço de venda, estoque, unidade (UN, KG…), NCM, CFOP e CST/CSOSN conforme o contador. Ou **📄 Importar XML** das notas de compra. Mercadoria que vende a caixa e o avulso: ligue **Também vende por unidade**, informe a embalagem, quantas unidades vêm dentro e os dois preços (exemplo: carteira R$ 20 e palheiro R$ 2). Sem essa opção, o produto continua com um preço só | Print da lista com os 20 itens mais vendidos, incluindo um item com os dois preços |
| 6 | Leitor de código de barras | Na tela PDV, bipe 3 produtos diferentes | Os 3 entram no carrinho |
| 7 | Formas de pagamento | **PIX**: chave, nome e cidade em PIX. **Maquininha** (Mercado Pago Point): token e aparelho em Maquininha, e o **CNPJ da credenciadora** em "Vínculo fiscal" (`MAQUININHA_MERCADOPAGO.md`, `VINCULO_PAGAMENTO_MT.md`) | Uma venda de R$ 0,01–1,00 em cada forma, conferida no aplicativo do banco |
| 8 | Fiscal em homologação | **Fiscal**: dados da empresa (CNPJ, IE, CNAE, endereço, regime), provedor **SEFAZ-MT direto**, ambiente **homologação**, certificado A1 **da própria loja** e senha, CSC e ID do CSC de homologação. Rode `scripts\fiscal_precheck.py` (mostra só presença e validade, nunca o valor). Roteiro completo: `TESTE_FISCAL_WINDOWS.md`. Se vier **cStat 230** ("IE do emitente não cadastrada"), ver `IE_NFCE_AMBIENTES.md` | Saída do precheck sem pendências; 1ª NFC-e autorizada em homologação |
| 9 | Produção fiscal | **Só com o contador de acordo** e o credenciamento confirmado. Trocar o ambiente para produção é decisão do dono | Data e nome de quem autorizou |
| 10 | Impressora térmica | Instale o driver da impressora; no PDV escolha a largura (58 ou 80 mm). No diálogo de impressão do navegador: sem cabeçalho/rodapé, margens nenhuma | Cupom em papel com o QR Code lido pela câmera do celular |
| 11 | Contingência | Desligue a internet, faça uma venda com NFC-e: saem **duas vias** com "EMITIDA EM CONTINGÊNCIA". Religue a internet com o programa aberto: a nota vira "autorizada" sozinha em até alguns minutos | Foto das duas vias + print da nota autorizada em **Vendas** |
| 12 | Backup ligado | O backup automático roda ao abrir o programa e a cada 24 h, guardando os 14 mais recentes em `%LOCALAPPDATA%\VendaFacilPDV\dados\backups`. Em **Backup**, clique em "Baixar backup agora" e salve num pendrive ou nuvem | Print da pasta de backups com o arquivo do dia |
| 13 | Restauração testada | Cadastre um produto "TESTE", restaure o backup baixado antes dele e confira que "TESTE" sumiu. Depois apague o teste | Print antes/depois |
| 14 | Licença | Com painel: confira a validade da loja no painel e na tela do PDV | Print da validade |
| 15 | Diagnóstico | Abra **Diagnóstico** e clique em "Copiar diagnóstico"; cole num bloco de notas. Assim a loja sabe mandar o diagnóstico ao suporte | Texto colado (não contém senhas) |
| 16 | Treinamento | Siga `TREINAMENTO_OPERADOR.md` com quem vai operar o caixa, inclusive o exercício da carteira e do avulso | Operador fez sozinho: abrir caixa, vender uma embalagem e uma unidade, sangria, fechar |
| 17 | Folha de suporte | Imprima `SUPORTE_LOJA.md`, preencha o contato de suporte e deixe ao lado do caixa | Foto da folha no balcão |

## Antes de ir embora

- [ ] Venda de teste cancelada (em **Vendas**, abrir a venda → **Cancelar venda (F9)**) e estoque devolvido.
- [ ] Caixa de teste fechado; caixa do dia aberto com o fundo de troco real.
- [ ] Dono sabe onde ficam os backups e que deve copiar um para fora do PC toda semana.
- [ ] Nenhum dado de teste fiscal (CSC, certificado) de outra empresa ficou no PC.
