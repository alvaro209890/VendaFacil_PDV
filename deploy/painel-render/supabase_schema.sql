-- ============================================================================
-- VendaFácil — Painel SaaS · Schema do banco (Supabase / Postgres)
-- ============================================================================
-- Cole tudo isto no Supabase → SQL Editor → New query → Run.
--
-- Observação: o painel cria estas tabelas sozinho no primeiro boot. Rodar este
-- script é opcional, mas serve para preparar/conferir o banco antes do deploy.
-- É idempotente (IF NOT EXISTS) — pode rodar mais de uma vez sem quebrar.
-- ============================================================================

-- ── ADMINs (você, dono do sistema) ──
CREATE TABLE IF NOT EXISTS admins (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    login       TEXT UNIQUE,
    nome        TEXT NOT NULL,
    senha_hash  TEXT NOT NULL,
    criado_em   TEXT NOT NULL
);
UPDATE admins
SET login = LOWER(SPLIT_PART(email, '@', 1))
WHERE login IS NULL OR login = '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_login ON admins(login);

-- ── CONTAS (cada loja/mercado que usa o sistema) ──
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

-- ── VENDAS sincronizadas pelos PDVs (espelho para acompanhamento) ──
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
    UNIQUE (conta_id, venda_uuid)   -- idempotência: a mesma venda não entra 2x
);

-- Índice para acelerar os resumos por loja (COUNT/SUM por conta_id).
CREATE INDEX IF NOT EXISTS idx_vendas_sync_conta ON vendas_sync (conta_id);
