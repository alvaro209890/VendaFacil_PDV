# Fase 5 — Robustez e suporte

**Status:** ✅ 12/12 tarefas implementadas; duas suítes verdes · **Depende de:** Fases 1 a 4 · **Pistas:** P8, P13 · **Testes:** R01–R09

## Objetivo

O que faz a loja não ligar às 18h de sábado: backup que restaura, sistema que abre mesmo com problema, e uma tela que diz ao suporte o que está errado.

## Tarefas

### Backup e recuperação

- [x] F5.1 (P8) `PRAGMA integrity_check` em cada backup gerado; backup reprovado é apagado e o erro vai para o log. Teste R01 — 73ae8f2 · F5_R01_RED.txt (1 falha) e F5_R01_GREEN.txt (3 verdes)
- [x] F5.2 (P8) Loop de backup registra falha no log em vez de engolir. Retenção conferida (R02). Nome do arquivo com hora local — 1979b2e · F5_R02_RED.txt (2 falhas) e F5_R02_GREEN.txt (5 verdes)
- [x] F5.3 (P8) Restauração valida o arquivo antes de trocar: `integrity_check` + tabelas do VendaFácil presentes. Arquivo ruim é recusado e o banco atual fica intacto (R04) — 1ee3df3 · F5_R04_RED.txt (1 falha) e F5_R03_R04_GREEN.txt (26 verdes)
- [x] F5.4 Restauração provada em banco novo: contagens iguais antes e depois (R03) — 1ee3df3 · R03 em F5_R03_R04_GREEN.txt; contagens iguais nas cinco tabelas
- [x] F5.5 Backup durante vendas concorrentes (R06) — f7abe37 · F5_R06_GREEN.txt; duas threads com 10 checkouts e cópia consistente
- [x] F5.6 (P8) Banco corrompido na abertura: o sistema sobe em **modo consulta**, mostra aviso com o caminho do último backup bom e não deixa vender em cima de banco quebrado (R05) — 15696f5/c387de0 · F5_R05_GREEN.txt e F5_RECUPERACAO_AUTH_GREEN.txt; subprocessos em consulta com e sem cópia válida

### Operação

- [x] F5.7 Log: conferir o rotativo de `errors.py` — pasta `logs/` dentro da pasta de dados, tamanho e quantidade de arquivos, sem dado sensível (R07) — 3d2882b · F5_R07_GREEN.txt; rotação de 1 MB, cinco arquivos antigos e sanitização
- [x] F5.8 Segunda instância do `.exe`: abre o navegador na que já está rodando, sem erro mudo (R09) — e6885ba · F5_INSTANCIA_GREEN.txt; run.main reutiliza somente serviço identificado em porta ocupada
- [x] F5.9 Desligamento: fechar o `.exe` ou cair a luz no meio de backup ou transmissão não corrompe (WAL conferido depois) — 9989418/f1bdf6a · F5_TRANSMISSAO_GREEN.txt e F5_INSTANCIA_GREEN.txt; encerramento do subprocesso durante SOAP e backup, WAL e integridade confirmados

### Suporte

- [x] F5.10 (P13) Diagnóstico: endpoint autenticado + tela. Campos: versão, caminho do banco, tamanho do banco, espaço livre, último backup e resultado do `integrity_check`, ambiente fiscal, validade do certificado, resposta do `statusServico`, notas pendentes e em contingência, última sincronização com o painel. Nenhum segredo (R08) — f25d05f/aa2ea37 · F5_R08_GREEN.txt (20 verdes), build e lint
- [x] F5.11 Botão "copiar diagnóstico" para o lojista mandar ao suporte — aa2ea37 · F5_DIAGNOSTICO_CHROMIUM.txt (1 verde, clipboard real)

## Complementos da auditoria

- [x] F5.12 P39: watchdog não interrompe transação; serviço alheio na porta não é PDV; R10 — e6885ba/f1bdf6a · F5_INSTANCIA_GREEN.txt (34 verdes), serviço alheio e encerramento cooperativo

## Portão de saída

- [x] R01–R10 verdes na matriz — c387de0 · F5_PORTAO_BACKEND.txt
- [x] docs/BACKUP.md atualizado com restauração pela interface e recuperação após corrupção — c387de0 · R03/R05, F5_R03_R04_GREEN.txt e F5_RECUPERACAO_AUTH_GREEN.txt
- [ ] Suítes verdes; pasta do plano commitada e `git push origin master`

## Evidências

| Item | Comando | Saída resumida |
|---|---|---|
| Suíte | pytest -q --tb=short | Backend 459 verdes/9 desmarcados; painel 23 verdes, F5_PORTAO_BACKEND/PAINEL.txt |
| Restauração (R03) | pytest tests/test_backup_robustez.py | F5_R03_R04_GREEN.txt |
| Banco corrompido (R05) | pytest tests/test_recuperacao_local.py | F5_R05_GREEN.txt |
| Diagnóstico (R08) | pytest tests/test_diagnostico_local.py e playwright test e2e/diagnostico.spec.ts | F5_R08_GREEN.txt e F5_DIAGNOSTICO_CHROMIUM.txt |
