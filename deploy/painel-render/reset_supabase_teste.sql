-- ============================================================================
-- VendaFacil Painel/Supabase - reset total e usuario teste
-- ============================================================================
-- Rode no Supabase > SQL Editor > New query > Run.
--
-- Login do painel admin:
--   usuario: teste
--   senha:   teste123
--
-- Login da loja/PDV para ativacao:
--   usuario: teste
--   senha:   teste123
--
-- ATENCAO: isto apaga admins, contas, vendas sincronizadas e configuracao
-- financeira do painel.
-- ============================================================================

CREATE TABLE IF NOT EXISTS admins (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    login       TEXT UNIQUE,
    nome        TEXT NOT NULL,
    senha_hash  TEXT NOT NULL,
    criado_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contas (
    id                 SERIAL PRIMARY KEY,
    nome_loja          TEXT NOT NULL,
    login              TEXT NOT NULL UNIQUE,
    senha_hash         TEXT NOT NULL,
    ativo              INTEGER NOT NULL DEFAULT 1,
    plano              TEXT NOT NULL DEFAULT 'mensal',
    licenca_expira_em  TEXT,
    observacao         TEXT,
    criado_em          TEXT NOT NULL,
    ultimo_acesso      TEXT
);

CREATE TABLE IF NOT EXISTS vendas_sync (
    id               SERIAL PRIMARY KEY,
    conta_id         INTEGER NOT NULL,
    venda_uuid       TEXT NOT NULL,
    total            DOUBLE PRECISION NOT NULL,
    desconto         DOUBLE PRECISION NOT NULL DEFAULT 0,
    forma_pagamento  TEXT,
    criado_em_local  TEXT,
    recebido_em      TEXT NOT NULL,
    payload          TEXT,
    UNIQUE (conta_id, venda_uuid)
);

CREATE TABLE IF NOT EXISTS fin_config (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    preco_por_loja  DOUBLE PRECISION NOT NULL DEFAULT 180,
    atualizado_em   TEXT
);

CREATE TABLE IF NOT EXISTS fin_custos (
    id     SERIAL PRIMARY KEY,
    nome   TEXT NOT NULL,
    valor  DOUBLE PRECISION NOT NULL DEFAULT 0,
    tipo   TEXT NOT NULL DEFAULT 'fixo',
    ativo  INTEGER NOT NULL DEFAULT 1
);

ALTER TABLE admins ADD COLUMN IF NOT EXISTS login TEXT;
UPDATE admins
SET login = LOWER(SPLIT_PART(email, '@', 1))
WHERE login IS NULL OR login = '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_login ON admins(login);
CREATE INDEX IF NOT EXISTS idx_vendas_sync_conta ON vendas_sync (conta_id);

TRUNCATE TABLE vendas_sync, contas, admins, fin_custos, fin_config RESTART IDENTITY;

INSERT INTO admins (email, login, nome, senha_hash, criado_em)
VALUES (
    'teste@local',
    'teste',
    'Admin Teste',
    '0123456789abcdef0123456789abcdef$1474e3a65a9a4ae03024b01c47414c6e2522166eadcf6c767a9429f71f2d90f0',
    NOW()::TEXT
);

INSERT INTO contas (
    nome_loja, login, senha_hash, ativo, plano, licenca_expira_em, observacao, criado_em
)
VALUES (
    'Loja Teste',
    'teste',
    '0123456789abcdef0123456789abcdef$1474e3a65a9a4ae03024b01c47414c6e2522166eadcf6c767a9429f71f2d90f0',
    1,
    'mensal',
    '2099-12-31T23:59:59+00:00',
    'Conta criada pelo reset_supabase_teste.sql',
    NOW()::TEXT
);

INSERT INTO fin_config (id, preco_por_loja, atualizado_em)
VALUES (1, 180, NOW()::TEXT);

INSERT INTO fin_custos (nome, valor, tipo, ativo)
VALUES
    ('Render - hospedagem da API (free)', 0, 'fixo', 1),
    ('Supabase - banco de dados (free)', 0, 'fixo', 1),
    ('Vercel - painel admin (free)', 0, 'fixo', 1);
