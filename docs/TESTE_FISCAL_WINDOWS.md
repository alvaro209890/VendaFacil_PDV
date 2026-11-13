# Teste fiscal de ponta a ponta (Windows) — NFC-e + maquininha

Guia para o agente/operador que vai validar a emissão fiscal na máquina Windows,
com **certificado A1 real**, **CNPJ/IE da loja** e a **maquininha Mercado Pago**.
Ordem: gerar o `.exe` → configurar → testar em **homologação** → só então
**produção somente com ordem explícita do Álvaro**.

> Regra de ouro: **nunca** comece em produção. Homologação não tem valor fiscal —
> é onde se erra à vontade.

---

## 0. O que ter em mãos (do contador / da loja)

Antes de qualquer transmissão real, execute na raiz do repositório:

```powershell
backend\.venv\Scripts\python.exe -X utf8 -I scripts\fiscal_precheck.py
```

Saída 0 indica requisitos locais presentes. Saída 2 identifica B1–B5. O script
é somente leitura e mostra presença/validade, sem imprimir A1, senha, CSC ou token.
Não procure outro certificado no PC. O CNAE principal pode ser cadastrado na tela
Fiscal e é normalizado para sete dígitos.

Os testes H01–H09 ficam fora da suíte padrão. Depois de preparar os cenários A–G
abaixo pelo PDV com o cofre da mercearia em homologação, reconfira-os com:

```powershell
cd backend
.venv\Scripts\python.exe -X utf8 -I -m pytest -m homologacao tests/test_homologacao_real.py --tb=short -rs -s
```

Esses testes leem o cofre padrão e consultam a SEFAZ/portal. Não criam vendas nem
cobranças, não alteram estoque e não consomem numeração automaticamente. Falta de
pré-requisito resulta em SKIPPED com B1–B5; isso não conta como homologação aprovada.
Quando houver aprovação real, guardar chave, protocolo e cStat; revisar a saída
antes de versionar e nunca registrar credenciais.

Em Fiscal, **Consultar serviço SEFAZ-MT** verifica o código 107 (em operação).
Os testes de autorização verificam se a loja pode emitir.

Para H09, **Inutilizar numeração sem uso**: selecionar modelo/ano/série e uma
quebra de sequência existente e justificar em 15–255 caracteres. Não usar número
futuro nem nota ativa/contingente. Protocolo e resultado ficam no histórico.
Resultado `processando` exige conferir a situação na SEFAZ antes de qualquer
reutilização; repetir o mesmo pedido pendente não gera novo envio.

