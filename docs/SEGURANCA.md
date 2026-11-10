# Segurança do PDV

Escolhas fechadas em 2026-11-10 para a mercearia. Não é auditoria completa; o restante entra na fase 3.

## Senha

- Mínimo de 8 caracteres no registro.
- Recusadas, além da senha igual ao usuário: `senha`, `1234`, `12345`, `123456`, `12345678`, `123456789`, `password`, `qwerty`, `admin`, `admin123`, `vendafacil`, `00000000`.
- Quem já entrou com senha antiga continua entrando. A regra vale para senha nova.

## Token de 30 dias

O token local dura 720 horas. A loja abre e fecha no mesmo PC, muitas vezes sem internet. Um token curto trancaria o caixa no meio do expediente se o painel não respondesse. Trinta dias cobrem o mês sem pedir senha todo dia, e o bloqueio da licença continua valendo na revalidação. Não é sessão de banco: é o caixa da loja.
