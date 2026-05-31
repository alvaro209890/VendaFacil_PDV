# 📦 Estoque e importação de XML (NF-e)

Como o controle de estoque funciona no VendaFácil PDV e como dar entrada de
mercadoria importando o XML da nota do fornecedor.

## Como o estoque funciona

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
2. O sistema lê a nota e mostra uma **prévia** com os itens já **casados pelo
   código de barras (EAN)** com o seu cadastro:
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
