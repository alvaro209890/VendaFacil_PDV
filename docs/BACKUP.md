# 💾 Backup local

Os dados do lojista (produtos, vendas, estoque, caixa) ficam num arquivo SQLite
**na própria máquina** do .exe. O Backup protege contra perda de dados.

## O que tem

- **Backup automático**: feito a cada inicialização do sistema e **uma vez por
  dia**, guardando os **últimos 14** na pasta `dados/backups` ao lado dos dados.
- **Baixar backup** (menu **Backup** → "Baixar backup agora"): gera um `.db`
  consistente e baixa pelo navegador. **Guarde fora do PC** (pen drive/nuvem).
- **Restaurar**: envie um arquivo `.db` de backup para voltar a um estado
  anterior. Antes de substituir, o sistema **salva o estado atual** automaticamente
  (backup `pre-restauracao`), e valida o arquivo.

> ⚠️ Restaurar **substitui todos os dados atuais**. Use com cuidado. A página
> recarrega após a restauração.

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
