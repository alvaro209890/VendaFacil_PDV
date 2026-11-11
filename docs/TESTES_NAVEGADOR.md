# Testes de navegador do PDV

**O que é:** automação de regressão do caixa com Chromium/Playwright.
**Onde roda:** Windows de desenvolvimento, na raiz deste repositório.
**Para que serve:** reproduzir teclado, rascunho, foco, decimais e mensagens sem usar a loja real.

## Preparação

Requer Node 22, o ambiente Python `backend/.venv` com as dependências do backend instaladas e portas locais 3121/5173 livres.
Playwright está em `devDependencies`; não faz parte do executável entregue ao cliente.

```bash
npm ci
npx playwright install chromium
```

No bash deste Windows, defina explicitamente o diretório temporário antes de executar.
Não suponha que o `TMPDIR` herdado já aponta para o scratch do agente.

```bash
export TMPDIR='C:/Users/Usuario/AppData/Local/hermes/cache/scratch'
npx playwright test --reporter=line
```

Em outro ambiente de desenvolvimento, escolha uma pasta temporária sob sua própria conta.
O harness atual usa o Python Windows de `backend/.venv/Scripts/python.exe`.

## Roteiros

```bash
# U01–U04: carrinho, teclado, foco e decimais
npx playwright test e2e/carrinho.spec.ts e2e/teclado.spec.ts e2e/foco.spec.ts e2e/decimais.spec.ts --reporter=line

# Repetir um roteiro sem esconder falhas com retry
npx playwright test e2e/decimais.spec.ts --repeat-each=2 --reporter=line

# Erros de estoque/caixa e apresentação do retorno fiscal
npx playwright test e2e/erros.spec.ts --reporter=line
```

As amostras de decimais incluem literalmente `1,5` e `1.5` em quantidade e desconto, além da edição parcial começando em zero e entradas inválidas.
A verificação não se limita ao texto: confere também o JSON enviado e o total devolvido pelo backend.

## Isolamento e limites

- `e2e/servidor.cjs` cria uma pasta nova `vf-e2e-*` em `TMPDIR`, com SQLite e chave JWT descartáveis.
- A API de teste usa `127.0.0.1:3121`; Vite usa `127.0.0.1:5173`. Não se conecta ao PDV real de `3020`.
- O harness remove `PYTHONPATH` e o segredo JWT herdado, usa Python isolado e desliga a URL do painel de licença.
- Vite só fica disponível após o health da API. O teste não reutiliza um servidor anterior e roda com um worker e zero retries.
- Trace e screenshot ficam desligados. Não habilite logs de cabeçalhos/corpos nem versione tokens ou dados temporários.
- Pastas temporárias podem permanecer depois da execução; são dados sintéticos, não backup da loja. Não confunda com `%LOCALAPPDATA%/VendaFacilPDV/dados`.
- Estoque insuficiente, venda com caixa fechado e emissão fiscal desabilitada exercitam a API local real.
- Os estados fiscais rejeitada/pendente/contingência/autorizada em `erros.spec.ts` são **fixtures interceptadas apenas para apresentação da UI**. Não provam autorização, assinatura, XSD, QR fiscal ou comunicação SEFAZ-MT.
- Nenhum certificado, CSC ou cadastro real da mercearia é necessário para estes roteiros. A homologação fiscal tem portões separados na Fase 4.

Um teste de caracterização que já passa amplia a cobertura; não é prova inventada de RED→GREEN.
Consulte `plano_producao/evidencias/` e a matriz para os resultados efetivamente executados.
