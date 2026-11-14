# 📦 Estoque e importação de XML (NF-e)

Como o controle de estoque funciona no VendaFácil PDV e como dar entrada de
mercadoria importando o XML da nota do fornecedor.

## Como o estoque funciona

### Embalagem fechada e avulso (1.0.15)

No cadastro, ligue **Também vende por unidade** somente nos produtos que têm
as duas formas de venda. Use estoque em **UN**, informe o nome da embalagem
(por exemplo, CARTEIRA), quantas unidades vêm dentro e **os dois preços**.
Os preços são independentes: não é obrigatório dividir o preço da carteira.
Ao ligar a opção num produto antigo, informe ambos; o estoque não é recontado.

| Palheiro: carteira com 20, carteira R$ 20, unidade R$ 2 | Total | Baixa |
|---|---|---|
| 1 carteira | R$ 20 | 20 unidades |
| 1 avulso | R$ 2 | 1 unidade |
| 1 carteira + 3 avulsos | R$ 26 | 23 unidades |
| 20 avulsos | R$ 40 | 20 unidades |
| Carteira com apenas 15 em estoque | Recusada | Nenhuma |

Um cadastro, um estoque. Não é preciso “abrir caixa” antes de vender avulsos.
Com 65 palheiros, a lista mostra **3 carteiras e 5 avulsos (65 palheiros)**.
Mudar o fator para 30 mantém as mesmas 65 unidades; a tela avisa antes de salvar.
KG, G, LT e ML continuam com o funcionamento anterior, sem essa opção.

No **+ Estoque**, escolha avulsos ou embalagens. Duas carteiras com fator 20
somam 40 unidades. A API também aceita `modo_entrada: "embalagem"`;
nesse modo, o custo informado é o custo da embalagem e será dividido pelo fator.
No cadastro, o preço de custo sempre é por unidade menor.

No PDV aparecem dois botões grandes. O código principal lança a embalagem;
o segundo código opcional e a busca pelo nome lançam unidade. As linhas
ficam separadas, inclusive depois de recarregar. O caixa valida a soma do
estoque usado pelas duas linhas. Histórico e relatórios identificam a forma
vendida; o lucro desconta o custo das unidades baixadas. O estorno devolve
as unidades da venda original, mesmo se o fator tiver mudado depois.

#### Conferir a prévia da NF-e

- Produto configurado e nota na unidade de compra: **2 CARTEIRA viram 40 UN**;
  custo da unidade = custo da carteira ÷ 20. Os dois preços de venda são mantidos.
- Nota em **UN**: entra unidade a unidade, fator 1.
- Produto novo cujo nome sugere caixa/fardo/pacote/display/carteira: responda
  **“Isto é embalagem fechada que também vende por unidade?”** somente se for
  isso mesmo. Ao confirmar, informe nome da embalagem, fator e os dois preços.
  A quantidade e o custo convertidos aparecem antes da confirmação do lote.
- Sem essa confirmação, a nota em UN conserva a quantidade e a unidade da nota,
  com venda sugerida de custo + 30%. **O número no nome não vira estoque.**
- Quantidade e custo derivados de embalagem configurada são calculados pela
  nota e pelo cadastro. Corrija o fator no cadastro antes de reimportar; a prévia
  não muda o cadastro nem os preços de venda de um produto existente.

Caso conferido com XML baixado: NF-e **446817**, `CX 00050 KAISER LT 350ML`,
`uCom=UN`, `qCom=600`, custo **R$ 2,74**. Sem confirmar abertura, entram
**600 UN**, com venda sugerida **R$ 3,56**. O “50” do nome não multiplica nada.

No recibo sai o que o cliente levou: **1 CARTEIRA a R$ 20** e **1 UN a R$ 2**.
No XML fiscal, CARTEIRA é abreviada como **CART** para respeitar o limite de
seis caracteres; a descrição preserva o nome. O grupo tributável usa as unidades
menores. Esta entrega continua em **homologação**, sem transmissão à SEFAZ.

#### Contrato de integração

Produto: `vende_por_unidade` (padrão false), `preco_embalagem`, `preco_unidade`,
`codigo_barras_unidade` opcional, mais `unidade_compra` e
`quantidade_por_embalagem` existentes. Checkout: `modo_venda` = `embalagem`
ou `unidade`. **Sem modo, vende unidade** nos produtos com a opção ligada.
Produto desligado mantém `preco_venda` e baixa 1 para 1.
Cada item vendido grava `unidade_venda`, `quantidade_estoque`, `modo_venda`
e `custo_unitario_estoque`; itens antigos mantêm o comportamento anterior.

### Rotina geral

- Cada produto tem **estoque** e **estoque mínimo**.
- **Venda** baixa o estoque automaticamente (e bloqueia se faltar).
- **Estoque baixo**: o Dashboard mostra alerta quando `estoque <= estoque_mínimo`.
- **Entrada manual**: na tela Produtos, botão **"+ Estoque"** soma uma quantidade
  ao produto (ex.: compra avulsa).
