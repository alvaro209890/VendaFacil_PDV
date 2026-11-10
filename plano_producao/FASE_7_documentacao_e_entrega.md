# Fase 7 — Documentação e entrega

**Status:** ⬜ não iniciada · **Depende de:** Fases 0 a 6

## Objetivo

Deixar tudo escrito: o que mudou, como a loja opera, como se implanta, e uma lista única do que o Álvaro precisa fazer.

## Tarefas

### Documentos novos em `docs/`

- [ ] F7.1 `docs/IMPLANTACAO_MERCEARIA.md` — roteiro de instalação na loja, item a item, com a evidência a colher: instalar, primeiro acesso e troca de senha, cadastro mínimo de produtos (código de barras, preço, estoque, unidade), formas de pagamento e maquininha, fiscal em homologação (certificado, CSC, empresa), impressora, backup ligado e restauração testada, licença com validade
- [ ] F7.2 `docs/TREINAMENTO_OPERADOR.md` — 20 minutos: abrir caixa, vender com leitor, sangria, fiado e recebimento, cancelar venda, fechar caixa, o que fazer se a nota não autorizar
- [ ] F7.3 `docs/SUPORTE_LOJA.md` — 1 página para imprimir: caiu a luz, caiu a internet, o sistema não abre, a nota ficou pendente, como mandar o diagnóstico, contato de suporte (campo em branco para o Álvaro preencher)
- [ ] F7.4 `docs/SEGURANCA.md` revisado (criado na Fase 3)

### Documentos existentes

- [ ] F7.5 Revisar e corrigir tudo que mudou de comportamento: `MANUAL.md`, `CAIXA.md`, `BACKUP.md`, `TESTES.md`, `TESTE_WINDOWS.md`, `TESTE_FISCAL_WINDOWS.md`, `CONTINGENCIA_OFFLINE.md`, `LEGISLACAO_FISCAL_MT.md`, `ESTOQUE_E_XML.md`, `LICENCA.md`, `docs/README.md` (índice)
- [ ] F7.6 `docs/CHECKLIST_COMERCIALIZACAO.md`: marcar o que ficou pronto e o que segue aberto, com a data
- [ ] F7.7 (P16, P18) `CLAUDE.md`: corrigir o que não é verdade (binários trackeados, build pelo GitHub Actions) e apontar para `plano_producao/`

### Fechamento do plano

- [ ] F7.8 Conferência final: nenhum `[ ]` nem `[~]` em nenhuma fase; nenhum ⬜ nem 🟥 em `03_TESTES.md`; toda pista com status final; toda decisão com "o que o agente fez" preenchido
- [ ] F7.9 Preencher `plano_producao/RELATORIO_FINAL.md`, incluindo a seção **"O que preciso de você"** — a lista única de pedidos ao Álvaro, em ordem de prioridade
- [ ] F7.10 Atualizar `00_PAINEL.md` com o estado final (✅ CONCLUÍDO ou ⏸ AGUARDANDO TERCEIRO)

### Segundo Cérebro e entrega

- [ ] F7.11 Ficha `02-projetos/vendafacil.md` no vault, via `ssh sd`, com o protocolo lock → patch → unlock → commit (autor `Hermes-windows`) e uma linha no `06-changelog.md`. Sem segredo. Sem acesso por SSH: deixar o texto pronto em `plano_producao/` e avisar
- [ ] F7.12 Commit final da pasta e dos docs, `git push origin master`, e conferir que `git status --porcelain` só mostra o binário modificado e o rascunho antigo

## Portão de saída

- [ ] `RELATORIO_FINAL.md` completo, com saída de comando em cada prova
- [ ] Painel no estado final
- [ ] Mensagem final ao Álvaro: veredito em 1 linha, números de teste, caminho do instalador e a lista "O que preciso de você"

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Conferência final (F7.8) | | |
| Commit do vault | | |
| Último `git log --oneline -1` | | |
