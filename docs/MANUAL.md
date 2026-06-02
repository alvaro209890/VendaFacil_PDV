# 📘 Manual completo — VendaFácil PDV

Guia de uso do sistema, dividido em duas partes:
- **Parte 1 — Lojista**: quem usa o PDV (.exe) no balcão.
- **Parte 2 — Administrador**: você, dono do sistema, que gerencia as lojas no Painel.

Sumário rápido:
- [1. Instalar e abrir](#1-instalar-e-abrir)
- [2. Primeiro acesso e login](#2-primeiro-acesso-e-login)
- [3. Vender (PDV)](#3-vender-pdv)
- [4. Formas de pagamento](#4-formas-de-pagamento)
- [5. Produtos e estoque](#5-produtos-e-estoque)
- [6. Importar XML (entrada de mercadoria)](#6-importar-xml-entrada-de-mercadoria)
- [7. Categorias e clientes](#7-categorias-e-clientes)
- [8. Fiado (contas a receber)](#8-fiado-contas-a-receber)
- [9. Caixa (abrir/fechar)](#9-caixa-abrirfechar)
- [10. Recibo na impressora térmica](#10-recibo-na-impressora-térmica)
- [11. Relatórios](#11-relatórios)
- [12. Nota fiscal (NFC-e e NF-e)](#12-nota-fiscal-nfce-e-nf-e)
- [13. Backup](#13-backup)
- [Parte 2 — Administrador (Painel)](#parte-2--administrador-painel)
- [FAQ / Problemas comuns](#faq--problemas-comuns)

---

# Parte 1 — Lojista (PDV)

## 1. Instalar e abrir
1. Receba o instalador **`VendaFacilPDV-Setup.exe`** e dê dois cliques.
2. Avance a instalação (cria atalho no Menu Iniciar e na Área de Trabalho).
3. Abra pelo atalho **VendaFácil PDV**. O sistema sobe e abre no navegador.

> Na 1ª vez o Windows pode mostrar um aviso azul (SmartScreen). Clique em
> **"Mais informações" → "Executar assim mesmo"** — é normal.

## 2. Primeiro acesso e login
- Se a loja usa **controle central** (licença), informe o **login e senha**
  fornecidos pelo seu fornecedor do sistema.
- Crie/efetue login do **operador** (e-mail e senha). Pronto, você está no PDV.

O sistema **funciona sem internet** (offline-first). Só pagamento em cartão e a
nota fiscal precisam de conexão.

## 3. Vender (PDV)
1. Na tela **PDV / Vender**, busque o produto por **nome** ou **código de
   barras** (pode usar leitor — bipou, entrou no carrinho).
2. Ajuste a **quantidade** com + / − no carrinho.
3. Informe **desconto** (opcional).
4. Escolha a **forma de pagamento**.
5. Clique em **FINALIZAR VENDA** (atalho **F2**). O estoque baixa automaticamente.

Atalhos: **F2** finaliza, **F4** foca a busca.

## 4. Formas de pagamento
- **Dinheiro / Débito / Crédito**: registra direto.
- **PIX** — dois jeitos:
  - **QR na tela do PDV**: precisa cadastrar a **chave PIX** em **PIX** (menu).
  - **QR na maquininha**: se a maquininha (Mercado Pago Point) estiver ligada e
    online, o PIX é cobrado **na telinha do aparelho** (não precisa configurar
    chave; o Mercado Pago concilia). Depende da Point suportar PIX.
- **Cartão pela maquininha (Mercado Pago Point)**: se habilitada e com internet,
  o sistema **dispara a cobrança na maquininha** e aguarda a aprovação. Sem
  internet, registre como **cartão manual** (passa no aparelho e confirma).
- **Fiado**: escolha o cliente; gera uma conta a receber.

> O **comprovante** (recibo térmico) sai para **qualquer** forma de pagamento.
> Se a venda emitir **NFC-e**, o recibo já inclui o **bloco fiscal** (nº, chave,
> protocolo e QR de consulta) — ou seja, a nota também sai na térmica.

## 5. Produtos e estoque
Tela **Produtos**:
- **+ Novo**: cadastre nome, preços (custo/venda), estoque, código de barras,
  unidade e (opcional) dados fiscais.
- **Editar / Desativar** cada produto.
- **+ Estoque**: dá entrada rápida (soma quantidade) num produto.
- **Ajustar**: corrige o estoque fora de venda/entrada. Três tipos:
  - **Perda** — baixa a quantidade (ex.: produto vencido).
  - **Quebra** — baixa a quantidade (ex.: avaria).
  - **Inventário** — você informa a **contagem real** da prateleira e o sistema
    acerta o estoque, lançando a diferença (sobra ou falta).
- **Histórico**: abre a lista de **todas as movimentações** do produto — entradas
  (manual/XML), saídas (venda) e ajustes (perda/quebra/inventário), com data,
  sinal +/− e observação.
- Estoque baixo aparece no **Dashboard** (alerta).

Detalhes: [`ESTOQUE_E_XML.md`](ESTOQUE_E_XML.md).

## 6. Importar XML (entrada de mercadoria)
Quando o fornecedor entrega a mercadoria com a **NF-e (.xml)**:
1. Em **Produtos**, clique **📄 Importar XML** e escolha o arquivo.
2. Confira a **prévia**: itens que já existem aparecem como **repor** (somam ao
   estoque) e os novos como **criar** (defina o preço de venda).
3. Ajuste quantidades/custos, desmarque o que não quiser, e **Confirmar importação**.

Detalhes: [`ESTOQUE_E_XML.md`](ESTOQUE_E_XML.md).

## 7. Categorias e clientes
- **Categorias**: organize os produtos (com cores).
- **Clientes**: cadastro para venda fiada e histórico.

## 8. Fiado (contas a receber)
- Venda no **fiado** gera uma conta a receber para o cliente.
- Em **Contas a Receber**, registre **pagamentos** (total ou parcial) e acompanhe
  o que está pendente/vencido.

## 9. Caixa (abrir/fechar)
Tela **Caixa**:
1. **Abrir caixa** com o fundo de troco inicial.
2. Durante o dia, use **Suprimento** (reforço) e **Sangria** (retirada).
3. Veja o **dinheiro esperado na gaveta** e as vendas por forma de pagamento.
4. **Fechar caixa**: conte o dinheiro e informe — o sistema mostra a **diferença**
   (sobra/falta).

Detalhes: [`CAIXA.md`](CAIXA.md).

## 10. Recibo na impressora térmica
- No PDV, escolha a largura do rolo (**80mm** ou **58mm**).
- Marque **"Imprimir recibo ao finalizar"** para imprimir automático, ou use o
  botão **🖨️ Imprimir recibo** após a venda.
- A impressora térmica precisa estar **instalada no Windows** (driver do fabricante).

Detalhes: [`RECIBO.md`](RECIBO.md).

## 11. Relatórios
Tela **Relatórios**: escolha o período (atalhos: hoje / 7 / 30 dias / mês) e veja
**faturamento, nº de vendas, ticket médio, lucro estimado**, vendas **por forma de
pagamento**, **produtos mais vendidos** e **vendas por dia**.

Na aba **Fiscal (Simples)** o sistema separa a receita do período para ajudar o
contador no PGDAS-D:
- **ICMS já recolhido por ST**: produtos cadastrados com **CSOSN 500**.
- **PIS/COFINS monofásico, ST ou alíquota zero**: produtos cadastrados com
  **CST 04, 05 ou 06** em PIS e/ou COFINS.
- **Tributada integral**: produtos sem essas marcações.

Essa segregação usa o cadastro fiscal atual de cada produto. Antes de fechar o
mês, confira com o contador se NCM, CFOP, CSOSN, CST PIS e CST COFINS estão
corretos para cada mercadoria.

## 12. Nota fiscal (NFC-e e NF-e)
Opcional. O sistema emite **NFC-e (modelo 65)** — o cupom fiscal do consumidor — e
**NF-e (modelo 55)** — a nota para outra empresa/cliente identificado. O fluxo
padrão é **direto com a SEFAZ-MT** (sem intermediário); o gateway Focus NFe segue
disponível apenas como legado.

### O que o lojista precisa (uma vez)
1. **Certificado A1** da loja (arquivo `.pfx`/`.p12` + senha).
2. **CSC e ID do CSC** gerados no portal da **SEFAZ-MT**.
3. **Credenciamento** de NFC-e/NF-e na SEFAZ-MT (gratuito, online) e **Inscrição
   Estadual** ativa.

### Configurar (tela Fiscal)
1. Ligue **"Emissão fiscal habilitada"**.
2. Preencha **Emitente** (CNPJ, IE, regime) e **Endereço**.
3. Em **SEFAZ-MT & Ambiente**: deixe o provedor em **SEFAZ-MT direto**, carregue o
   **certificado A1** + senha e informe **CSC** e **ID do CSC**.
4. Comece em **Homologação** (teste, sem valor fiscal). Só mude para **Produção**
   depois de autorizar uma nota de teste com sucesso.
5. *(Avançado, opcional)* **Responsável Técnico** — **Mato Grosso não exige**;
   deixe desligado. Veja [`RESPONSAVEL_TECNICO.md`](RESPONSAVEL_TECNICO.md).

### Emitir e acompanhar
- No **PDV**, marque **"Emitir nota"** ao finalizar (pode informar o CPF do
  consumidor). A NFC-e autorizada já imprime no recibo térmico, com QR de consulta.
- Em **Vendas**, abra uma venda para **emitir**, **consultar status** ou
  **cancelar** a nota (com justificativa). A NF-e (modelo 55) exige um cliente com
  endereço/documento completos.

> Notas que ficarem em **"processando"** são reconsultadas automaticamente em
> segundo plano até a SEFAZ dar o resultado.

### Pagamento em cartão/PIX e a nota (MT)
Em Mato Grosso, a NFC-e de **cartão/PIX** precisa levar os dados da transação
(vínculo do pagamento — Portaria 262/2023). Quando a cobrança é feita pela
**maquininha Mercado Pago**, o sistema preenche isso sozinho; você só informa
**uma vez** o **CNPJ da credenciadora** em **Maquininha → Vínculo fiscal**.
Detalhes e quem é obrigado: [`VINCULO_PAGAMENTO_MT.md`](VINCULO_PAGAMENTO_MT.md).

### Entregar os XMLs ao contador
O sistema **guarda o XML** de cada nota. Para o contador: em **Relatórios →
Fiscal (Simples)**, escolha o período e clique **"Exportar XMLs do período
(ZIP)"**; para uma nota só, **Vendas → abrir → "Baixar XML"**. O contador é quem
**apura e declara** (a loja só emite). Veja [`CONTADOR.md`](CONTADOR.md).

## 13. Backup
Tela **Backup**:
- **Baixar backup agora**: salva um arquivo `.db` — guarde fora do PC (pen
  drive/nuvem).
- **Restaurar**: volta a um backup (substitui os dados atuais; salva o estado
  atual antes).
- Backups **automáticos** diários ficam na máquina.

Detalhes: [`BACKUP.md`](BACKUP.md).

---

# Parte 2 — Administrador (Painel)

O **Painel** (web) é onde você gerencia as lojas, licenças e o financeiro do seu
negócio. Acesse pela URL do seu painel (Vercel/Render).

## Primeiro acesso
No 1º acesso, crie o **admin master** (seu e-mail e senha). Depois é só logar.

## Gerenciar lojas
- **+ Nova loja**: crie a conta (nome, login, senha, plano, validade da licença).
- **Editar**: muda dados, validade e senha da loja.
- **Bloquear / Ativar**: liga/desliga o acesso da loja na hora.
- **Excluir**: remove a loja e as vendas sincronizadas dela (irreversível).

## Licença e cobrança (manual)
Você cobra a mensalidade por fora (PIX/boleto) e controla o acesso pela validade
e pelo bloqueio. Fluxo sugerido em [`COBRANCA_MANUAL.md`](COBRANCA_MANUAL.md).

## Financeiro
Botão **💰 Financeiro**: defina o **preço por loja**, cadastre **custos** (fixos e
por loja) e veja **receita, custo, lucro e ponto de equilíbrio**. Detalhes em
[`CUSTOS.md`](CUSTOS.md).

## Segurança
- **Trocar senha**: botão no painel (peça a senha atual).
- O login tem **proteção contra força-bruta** (bloqueia após várias tentativas).

## Conectar os PDVs ao painel
Cada `.exe` aponta para o painel pela variável `VENDAFACIL_PAINEL_URL`
(definida ao gerar o executável). Sem ela, o PDV roda em **modo local**.

---

# FAQ / Problemas comuns

**O Windows diz "editor desconhecido" ao abrir.**
Normal (o app não é assinado). Clique em "Mais informações → Executar assim mesmo".

**Funciona sem internet?**
Sim. Vendas, estoque, caixa, recibo e backup são locais. Só **cartão pela
maquininha** e **NFC-e** precisam de internet.

**A maquininha não cobra.**
Verifique internet, se a Point está ligada e em **modo PDV/Integração**, e se o
Access Token/Device ID estão certos na tela **Maquininha**. Sem internet, use
**cartão manual**.

**Perdi/zerei o computador.**
Restaure pelo menu **Backup** com o `.db` que você baixou. Por isso, baixe
backups regularmente e guarde fora do PC.

**Esqueci a senha do admin do Painel.**
Hoje não há "esqueci a senha" por e-mail. Estando logado, use **Trocar senha**.
Se ficou totalmente sem acesso, é preciso redefinir direto no banco (Supabase) —
fale com o suporte técnico.

**A nota fiscal não autoriza / fica "rejeitada".**
Confira na tela **Fiscal**: certificado A1 e senha corretos, CSC/ID do CSC
preenchidos, CNPJ/IE regulares e credenciados na SEFAZ-MT. A mensagem de rejeição
da SEFAZ aparece na venda (em **Vendas**) e indica o motivo. Teste sempre em
**Homologação** antes de **Produção**.

**Preciso de certificado A1 para usar o sistema?**
Só para **emitir nota fiscal**. Vender, controlar estoque, caixa e recibo
funcionam sem nada disso. O A1 é da **loja** (cada CNPJ tem o seu).

**O painel no Vercel não conecta na API.**
Confira se o backend (Render) está no ar (`/health`) e se a URL da API está certa
(arquivo `config.js` ou botão "Configurar URL da API").

**As vendas no cartão não somem do dinheiro do caixa.**
Correto: o caixa controla só o **dinheiro**. Cartão/PIX aparecem no resumo, mas
não entram no esperado em espécie.