- **Ajuste manual**: na tela Produtos, botão **"Ajustar"** corrige o estoque fora
  de venda/entrada. Três tipos:
  - **Perda** — baixa a quantidade informada (ex.: produto vencido).
  - **Quebra** — baixa a quantidade informada (ex.: avaria).
  - **Inventário** — você informa a **contagem real** e o sistema acerta o
    estoque, lançando a diferença como entrada (sobra) ou saída (falta).
  Perda/quebra são bloqueadas se a quantidade passar do estoque disponível.
- **Histórico de movimentações**: toda entrada (XML/manual), saída (venda) e
  ajuste (perda/quebra/inventário) fica registrada em `movimentacoes_estoque`
  (tipo, quantidade, origem, documento). Na tela Produtos, o botão **"Histórico"**
  abre o painel com tudo que entrou e saiu do produto.

## Importação de XML (NF-e de entrada)

Quando o fornecedor entrega a mercadoria, ele manda a **NF-e (arquivo .xml)**.
Importando esse XML, o sistema dá entrada no estoque de uma vez.

### Passo a passo (tela Produtos → "📄 Importar XML")

1. Clique em **📄 Importar XML** e selecione o arquivo `.xml` da NF-e.
2. O sistema lê a nota e abre um **diálogo** com a prévia. Os itens já vêm
   **casados pelo código de barras (EAN)** com o seu cadastro. Dá para marcar
   ou desmarcar todos de uma vez:
   - **Repor**: o produto já existe → vai **somar** a quantidade ao estoque.
   - **Criar novo**: não existe → será **cadastrado** (você define o preço de venda).
3. Confira/edite **quantidade** e **custo** de cada item; desmarque o que não
   quiser importar.
4. **Confirmar importação**. Pronto: estoque atualizado e novos produtos criados.

### O que é lido do XML

Por item: nome (`xProd`), código de barras (`cEAN`, "SEM GTIN" vira vazio),
unidade (`uCom`), quantidade (`qCom`), custo unitário (`vUnCom`), NCM e CFOP.
Também o fornecedor (`emit/xNome`) e o número da nota.

### Regras de negócio

- O **casamento** é por código de barras. Itens "SEM GTIN" entram como **novos**
  (você pode depois editar e juntar manualmente, se for o caso).
- Ao **repor**, o **preço de custo é atualizado** com o valor da nota (pode
  desligar isso por item futuramente; hoje atualiza por padrão).
- Ao **criar**, o preço de venda sugerido é **custo + 30%** (editável na prévia).
- Com chave preenchida, a mesma NF-e só pode ser confirmada **uma vez por usuário**;
  repetição devolve 409. A tela encaminha a chave da prévia para a confirmação,
  e apresenta a recusa e seu código de referência dentro do modal. Sem chave,
  não há deduplicação por documento.
- Produto, campos fiscais, quantidade/custo, movimentos e chave são gravados na
  **mesma transação SQLite**. Falha em qualquer escrita desfaz o lote inteiro;
  uma nova tentativa não duplica a primeira parte. Duas confirmações da mesma
  chave em conexões diferentes geram uma entrada e uma recusa.
- Referência inexistente, inativa ou de outro usuário recusa o lote com 400.
  Não se ignora um item para importar só os demais.
- Lote vazio e valores não finitos são recusados antes de gravar (422).
- A prévia aceita somente raiz NFe/nfeProc, modelo 55. GTIN deve ter 8, 12,
  13 ou 14 dígitos ASCII e verificador válido, ou ser vazio/SEM GTIN. Quantidade
  precisa ser positiva; custo, não negativo; ambos finitos. Item sem produto
  ou nome também recusa o XML inteiro com 400, em vez de sumir da prévia.
  Essa leitura não substitui validação XSD, assinatura digital ou situação da
  nota na SEFAZ: esses portões fiscais são separados.
- Se a nota chega em UN, o fator/unidade de compra do cadastro é preservado;
  a conversão de CX usa o fator configurado na prévia.

## API (backend, exige JWT)

| Método | Rota | Função |
|---|---|---|
| `POST` | `/api/produtos/importar-xml/preview` | envia o XML cru; devolve itens casados |
| `POST` | `/api/produtos/importar-xml/confirmar` | aplica a entrada (repõe/cria) |
| `POST` | `/api/produtos/{id}/entrada` | entrada manual de estoque |
| `POST` | `/api/produtos/{id}/ajuste` | ajuste manual: `tipo` = `perda`/`quebra`/`inventario` |
| `GET`  | `/api/produtos/{id}/movimentacoes` | histórico de movimentações do produto |

> Tudo isso roda no **.exe local** (offline-first). A importação de XML não
> depende de internet — é leitura de arquivo.
