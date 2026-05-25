# Refatoração mobile do frontend

## Objetivo

Preparar o frontend do VendaFácil PDV para uso confortável em celulares, com foco em telas pequenas, toque com o dedo e navegação rápida entre módulos do PDV.

## Principais mudanças

- Navegação mobile movida do topo para uma barra fixa inferior.
- Topbar mobile simplificada com nome da tela atual.
- Uso de `100dvh` para reduzir problemas causados pela barra do navegador em celulares.
- Espaçamento inferior no conteúdo para não ficar escondido atrás da navegação.
- Áreas clicáveis maiores com a classe utilitária `touch-target`.
- Modais com limite de altura e rolagem interna por meio de `modal-panel`.
- Prevenção de overflow horizontal global.
- Inputs em mobile com fonte mínima de 16px para evitar zoom automático no iOS.

## Telas revisadas

- Login
- Dashboard
- PDV
- Produtos
- Categorias
- Clientes
- Vendas
- Contas a Receber

## Ajustes por tela

### Layout geral

Arquivo: `src/App.tsx`

- Sidebar desktop preservada.
- Mobile usa topbar + bottom navigation.
- Itens de navegação receberam rótulo curto para caber melhor na barra inferior.

### Estilos globais

Arquivo: `src/index.css`

- Adicionadas classes utilitárias:
  - `app-shell`
  - `touch-target`
  - `mobile-scrollbar`
  - `safe-bottom`
  - `mobile-topbar`
  - `modal-panel`

### PDV

Arquivo: `src/pages/PDV.tsx`

- Cards de produtos com altura mínima maior para toque.
- Carrinho com altura máxima relativa à viewport.
- Grade de formas de pagamento ajustada para telas estreitas.
- Modal PIX com scroll interno.

### Produtos

Arquivo: `src/pages/Produtos.tsx`

- Tabela substituída por cards no mobile.
- Tabela mantida em telas `sm` ou maiores.
- Ações de edição/desativação com botões maiores.

### Vendas

Arquivo: `src/pages/Vendas.tsx`

- Histórico exibido como cards no mobile.
- Tabela mantida em telas maiores.
- Botão de detalhes ocupa largura total no mobile.

### Clientes, Categorias e Contas a Receber

Arquivos:

- `src/pages/Clientes.tsx`
- `src/pages/Categorias.tsx`
- `src/pages/ContasReceber.tsx`

- Cards quebram em coluna em telas pequenas.
- Botões de ação ficam em grid para facilitar toque.
- Modais receberam `modal-panel`.

## Validação

Comandos executados:

```bash
npm run lint
npm run build
```

Ambos devem passar antes de publicar.

Também foi feita verificação visual em viewport mobile `390x844` usando Chrome headless nas principais rotas autenticadas.