- [ ] **Certificado Digital A1** da loja: arquivo **`.pfx`/`.p12`** + **senha**.
- [ ] **CNPJ**, **Inscrição Estadual (IE)** ativa e **regime** (Simples Nacional = CRT 1).
- [ ] **Endereço completo** + **código IBGE do município** (7 dígitos).
- [ ] **CSC** e **ID do CSC** — de **homologação** e de **produção** (gerados no
      portal NFC-e da SEFAZ-MT: <https://www.sefaz.mt.gov.br/portal/nfce/>).
- [ ] **Tabela fiscal por produto** (NCM, CFOP, CSOSN, CST PIS/COFINS) — do contador.
- [ ] **CNPJ da credenciadora** do Mercado Pago (p/ o vínculo de cartão/PIX).
- [ ] Maquininha **Mercado Pago Point** ativada + **Access Token de produção**.

---

## 1. Gerar o `.exe` (a partir do `master`)

```bat
git checkout master && git pull
build_exe.bat
installer\build_installer.bat
```
Saídas: `dist_exe\VendaFacilPDV.exe` e `dist_installer\VendaFacilPDV-Setup-*.exe`.
(Detalhes: [`BUILD_WINDOWS.md`](BUILD_WINDOWS.md).) Abra o `.exe` → o navegador
sobe em `http://127.0.0.1:3020/`.

> Alternativa: baixar o artifact já compilado em **GitHub → Actions** (o push no
> `master` dispara o build automático).

---

## 2. Configurar a parte fiscal (tela **Fiscal**)

1. Ligue **"Emissão fiscal habilitada"**.
2. **Emitente**: CNPJ, IE, **regime = Simples Nacional**, razão social, nome fantasia.
3. **Endereço** completo + **código do município (IBGE)**.
4. **SEFAZ-MT & Ambiente**:
   - Provedor: **SEFAZ-MT direto**.
   - **Ambiente: Homologação**.
   - Carregue o **A1 (.pfx)** + senha → confira que aparece a **validade** do certificado.
   - **CSC** e **ID do CSC** **de homologação**.
5. **Responsável Técnico**: deixe **desligado** (MT não exige).

## 3. Configurar a maquininha (tela **Maquininha**)

1. **Access Token** (produção) → **Buscar maquininhas** → selecione a **Point**.
2. **Vínculo fiscal**: informe o **CNPJ da credenciadora** (Mercado Pago).
3. (Opcional) ligue **"Cobrar PIX pela maquininha"** se for testar PIX integrado.

## 4. Cadastrar 1–2 produtos com dados fiscais

Em **Produtos → Novo**, preencha além do preço: **NCM**, **CFOP** (ex.: 5102),
**CSOSN** (ex.: 102), **unidade**, **CST PIS/COFINS** (conforme o contador).
Sem esses campos a emissão é bloqueada com a mensagem de "dados fiscais incompletos".

---

## 5. Roteiro de testes (em **Homologação**)

> Em homologação, quando há **destinatário** (CPF/CNPJ informado), o XML sai com o
> nome "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL". É o esperado
> (a SEFAZ exige — Rejeição 706).

### Teste A — NFC-e em **dinheiro**
1. PDV → adicione o produto → forma **Dinheiro** → marque **Emitir NFC-e (Cupom Fiscal)** → **Finalizar**.
2. ✅ Esperado: nota **autorizada** (cStat 100), recibo com **chave + QR**.
3. Em **Vendas**, abra a venda → confira **status autorizada** e o **QR de consulta**.

### Teste B — NFC-e em **cartão** pela maquininha (vínculo de pagamento)
1. Forma **Crédito** (ou Débito) → **Emitir NFC-e** → **Finalizar**.
2. Passe o cartão na **Point** (em homologação, use cartão de teste do MP se aplicável).
3. ✅ Esperado: cobrança aprovada → venda criada → **NFC-e autorizada**.
4. **Conferência do vínculo** — abra o XML autorizado (em Vendas) e verifique o
   grupo de pagamento:
   ```xml
   <detPag>
     <tPag>03</tPag>
     <card>
       <tpIntegra>1</tpIntegra>
       <CNPJ>...credenciadora...</CNPJ>
       <tBand>..</tBand>
       <cAut>..autorização..</cAut>
     </card>
   </detPag>
   ```
5. ⚠️ Se vier **`<tpIntegra>2</tpIntegra>`**: faltou **CNPJ da credenciadora** ou o
   **cAut** não veio da Point. Reveja o passo 3.2 e os logs.
6. ⚠️ Se a SEFAZ **rejeitar 392**: dados do cartão incompletos. **Rejeição 737**:
   ela espera transação integrada (tpIntegra=1) — confirme o vínculo.

### Teste C — NFC-e em **PIX** (se "PIX integrado" ligado)
1. Forma **PIX** → **Emitir NFC-e** → **Finalizar** → pague o PIX na **telinha da Point**.
2. ✅ Esperado: `tPag=17`, `<card><tpIntegra>1</tpIntegra>` com **cAut = endToEndId**.
3. Se a Point **não** oferecer PIX: desligue "PIX integrado" → o PDV volta ao **QR
   estático** (sairá com `tPag=20` e sem grupo `<card>`).

### Teste D — Cancelamento
1. Em **Vendas**, abra a venda com nota autorizada → **Cancelar NFC-e** com justificativa (≥15 caracteres), em até 30 minutos.
2. ✅ Esperado: evento de cancelamento **registrado** (cStat 135).

### Teste E — Contingência offline (caixa sem internet)
1. **Desligue a internet** da máquina (Wi-Fi/cabo).
2. PDV → produto → **Dinheiro** → **Emitir NFC-e** → **Finalizar**.
3. ✅ Esperado: a venda conclui e o **DANFE imprime em duas vias com "EMITIDA EM
   CONTINGÊNCIA" e "Pendente de autorização"** (chave + QR). Em **Vendas** a nota fica **`contingência`**.
4. **Religue a internet** e aguarde ~1 min (o loop transmite sozinho).
5. ✅ Esperado: a nota vira **`autorizada`** (cStat 100) com protocolo, sem perder
   o número fiscal.

### Teste F — NFC-e com **desconto**
1. PDV → adicione 2 itens → informe um **desconto** → **Emitir NFC-e** → **Finalizar**.
2. ✅ Esperado: nota **autorizada**. Abra o XML e confira os totais fechando:
   `vProd − vDesc = vNF` (sem **Rejeição 528/610**), com `vDesc` rateado nos itens.

### Teste G — Processando / reconsulta
1. Se uma nota ficar **"processando"**, aguarde — o sistema **reconsulta sozinho**
   em segundo plano até a SEFAZ responder. Confira que ela conclui.

## 5.1 Rejeições específicas da SEFAZ-MT (12/11/2026)

- **402 — XML utiliza codificação diferente de UTF-8**: o autorizador de NFC-e
  re-serializa o XML em ISO-8859-1; qualquer acento derruba a nota. O PDV
  translitera os textos para ASCII 7-bit antes da assinatura (a tela pode manter
  o acento no cadastro; o XML sai sem). O cupom impresso segue o XML, então o
  nome do emitente e o município também saem sem acento; `scripts/verificar_cupons_pdf.py`
  confere o texto nas duas formas.
- **587 — namespace diverso do padrão**: a assinatura não pode sair com prefixo
  `ds:`; o PDV monta o XMLDSig com o namespace `xmldsig` default.
- **297 — assinatura difere do calculado**: o C14N de um subelemento que herda o
  `xmlns` do pai precisa ser feito sobre a cópia reparseada; sem isso o digest da
  Reference não fecha na SEFAZ.
- **230 — IE do emitente não cadastrada**: bloqueio cadastral do ambiente de
  homologação. A IE pode estar ativa no CCE e mesmo assim faltar no autorizador;
  o contador precisa pedir a atualização do cadastro na SEFAZ-MT.

---

## 6. Virar para **Produção**

Só depois de A–D passarem em homologação:
1. Tela **Fiscal → Ambiente: Produção**.
2. Troque **CSC/ID do CSC** para os de **produção**.
3. Emita **uma** NFC-e real de **valor baixo** (ex.: R$ 1,00) em dinheiro e confirme
   autorização e o **QR de consulta** no site da SEFAZ-MT.
4. A partir daí, operação normal.

---

## 7. Checklist de aceite

- [ ] A (dinheiro) autorizada em homologação
- [ ] B (cartão) autorizada **com `<tpIntegra>1</tpIntegra>` e `cAut` preenchido**
- [ ] C (PIX) — conforme suporte da Point
- [ ] D (cancelamento) registrado
- [ ] E (contingência offline) imprime o DANFE e autoriza ao voltar a internet
- [ ] F (desconto) autorizada com `vProd − vDesc = vNF`
- [ ] G (reconsulta) conclui sozinha
- [ ] QR Code do DANFE abre a consulta no portal NFC-e MT
- [ ] Produção: 1 nota real autorizada e consultável

## 8. Se algo falhar — onde olhar

- **Logs**: `%LOCALAPPDATA%\VendaFacilPDV\dados\logs\vendafacil.log`.
- **Certificado inválido / senha**: re-carregue o A1 e confira a senha.
- **"Configuração fiscal incompleta"**: faltou campo do emitente (CNPJ/IE/município...).
- **Rejeições da SEFAZ**: o motivo (xMotivo) aparece na venda; anote o cStat.
- Vínculo de pagamento: ver [`VINCULO_PAGAMENTO_MT.md`](VINCULO_PAGAMENTO_MT.md).
- Maquininha: ver [`MAQUININHA_MERCADOPAGO.md`](MAQUININHA_MERCADOPAGO.md) e
  [`DIAGNOSTICO_MAQUININHA_POINT.md`](DIAGNOSTICO_MAQUININHA_POINT.md).
