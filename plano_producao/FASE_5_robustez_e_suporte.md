# Fase 5 — Robustez e suporte

**Status:** ⬜ não iniciada · **Depende de:** Fases 1 a 4 · **Pistas:** P8, P13 · **Testes:** R01–R09

## Objetivo

O que faz a loja não ligar às 18h de sábado: backup que restaura, sistema que abre mesmo com problema, e uma tela que diz ao suporte o que está errado.

## Tarefas

### Backup e recuperação

- [ ] F5.1 (P8) `PRAGMA integrity_check` em cada backup gerado; backup reprovado é apagado e o erro vai para o log. Teste R01
- [ ] F5.2 (P8) Loop de backup registra falha no log em vez de engolir. Retenção conferida (R02). Nome do arquivo com hora local
- [ ] F5.3 (P8) Restauração valida o arquivo antes de trocar: `integrity_check` + tabelas do VendaFácil presentes. Arquivo ruim é recusado e o banco atual fica intacto (R04)
- [ ] F5.4 Restauração provada em banco novo: contagens iguais antes e depois (R03)
- [ ] F5.5 Backup durante vendas concorrentes (R06)
- [ ] F5.6 (P8) Banco corrompido na abertura: o sistema sobe em **modo consulta**, mostra aviso com o caminho do último backup bom e não deixa vender em cima de banco quebrado (R05)

### Operação

- [ ] F5.7 Log: conferir o rotativo de `errors.py` — pasta `logs/` dentro da pasta de dados, tamanho e quantidade de arquivos, sem dado sensível (R07)
- [ ] F5.8 Segunda instância do `.exe`: abre o navegador na que já está rodando, sem erro mudo (R09)
- [ ] F5.9 Desligamento: fechar o `.exe` ou cair a luz no meio de backup ou transmissão não corrompe (WAL conferido depois)

### Suporte

- [ ] F5.10 (P13) Diagnóstico: endpoint autenticado + tela. Campos: versão, caminho do banco, tamanho do banco, espaço livre, último backup e resultado do `integrity_check`, ambiente fiscal, validade do certificado, resposta do `statusServico`, notas pendentes e em contingência, última sincronização com o painel. Nenhum segredo (R08)
- [ ] F5.11 Botão "copiar diagnóstico" para o lojista mandar ao suporte

## Complementos da auditoria

- [ ] F5.12 P39: watchdog não interrompe transação; serviço alheio na porta não é PDV; R10

## Portão de saída

- [ ] R01–R09 ✅ em `03_TESTES.md`
- [ ] `docs/BACKUP.md` atualizado (inclui "como restaurar" passo a passo)
- [ ] Suítes verdes; pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte | | |
| Restauração (R03) | | |
| Banco corrompido (R05) | | |
| Diagnóstico (R08) | | |
