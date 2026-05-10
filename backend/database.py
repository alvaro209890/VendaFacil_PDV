import sqlite3
import threading
from pathlib import Path
from typing import Any

DB_DIR = Path("/media/server/HD Backup/Servidores_NAO_MEXA/Banco_de_dados/VendaFacil_PDV")
DB_PATH = DB_DIR / "vendafacil.db"


class Database:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    nome TEXT NOT NULL DEFAULT '',
                    senha_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    ultimo_login TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    preco_custo REAL NOT NULL DEFAULT 0,
                    preco_venda REAL NOT NULL DEFAULT 0,
                    estoque INTEGER NOT NULL DEFAULT 0,
                    estoque_minimo INTEGER NOT NULL DEFAULT 5,
                    codigo_barras TEXT DEFAULT '',
                    unidade TEXT NOT NULL DEFAULT 'UN',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_produtos_user ON produtos(user_id);
                CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos(nome);

                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    total REAL NOT NULL DEFAULT 0,
                    desconto REAL NOT NULL DEFAULT 0,
                    forma_pagamento TEXT NOT NULL DEFAULT 'dinheiro',
                    status TEXT NOT NULL DEFAULT 'concluida',
                    observacao TEXT DEFAULT '',
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_vendas_user ON vendas(user_id);
                CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas(criado_em);

                CREATE TABLE IF NOT EXISTS itens_venda (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venda_id INTEGER NOT NULL,
                    produto_id INTEGER NOT NULL,
                    nome_produto TEXT NOT NULL,
                    quantidade REAL NOT NULL DEFAULT 1,
                    preco_unitario REAL NOT NULL DEFAULT 0,
                    subtotal REAL NOT NULL DEFAULT 0,
                    FOREIGN KEY (venda_id) REFERENCES vendas(id),
                    FOREIGN KEY (produto_id) REFERENCES produtos(id)
                );
                CREATE INDEX IF NOT EXISTS idx_itens_venda ON itens_venda(venda_id);
            """)

    def create_user(self, email: str, nome: str, senha_hash: str, criado_em: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            try:
                cursor = self._conn.execute(
                    "INSERT INTO users (email, nome, senha_hash, criado_em) VALUES (?, ?, ?, ?)",
                    (email.strip().lower(), nome.strip(), senha_hash, criado_em),
                )
                return {"id": cursor.lastrowid, "email": email.strip().lower(), "nome": nome.strip()}
            except sqlite3.IntegrityError:
                return None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, email, nome, senha_hash FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()
        return dict(row) if row else None

    def update_last_login(self, email: str, timestamp: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET ultimo_login = ? WHERE email = ?",
                (timestamp, email.strip().lower()),
            )

    def update_password(self, email: str, senha_hash: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE users SET senha_hash = ? WHERE email = ?",
                (senha_hash, email.strip().lower()),
            )
        return cursor.rowcount > 0

    # ── Produtos ──

    def list_produtos(self, user_id: int, ativos_only: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            q = "SELECT * FROM produtos WHERE user_id = ?"
            if ativos_only:
                q += " AND ativo = 1"
            q += " ORDER BY nome"
            rows = self._conn.execute(q, (user_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_produto(self, produto_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        with self._lock:
            q = "SELECT * FROM produtos WHERE id = ?"
            params: tuple = (produto_id,)
            if user_id is not None:
                q += " AND user_id = ?"
                params = (produto_id, user_id)
            row = self._conn.execute(q, params).fetchone()
        return dict(row) if row else None

    def create_produto(self, user_id: int, nome: str, preco_custo: float,
                       preco_venda: float, estoque: int, estoque_minimo: int,
                       codigo_barras: str, unidade: str, agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO produtos (user_id, nome, preco_custo, preco_venda, estoque,
                   estoque_minimo, codigo_barras, unidade, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, nome.strip(), preco_custo, preco_venda, estoque,
                 estoque_minimo, codigo_barras.strip(), unidade.strip().upper(), agora, agora),
            )
            return self.get_produto(cursor.lastrowid)

    def update_produto(self, produto_id: int, user_id: int, **kwargs) -> dict[str, Any] | None:
        allowed = {"nome", "preco_custo", "preco_venda", "estoque",
                   "estoque_minimo", "codigo_barras", "unidade", "ativo", "atualizado_em"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return self.get_produto(produto_id, user_id)
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values())
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE produtos SET {sets} WHERE id = ? AND user_id = ?",
                vals + [produto_id, user_id],
            )
            return self.get_produto(produto_id, user_id)

    def baixar_estoque(self, produto_id: int, quantidade: float) -> bool:
        with self._lock, self._conn:
            row = self._conn.execute("SELECT estoque FROM produtos WHERE id = ?", (produto_id,)).fetchone()
            if not row or row[0] < quantidade:
                return False
            self._conn.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                (quantidade, produto_id),
            )
            return True

    # ── Vendas ──

    def list_vendas(self, user_id: int, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM vendas WHERE user_id = ? ORDER BY criado_em DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_venda(self, venda_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        with self._lock:
            q = "SELECT * FROM vendas WHERE id = ?"
            params: tuple = (venda_id,)
            if user_id is not None:
                q += " AND user_id = ?"
                params = (venda_id, user_id)
            row = self._conn.execute(q, params).fetchone()
        return dict(row) if row else None

    def create_venda(self, user_id: int, total: float, desconto: float,
                     forma_pagamento: str, observacao: str, itens: list[dict],
                     agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO vendas (user_id, total, desconto, forma_pagamento, status, observacao, criado_em)
                   VALUES (?, ?, ?, ?, 'concluida', ?, ?)""",
                (user_id, total, desconto, forma_pagamento, observacao, agora),
            )
            venda_id = cursor.lastrowid
            for item in itens:
                self._conn.execute(
                    """INSERT INTO itens_venda (venda_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (venda_id, item["produto_id"], item["nome_produto"],
                     item["quantidade"], item["preco_unitario"], item["subtotal"]),
                )
            return self.get_venda(venda_id)

    def get_itens_venda(self, venda_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM itens_venda WHERE venda_id = ? ORDER BY id",
                (venda_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_venda_completa(self, venda_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        venda = self.get_venda(venda_id, user_id)
        if not venda:
            return None
        venda["itens"] = self.get_itens_venda(venda_id)
        return venda

    # ── Métricas / Dashboard ──

    def get_dashboard(self, user_id: int) -> dict[str, Any]:
        with self._lock:
            hoje = self._conn.execute(
                "SELECT date('now', 'localtime')"
            ).fetchone()[0]

            total_produtos = self._conn.execute(
                "SELECT COUNT(*) FROM produtos WHERE user_id = ? AND ativo = 1",
                (user_id,),
            ).fetchone()[0]

            alertas_estoque = self._conn.execute(
                "SELECT COUNT(*) FROM produtos WHERE user_id = ? AND ativo = 1 AND estoque <= estoque_minimo",
                (user_id,),
            ).fetchone()[0]

            vendas_hoje = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM vendas WHERE user_id = ? AND date(criado_em) = ?",
                (user_id, hoje),
            ).fetchone()

            total_vendas = self._conn.execute(
                "SELECT COALESCE(SUM(total), 0) FROM vendas WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]

            ultimas_vendas_rows = self._conn.execute(
                "SELECT id, total, forma_pagamento, criado_em FROM vendas WHERE user_id = ? ORDER BY criado_em DESC LIMIT 5",
                (user_id,),
            ).fetchall()

            produtos_baixo = self._conn.execute(
                "SELECT id, nome, estoque, estoque_minimo FROM produtos WHERE user_id = ? AND ativo = 1 AND estoque <= estoque_minimo ORDER BY estoque LIMIT 5",
                (user_id,),
            ).fetchall()

        return {
            "total_produtos": total_produtos,
            "alertas_estoque": alertas_estoque,
            "vendas_hoje_qtd": vendas_hoje[0],
            "vendas_hoje_total": vendas_hoje[1],
            "vendas_total": total_vendas,
            "ultimas_vendas": [dict(r) for r in ultimas_vendas_rows],
            "produtos_baixo_estoque": [dict(r) for r in produtos_baixo],
        }

    def close(self) -> None:
        self._conn.close()


# Singleton
db = Database()
