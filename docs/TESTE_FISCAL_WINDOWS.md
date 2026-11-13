# Teste fiscal de ponta a ponta (Windows) �?" NFC-e + maquininha

Guia para o agente/operador que vai validar a emissǜo fiscal na mǭquina Windows,
com **certificado A1 real**, **CNPJ/IE da loja** e a **maquininha Mercado Pago**.
Ordem: gerar o `.exe` ��' configurar ��' testar em **homologa��ǜo** ��' s�� entǜo
**produ��ǜo somente com ordem expl��cita do �?lvaro**.

> Regra de ouro: **nunca** comece em produ��ǜo. Homologa��ǜo nǜo tem valor fiscal �?"
> Ǹ onde se erra �� vontade.

---

## 0. O que ter em mǜos (do contador / da loja)

Antes de qualquer transmissǜo real, execute na raiz do reposit��rio:

```powershell
backend\.venv\Scripts\python.exe -X utf8 -I scripts\fiscal_precheck.py
```

Sa��da 0 indica requisitos locais presentes. Sa��da 2 identifica B1�?"B5. O script
Ǹ somente leitura e mostra presen��a/validade, sem imprimir A1, senha, CSC ou token.
Nǜo procure outro certificado no PC. O CNAE principal pode ser cadastrado na tela
Fiscal e Ǹ normalizado para sete d��gitos.

Os testes H01�?"H09 ficam fora da su��te padrǜo. Depois de preparar os cenǭrios A�?"G
abaixo pelo PDV com o cofre da mercearia em homologa��ǜo, reconfira-os com:

```powershell
cd backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -m homologacao tests/test_homologacao_real.py --tb=short -rs -s
```

Esses testes leem o cofre padrǜo e consultam a SEFAZ/portal. Nǜo criam vendas nem
cobran��as, nǜo alteram estoque e nǜo consomem numera��ǜo automaticamente. Falta de
prǸ-requisito resulta em SKIPPED com B1�?"B5; isso nǜo conta como homologa��ǜo aprovada.
Quando houver aprova��ǜo real, guardar chave, protocolo e cStat; revisar a sa��da
antes de versionar e nunca registrar credenciais.

Em Fiscal, **Consultar servi��o SEFAZ-MT** verifica o c��digo 107 (em opera��ǜo).
Os testes de autoriza��ǜo verificam se a loja pode emitir.

Para H09, **Inutilizar numera��ǜo sem uso**: selecionar modelo/ano/sǸrie e uma
quebra de sequǦncia existente e justificar em 15�?"255 caracteres. Nǜo usar nǧmero
futuro nem nota ativa/contingente. Protocolo e resultado ficam no hist��rico.
Resultado `processando` exige conferir a situa��ǜo na SEFAZ antes de qualquer
reutiliza��ǜo; repetir o mesmo pedido pendente nǜo gera novo envio.

- [ ] **Certificado Digital A1** da loja: arquivo **`.pfx`/`.p12`** + **senha**.
- [ ] **CNPJ**, **Inscri��ǜo Estadual (IE)** ativa e **regime** (Simples Nacional = CRT 1).
- [ ] **Endere��o completo** + **c��digo IBGE do munic��pio** (7 d��gitos).
- [ ] **CSC** e **ID do CSC** �?" de **homologa��ǜo** e de **produ��ǜo** (gerados no
      portal NFC-e da SEFAZ-MT: <https://www.sefaz.mt.gov.br/portal/nfce/>).
- [ ] **Tabela fiscal por produto** (NCM, CFOP, CSOSN, CST PIS/COFINS) �?" do contador.
- [ ] **CNPJ da credenciadora** do Mercado Pago (p/ o v��nculo de cartǜo/PIX).
- [ ] Maquininha **Mercado Pago Point** ativada + **Access Token de produ��ǜo**.

---

## 1. Gerar o `.exe` (a partir do `master`)

```bat
git checkout master && git pull
build_exe.bat
installer\build_installer.bat
```
Sa��das: `dist_exe\VendaFacilPDV.exe` e `dist_installer\VendaFacilPDV-Setup-*.exe`.
(Detalhes: [`BUILD_WINDOWS.md`](BUILD_WINDOWS.md).) Abra o `.exe` ��' o navegador
sobe em `http://127.0.0.1:3020/`.

> Alternativa: baixar o artifact jǭ compilado em **GitHub ��' Actions** (o push no
> `master` dispara o build automǭtico).

---

## 2. Configurar a parte fiscal (tela **Fiscal**)

1. Ligue **"Emissǜo fiscal habilitada"**.
2. **Emitente**: CNPJ, IE, **regime = Simples Nacional**, razǜo social, nome fantasia.
3. **Endere��o** completo + **c��digo do munic��pio (IBGE)**.
4. **SEFAZ-MT & Ambiente**:
   - Provedor: **SEFAZ-MT direto**.
   - **Ambiente: Homologa��ǜo**.
   - Carregue o **A1 (.pfx)** + senha ��' confira que aparece a **validade** do certificado.
   - **CSC** e **ID do CSC** **de homologa��ǜo**.
