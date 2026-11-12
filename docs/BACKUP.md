# 💾 Backup local

Os dados do lojista (produtos, vendas, estoque, caixa) ficam num arquivo SQLite
**na própria máquina** do .exe. O Backup protege contra perda de dados.

## O que tem

- **Backup automático**: feito a cada inicialização do sistema e **uma vez por
  dia**, guardando os **últimos 14** na pasta `dados/backups` ao lado dos dados.
- **Baixar backup** (menu **Backup** → "Baixar backup agora"): gera um `.db`
  consistente e baixa pelo navegador. **Guarde fora do PC** (pen drive/nuvem).
- Cada cópia entra no histórico após o `PRAGMA integrity_check`. O nome usa a
  hora local. Falhas aparecem em `dados/logs/vendafacil.log`.

> ⚠️ Restaurar **substitui todos os dados atuais**. Use com cuidado. A página
> recarrega após a restauração.

## Restaurar com o PDV aberto

1. Pare de registrar vendas enquanto escolhe a cópia.
2. Em **Backup**, confira a data e clique em **Restaurar**. Selecione o `.db`
   da loja e confirme.
3. O sistema valida a integridade e as tabelas, prepara as migrações e grava
   um backup `pre-restauracao` antes de aplicar a cópia.
4. Depois da recarga, confira produtos, vendas, caixa e notas. Confira com o
   contador as notas emitidas após a data da cópia antes de voltar a emitir.

## Recuperar quando o banco não abre

O PDV mostra **Modo consulta** e o caminho do último backup válido dentro da
pasta de dados. Com uma cópia
disponível, entre com o usuário existente na data do backup para consultar os
registros. As operações de venda e as tarefas em segundo plano ficam bloqueadas.

1. Anote o caminho mostrado e feche todas as abas do PDV. Aguarde o programa
   encerrar antes de mover os arquivos.
2. Guarde uma cópia da pasta de dados inteira em local protegido. Na instalação
   padrão ela fica em `%LOCALAPPDATA%\VendaFacilPDV\dados`.
3. Mova `vendafacil.db` e os arquivos `vendafacil.db-wal` e
   `vendafacil.db-shm` que existirem para a pasta de recuperação. Deixe os
   arquivos juntos para eventual análise.
4. Copie o backup válido para a pasta de dados com o nome `vendafacil.db`.
   Abra o PDV e confirme em **Diagnóstico** que o banco está íntegro.
5. Reconcilie as vendas e notas posteriores ao backup antes de liberar o caixa.

O botão **Copiar diagnóstico** prepara um resumo de integridade, espaço livre,
backup, pendências fiscais e sincronização para enviar ao suporte. Compartilhe
o arquivo `.db` só quando necessário. Ele contém os dados da loja e pode incluir
credenciais fiscais.

## Por que baixar mesmo tendo backup automático?

Os backups automáticos ficam **na mesma máquina**. Se o computador pifar ou for
roubado, eles vão junto. Por isso: **baixe um backup periodicamente** e guarde em
outro lugar (pen drive, Google Drive, etc.).

## API (backend, exige JWT)

| Método | Rota | Função |
|---|---|---|
| `GET`  | `/api/backup/exportar` | gera e baixa um `.db` consistente |
| `GET`  | `/api/backup/listar` | lista os backups na máquina |
| `POST` | `/api/backup/restaurar` | restaura a partir de um `.db` (corpo da requisição) |

Detalhes técnicos: a cópia usa a **API de backup do SQLite** (`Connection.backup`),
segura mesmo com o sistema em uso. Variáveis: `VENDAFACIL_BACKUPS_MANTER` (padrão
14) e `VENDAFACIL_BACKUP_INTERVALO_SEG` (padrão 86400).
