"""Banco do Painel SaaS VendaFácil (roda na VPS).

Guarda os ADMINs (você, dono do sistema), as CONTAS das lojas (cada mercado
que compra/aluga o sistema) e um espelho das VENDAS sincronizadas pelos PDVs
para você acompanhar de forma centralizada.
"""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _data_dir() -> Path:
    env = os.environ.get("PAINEL_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent / "dados"


DATA_DIR = _data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "painel.db"


def agora() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    nome TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS contas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_loja TEXT NOT NULL,
                    login TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    plano TEXT NOT NULL DEFAULT 'mensal',
                    licenca_expira_em TEXT,
                    observacao TEXT,
                    criado_em TEXT NOT NULL,
                    ultimo_acesso TEXT
                );

                CREATE TABLE IF NOT EXISTS vendas_sync (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conta_id INTEGER NOT NULL,
                    venda_uuid TEXT NOT NULL,
                    total REAL NOT NULL,
                    desconto REAL NOT NULL DEFAULT 0,
                    forma_pagamento TEXT,
                    criado_em_local TEXT,
                    recebido_em TEXT NOT NULL,
                    payload TEXT,
                    UNIQUE(conta_id, venda_uuid)
                );
                """
            )

    # ── Admins ──
    def get_admin_by_email(self, email: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM admins WHERE email = ?", (email.lower(),)
            ).fetchone()
            return dict(row) if row else None

    def count_admins(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) c FROM admins").fetchone()["c"]

    def create_admin(self, email: str, nome: str, senha_hash: str) -> Optional[dict]:
        with self._lock, self._conn:
            try:
                cur = self._conn.execute(
                    "INSERT INTO admins (email, nome, senha_hash, criado_em) VALUES (?,?,?,?)",
                    (email.lower(), nome, senha_hash, agora()),
                )
                return {"id": cur.lastrowid, "email": email.lower(), "nome": nome}
            except sqlite3.IntegrityError:
                return None

    # ── Contas (lojas) ──
    def listar_contas(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, nome_loja, login, ativo, plano, licenca_expira_em, "
                "observacao, criado_em, ultimo_acesso FROM contas ORDER BY criado_em DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_conta_by_login(self, login: str) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM contas WHERE login = ?", (login.lower(),)
            ).fetchone()
            return dict(row) if row else None

    def get_conta(self, conta_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM contas WHERE id = ?", (conta_id,)
            ).fetchone()
            return dict(row) if row else None

    def criar_conta(
        self, nome_loja: str, login: str, senha_hash: str, plano: str,
        licenca_expira_em: Optional[str], observacao: Optional[str],
    ) -> Optional[dict]:
        with self._lock, self._conn:
            try:
                cur = self._conn.execute(
                    "INSERT INTO contas (nome_loja, login, senha_hash, ativo, plano, "
                    "licenca_expira_em, observacao, criado_em) VALUES (?,?,?,1,?,?,?,?)",
                    (nome_loja, login.lower(), senha_hash, plano,
                     licenca_expira_em, observacao, agora()),
                )
                return self.get_conta(cur.lastrowid)
            except sqlite3.IntegrityError:
                return None

    def atualizar_conta(self, conta_id: int, campos: dict) -> bool:
        if not campos:
            return False
        permitidos = {"nome_loja", "ativo", "plano", "licenca_expira_em",
                      "observacao", "senha_hash"}
        sets, vals = [], []
        for k, v in campos.items():
            if k in permitidos:
                sets.append(f"{k} = ?")
                vals.append(v)
        if not sets:
            return False
        vals.append(conta_id)
        with self._lock, self._conn:
            cur = self._conn.execute(
                f"UPDATE contas SET {', '.join(sets)} WHERE id = ?", vals
            )
            return cur.rowcount > 0

    def marcar_acesso(self, conta_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE contas SET ultimo_acesso = ? WHERE id = ?", (agora(), conta_id)
            )

    # ── Vendas sincronizadas ──
    def registrar_venda_sync(self, conta_id: int, v: dict) -> bool:
        import json
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO vendas_sync (conta_id, venda_uuid, total, desconto, "
                    "forma_pagamento, criado_em_local, recebido_em, payload) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (conta_id, v.get("uuid"), float(v.get("total", 0)),
                     float(v.get("desconto", 0)), v.get("forma_pagamento"),
                     v.get("criado_em"), agora(), json.dumps(v, ensure_ascii=False)),
                )
                return True
            except sqlite3.IntegrityError:
                return False  # já recebida (idempotente)

    def resumo_vendas(self, conta_id: int) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) qtd, COALESCE(SUM(total),0) total FROM vendas_sync "
                "WHERE conta_id = ?", (conta_id,)
            ).fetchone()
            return {"qtd_vendas": row["qtd"], "total_vendido": row["total"]}


db = Database()
