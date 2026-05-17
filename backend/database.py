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

                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    cor TEXT DEFAULT '#6366f1',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_categorias_user ON categorias(user_id);

                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    categoria_id INTEGER,
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
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
                );
                CREATE INDEX IF NOT EXISTS idx_produtos_user ON produtos(user_id);
                CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos(nome);
                CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id);

                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    telefone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    endereco TEXT DEFAULT '',
                    observacao TEXT DEFAULT '',
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_clientes_user ON clientes(user_id);
                CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome);

                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    cliente_id INTEGER,
                    total REAL NOT NULL DEFAULT 0,
                    desconto REAL NOT NULL DEFAULT 0,
                    forma_pagamento TEXT NOT NULL DEFAULT 'dinheiro',
                    status TEXT NOT NULL DEFAULT 'concluida',
                    observacao TEXT DEFAULT '',
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_vendas_user ON vendas(user_id);
                CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas(criado_em);
                CREATE INDEX IF NOT EXISTS idx_vendas_cliente ON vendas(cliente_id);

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

                CREATE TABLE IF NOT EXISTS contas_receber (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    venda_id INTEGER,
                    cliente_id INTEGER,
                    valor_total REAL NOT NULL DEFAULT 0,
                    valor_pendente REAL NOT NULL DEFAULT 0,
                    data_vencimento TEXT,
                    status TEXT NOT NULL DEFAULT 'pendente',
                    observacao TEXT DEFAULT '',
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (venda_id) REFERENCES vendas(id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_contas_receber_user ON contas_receber(user_id);
                CREATE INDEX IF NOT EXISTS idx_contas_receber_status ON contas_receber(status);
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
                       codigo_barras: str, unidade: str, agora: str,
                       categoria_id: int | None = None) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO produtos (user_id, categoria_id, nome, preco_custo, preco_venda, estoque,
                   estoque_minimo, codigo_barras, unidade, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, categoria_id, nome.strip(), preco_custo, preco_venda, estoque,
                 estoque_minimo, codigo_barras.strip(), unidade.strip().upper(), agora, agora),
            )
            return self.get_produto(cursor.lastrowid)

    def update_produto(self, produto_id: int, user_id: int, **kwargs) -> dict[str, Any] | None:
        allowed = {"nome", "categoria_id", "preco_custo", "preco_venda", "estoque",
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

    def create_venda(self, user_id: int, cliente_id: int | None,
                     total: float, desconto: float,
                     forma_pagamento: str, observacao: str, itens: list[dict],
                     agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO vendas (user_id, cliente_id, total, desconto, forma_pagamento, status, observacao, criado_em)
                   VALUES (?, ?, ?, ?, ?, 'concluida', ?, ?)""",
                (user_id, cliente_id, total, desconto, forma_pagamento, observacao, agora),
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

    # ── Categorias ──

    def list_categorias(self, user_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT c.*, COUNT(p.id) as total_produtos FROM categorias c "
                "LEFT JOIN produtos p ON p.categoria_id = c.id AND p.ativo = 1 "
                "WHERE c.user_id = ? AND c.ativo = 1 "
                "GROUP BY c.id ORDER BY c.nome",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_categoria(self, user_id: int, nome: str, cor: str, agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO categorias (user_id, nome, cor, criado_em) VALUES (?, ?, ?, ?)",
                (user_id, nome.strip(), cor, agora),
            )
            return {"id": cursor.lastrowid, "nome": nome.strip(), "cor": cor, "total_produtos": 0}

    def update_categoria(self, categoria_id: int, user_id: int, **kwargs) -> dict[str, Any] | None:
        allowed = {"nome", "cor", "ativo"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return None
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values())
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE categorias SET {sets} WHERE id = ? AND user_id = ?",
                vals + [categoria_id, user_id],
            )
            row = self._conn.execute(
                "SELECT * FROM categorias WHERE id = ?", (categoria_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_categoria(self, categoria_id: int, user_id: int) -> bool:
        with self._lock, self._conn:
            # Remove referência dos produtos
            self._conn.execute(
                "UPDATE produtos SET categoria_id = NULL WHERE categoria_id = ? AND user_id = ?",
                (categoria_id, user_id),
            )
            cursor = self._conn.execute(
                "UPDATE categorias SET ativo = 0 WHERE id = ? AND user_id = ?",
                (categoria_id, user_id),
            )
            return cursor.rowcount > 0

    # ── Clientes ──

    def list_clientes(self, user_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM clientes WHERE user_id = ? AND ativo = 1 ORDER BY nome",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_cliente(self, cliente_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        with self._lock:
            q = "SELECT * FROM clientes WHERE id = ?"
            params: tuple = (cliente_id,)
            if user_id is not None:
                q += " AND user_id = ?"
                params = (cliente_id, user_id)
            row = self._conn.execute(q, params).fetchone()
        return dict(row) if row else None

    def create_cliente(self, user_id: int, nome: str, telefone: str, email: str,
                       endereco: str, observacao: str, agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO clientes (user_id, nome, telefone, email, endereco, observacao, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, nome.strip(), telefone.strip(), email.strip(),
                 endereco.strip(), observacao.strip(), agora, agora),
            )
            return self.get_cliente(cursor.lastrowid)

    def update_cliente(self, cliente_id: int, user_id: int, **kwargs) -> dict[str, Any] | None:
        allowed = {"nome", "telefone", "email", "endereco", "observacao", "ativo", "atualizado_em"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return self.get_cliente(cliente_id, user_id)
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values())
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE clientes SET {sets} WHERE id = ? AND user_id = ?",
                vals + [cliente_id, user_id],
            )
            return self.get_cliente(cliente_id, user_id)

    # ── Contas a Receber / Venda Fiada ──

    def list_contas_receber(self, user_id: int, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            q = """SELECT cr.*, cl.nome as cliente_nome,
                    COALESCE((SELECT COUNT(*) FROM vendas v WHERE v.id = cr.venda_id), 0) as tem_venda
                    FROM contas_receber cr
                    LEFT JOIN clientes cl ON cl.id = cr.cliente_id
                    WHERE cr.user_id = ?"""
            params: list = [user_id]
            if status:
                q += " AND cr.status = ?"
                params.append(status)
            q += " ORDER BY cr.data_vencimento IS NULL, cr.data_vencimento, cr.criado_em DESC"
            rows = self._conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    def get_conta_receber(self, conta_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        with self._lock:
            q = """SELECT cr.*, cl.nome as cliente_nome
                    FROM contas_receber cr
                    LEFT JOIN clientes cl ON cl.id = cr.cliente_id
                    WHERE cr.id = ?"""
            params: tuple = (conta_id,)
            if user_id is not None:
                q += " AND cr.user_id = ?"
                params = (conta_id, user_id)
            row = self._conn.execute(q, params).fetchone()
        return dict(row) if row else None

    def create_conta_receber(self, user_id: int, cliente_id: int | None, venda_id: int | None,
                              valor_total: float, data_vencimento: str | None,
                              observacao: str, agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO contas_receber (user_id, venda_id, cliente_id, valor_total,
                   valor_pendente, data_vencimento, status, observacao, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)""",
                (user_id, venda_id, cliente_id, valor_total, valor_total,
                 data_vencimento, observacao, agora, agora),
            )
            return self.get_conta_receber(cursor.lastrowid)

    def pagar_conta_receber(self, conta_id: int, user_id: int, valor: float, agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM contas_receber WHERE id = ? AND user_id = ?",
                (conta_id, user_id),
            ).fetchone()
            if not row:
                return None
            novo_pendente = round(row["valor_pendente"] - valor, 2)
            if novo_pendente <= 0:
                self._conn.execute(
                    "UPDATE contas_receber SET valor_pendente = 0, status = 'pago', atualizado_em = ? WHERE id = ?",
                    (agora, conta_id),
                )
            else:
                self._conn.execute(
                    "UPDATE contas_receber SET valor_pendente = ?, status = 'parcial', atualizado_em = ? WHERE id = ?",
                    (novo_pendente, agora, conta_id),
                )
            return self.get_conta_receber(conta_id)

    def cancelar_conta_receber(self, conta_id: int, user_id: int, agora: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE contas_receber SET status = 'cancelado', atualizado_em = ? WHERE id = ? AND user_id = ?",
                (agora, conta_id, user_id),
            )
            return cursor.rowcount > 0

    # ── Dashboard (atualizado) ──

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

            # Novos indicadores
            contas_pendentes = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(valor_pendente), 0) FROM contas_receber "
                "WHERE user_id = ? AND status IN ('pendente', 'parcial')",
                (user_id,),
            ).fetchone()

        return {
            "total_produtos": total_produtos,
            "alertas_estoque": alertas_estoque,
            "vendas_hoje_qtd": vendas_hoje[0],
            "vendas_hoje_total": vendas_hoje[1],
            "vendas_total": total_vendas,
            "contas_pendentes_qtd": contas_pendentes[0],
            "contas_pendentes_total": contas_pendentes[1],
            "ultimas_vendas": [dict(r) for r in ultimas_vendas_rows],
            "produtos_baixo_estoque": [dict(r) for r in produtos_baixo],
        }

    def close(self) -> None:
        self._conn.close()


# Singleton
db = Database()