5. **Responsǭvel TǸcnico**: deixe **desligado** (MT nǜo exige).

## 3. Configurar a maquininha (tela **Maquininha**)

1. **Access Token** (produ��ǜo) ��' **Buscar maquininhas** ��' selecione a **Point**.
2. **V��nculo fiscal**: informe o **CNPJ da credenciadora** (Mercado Pago).
3. (Opcional) ligue **"Cobrar PIX pela maquininha"** se for testar PIX integrado.

## 4. Cadastrar 1�?"2 produtos com dados fiscais

Em **Produtos ��' Novo**, preencha alǸm do pre��o: **NCM**, **CFOP** (ex.: 5102),
**CSOSN** (ex.: 102), **unidade**, **CST PIS/COFINS** (conforme o contador).
Sem esses campos a emissǜo Ǹ bloqueada com a mensagem de "dados fiscais incompletos".

---

## 5. Roteiro de testes (em **Homologa��ǜo**)

> Em homologa��ǜo, quando hǭ **destinatǭrio** (CPF/CNPJ informado), o XML sai com o
> nome "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL". �% o esperado
> (a SEFAZ exige �?" Rejei��ǜo 706).

### Teste A �?" NFC-e em **dinheiro**
1. PDV ��' adicione o produto ��' forma **Dinheiro** ��' marque **Emitir NFC-e (Cupom Fiscal)** ��' **Finalizar**.
2. �o. Esperado: nota **autorizada** (cStat 100), recibo com **chave + QR**.
3. Em **Vendas**, abra a venda ��' confira **status autorizada** e o **QR de consulta**.

### Teste B �?" NFC-e em **cartǜo** pela maquininha (v��nculo de pagamento)
1. Forma **CrǸdito** (ou DǸbito) ��' **Emitir NFC-e** ��' **Finalizar**.
2. Passe o cartǜo na **Point** (em homologa��ǜo, use cartǜo de teste do MP se aplicǭvel).
3. �o. Esperado: cobran��a aprovada ��' venda criada ��' **NFC-e autorizada**.
4. **ConferǦncia do v��nculo** �?" abra o XML autorizado (em Vendas) e verifique o
   grupo de pagamento:
   ```xml
   <detPag>
     <tPag>03</tPag>
     <card>
       <tpIntegra>1</tpIntegra>
       <CNPJ>...credenciadora...</CNPJ>
       <tBand>..</tBand>
       <cAut>..autoriza��ǜo..</cAut>
     </card>
   </detPag>
   ```
5. �s���? Se vier **`<tpIntegra>2</tpIntegra>`**: faltou **CNPJ da credenciadora** ou o
   **cAut** nǜo veio da Point. Reveja o passo 3.2 e os logs.
6. �s���? Se a SEFAZ **rejeitar 392**: dados do cartǜo incompletos. **Rejei��ǜo 737**:
   ela espera transa��ǜo integrada (tpIntegra=1) �?" confirme o v��nculo.

### Teste C �?" NFC-e em **PIX** (se "PIX integrado" ligado)
1. Forma **PIX** ��' **Emitir NFC-e** ��' **Finalizar** ��' pague o PIX na **telinha da Point**.
2. �o. Esperado: `tPag=17`, `<card><tpIntegra>1</tpIntegra>` com **cAut = endToEndId**.
3. Se a Point **nǜo** oferecer PIX: desligue "PIX integrado" ��' o PDV volta ao **QR
   estǭtico** (sairǭ com `tPag=20` e sem grupo `<card>`).

### Teste D �?" Cancelamento
1. Em **Vendas**, abra a venda com nota autorizada ��' **Cancelar NFC-e** com justificativa (�%�15 caracteres), em atǸ 30 minutos.
2. �o. Esperado: evento de cancelamento **registrado** (cStat 135).

### Teste E �?" ContingǦncia offline (caixa sem internet)
1. **Desligue a internet** da mǭquina (Wi-Fi/cabo).
2. PDV ��' produto ��' **Dinheiro** ��' **Emitir NFC-e** ��' **Finalizar**.
3. �o. Esperado: a venda conclui e o **DANFE imprime em duas vias com "EMITIDA EM
   CONTING�SNCIA" e "Pendente de autoriza��ǜo"** (chave + QR). Em **Vendas** a nota fica **`contingǦncia`**.
4. **Religue a internet** e aguarde ~1 min (o loop transmite sozinho).
5. �o. Esperado: a nota vira **`autorizada`** (cStat 100) com protocolo, sem perder
   o nǧmero fiscal.

### Teste F �?" NFC-e com **desconto**
1. PDV ��' adicione 2 itens ��' informe um **desconto** ��' **Emitir NFC-e** ��' **Finalizar**.
2. �o. Esperado: nota **autorizada**. Abra o XML e confira os totais fechando:
   `vProd �^' vDesc = vNF` (sem **Rejei��ǜo 528/610**), com `vDesc` rateado nos itens.

### Teste G �?" Processando / reconsulta
1. Se uma nota ficar **"processando"**, aguarde �?" o sistema **reconsulta sozinho**
   em segundo plano atǸ a SEFAZ responder. Confira que ela conclui.

## 5.1 Rejei����es espec��ficas da SEFAZ-MT (12/11/2026)

- **402 �?" XML utiliza codifica��ǜo diferente de UTF-8**: o autorizador de NFC-e
  re-serializa o XML em ISO-8859-1; qualquer acento derruba a nota. O PDV
  translitera os textos para ASCII 7-bit antes da assinatura (a tela pode manter
  o acento no cadastro; o XML sai sem). O cupom impresso segue o XML, entǜo o
  nome do emitente e o munic��pio tambǸm saem sem acento; `scripts/verificar_cupons_pdf.py`
  confere o texto nas duas formas.
- **587 �?" namespace diverso do padrǜo**: a assinatura nǜo pode sair com prefixo
  `ds:`; o PDV monta o XMLDSig com o namespace `xmldsig` default.
- **297 �?" assinatura difere do calculado**: o C14N de um subelemento que herda o
  `xmlns` do pai precisa ser feito sobre a c��pia reparseada; sem isso o digest da
  Reference nǜo fecha na SEFAZ.
- **230 �?" IE do emitente nǜo cadastrada**: bloqueio cadastral do ambiente de
  homologa��ǜo. A IE pode estar ativa no CCE e mesmo assim faltar no autorizador;
  o contador precisa pedir a atualiza��ǜo do cadastro na SEFAZ-MT.

---

## 5.2 Próximo passo: só teste real de operação (decisão do Álvaro, 12/11/2026)

Homologação não avança enquanto a SEFAZ-MT não cadastrar a IE no autorizador de teste
(cStat 230). O Álvaro decidiu **não fazer mais testes sem ser reais**: o sistema só volta a
ser exercitado numa venda de verdade, em produção, com cliente na frente.

Requisitos antes de ligar a chave em produção:

1. Contador confirmar o credenciamento de NFC-e nos **dois** ambientes (homologação e produção).
2. Trocar `ambiente` para produção e o CSC/ID do CSC pelos de produção.
3. Um teste único e controlado, de valor baixo (**R$ 0,01 a R$ 1,00**), em horário de movimento,
   com operador acompanhando. Se autorizar (cStat 100), a operação é liberada no dia.
4. Se rejeitar, **parar e anotar o cStat** — nada de tentativas em sequência em produção.

Vendas reais que falharem caem em **contingência (tpEmis=9)**: o cupom sai com duas vias e
"Pendente de autorização", e o PDV transmite quando a conexão/motivo voltar. Não é venda
perdida, mas é a primeira coisa a conferir todo dia (relatório de pendentes em Vendas).

---

## 6. Virar para **Produ��ǜo**

S�� depois de A�?"D passarem em homologa��ǜo:
1. Tela **Fiscal ��' Ambiente: Produ��ǜo**.
2. Troque **CSC/ID do CSC** para os de **produ��ǜo**.
3. Emita **uma** NFC-e real de **valor baixo** (ex.: R$ 1,00) em dinheiro e confirme
   autoriza��ǜo e o **QR de consulta** no site da SEFAZ-MT.
4. A partir da��, opera��ǜo normal.

---

## 7. Checklist de aceite

- [ ] A (dinheiro) autorizada em homologa��ǜo
- [ ] B (cartǜo) autorizada **com `<tpIntegra>1</tpIntegra>` e `cAut` preenchido**
- [ ] C (PIX) �?" conforme suporte da Point
- [ ] D (cancelamento) registrado
- [ ] E (contingǦncia offline) imprime o DANFE e autoriza ao voltar a internet
- [ ] F (desconto) autorizada com `vProd �^' vDesc = vNF`
- [ ] G (reconsulta) conclui sozinha
- [ ] QR Code do DANFE abre a consulta no portal NFC-e MT
- [ ] Produ��ǜo: 1 nota real autorizada e consultǭvel

## 8. Se algo falhar �?" onde olhar

- **Logs**: `%LOCALAPPDATA%\VendaFacilPDV\dados\logs\vendafacil.log`.
- **Certificado invǭlido / senha**: re-carregue o A1 e confira a senha.
- **"Configura��ǜo fiscal incompleta"**: faltou campo do emitente (CNPJ/IE/munic��pio...).
- **Rejei����es da SEFAZ**: o motivo (xMotivo) aparece na venda; anote o cStat.
- V��nculo de pagamento: ver [`VINCULO_PAGAMENTO_MT.md`](VINCULO_PAGAMENTO_MT.md).
- Maquininha: ver [`MAQUININHA_MERCADOPAGO.md`](MAQUININHA_MERCADOPAGO.md) e
  [`DIAGNOSTICO_MAQUININHA_POINT.md`](DIAGNOSTICO_MAQUININHA_POINT.md).

