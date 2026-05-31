import sqlite3
import threading
from typing import Any

from paths import DATA_DIR

DB_DIR = DATA_DIR
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
            self._migrar()

    def _migrar(self) -> None:
        """Migrações leves e idempotentes (adicionar colunas novas)."""
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(vendas)")}
        if "sincronizado" not in cols:
            self._conn.execute(
                "ALTER TABLE vendas ADD COLUMN sincronizado INTEGER NOT NULL DEFAULT 0"
            )
        if "uuid" not in cols:
            self._conn.execute("ALTER TABLE vendas ADD COLUMN uuid TEXT")

        # Campos fiscais nos produtos (NFC-e)
        pcols = {r["name"] for r in self._conn.execute("PRAGMA table_info(produtos)")}
        fiscais = {
            "ncm": "TEXT DEFAULT ''",
            "cest": "TEXT DEFAULT ''",
            "cfop": "TEXT DEFAULT '5102'",
            "origem": "TEXT DEFAULT '0'",
            "unidade_tributavel": "TEXT DEFAULT ''",
            "cst_csosn": "TEXT DEFAULT '102'",
            "aliquota_icms": "REAL DEFAULT 0",
            "cst_pis": "TEXT DEFAULT '07'",
            "aliquota_pis": "REAL DEFAULT 0",
            "cst_cofins": "TEXT DEFAULT '07'",
            "aliquota_cofins": "REAL DEFAULT 0",
        }
        for col, ddl in fiscais.items():
            if col not in pcols:
                self._conn.execute(f"ALTER TABLE produtos ADD COLUMN {col} {ddl}")

        # Configuração fiscal do emitente (1 linha) + notas emitidas
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS config_fiscal (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                habilitado INTEGER NOT NULL DEFAULT 0,
                razao_social TEXT DEFAULT '',
                nome_fantasia TEXT DEFAULT '',
                cnpj TEXT DEFAULT '',
                inscricao_estadual TEXT DEFAULT '',
                regime_tributario TEXT DEFAULT '1',
                logradouro TEXT DEFAULT '',
                numero TEXT DEFAULT '',
                bairro TEXT DEFAULT '',
                municipio TEXT DEFAULT '',
                codigo_municipio TEXT DEFAULT '',
                uf TEXT DEFAULT '',
                cep TEXT DEFAULT '',
                csc TEXT DEFAULT '',
                csc_id TEXT DEFAULT '',
                ambiente TEXT DEFAULT 'homologacao',
                gateway TEXT DEFAULT 'focusnfe',
                gateway_token TEXT DEFAULT '',
                serie INTEGER NOT NULL DEFAULT 1,
                proximo_numero INTEGER NOT NULL DEFAULT 1,
                atualizado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS notas_fiscais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venda_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                ref TEXT NOT NULL UNIQUE,
                modelo TEXT NOT NULL DEFAULT '65',
                numero INTEGER,
                serie INTEGER,
                ambiente TEXT,
                status TEXT NOT NULL DEFAULT 'pendente',
                chave TEXT,
                protocolo TEXT,
                mensagem TEXT,
                xml_url TEXT,
                danfe_url TEXT,
                qrcode_url TEXT,
                payload TEXT,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_nf_venda ON notas_fiscais(venda_id);
            CREATE INDEX IF NOT EXISTS idx_nf_status ON notas_fiscais(status);

            CREATE TABLE IF NOT EXISTS config_maquininha (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                habilitado INTEGER NOT NULL DEFAULT 0,
                provedor TEXT DEFAULT 'mercadopago',
                access_token TEXT DEFAULT '',
                device_id TEXT DEFAULT '',
                store_id TEXT DEFAULT '',
                pos_id TEXT DEFAULT '',
                imprimir_comprovante INTEGER NOT NULL DEFAULT 1,
                atualizado_em TEXT
            );

            CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,            -- entrada | saida | ajuste
                quantidade REAL NOT NULL,
                custo_unitario REAL,
                origem TEXT,                   -- xml | manual | venda
                documento TEXT,                -- nº/chave da NF-e (entrada por XML)
                observacao TEXT,
                criado_em TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mov_user ON movimentacoes_estoque(user_id);
            CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacoes_estoque(produto_id);

            CREATE TABLE IF NOT EXISTS caixa_sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                valor_abertura REAL NOT NULL DEFAULT 0,
                aberto_em TEXT NOT NULL,
                fechado_em TEXT,
                valor_fechamento REAL,
                valor_esperado REAL,
                diferenca REAL,
                observacao TEXT DEFAULT '',
                criado_em TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_caixa_user ON caixa_sessoes(user_id);

            CREATE TABLE IF NOT EXISTS caixa_movimentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sessao_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,          -- sangria | suprimento
                valor REAL NOT NULL,
                motivo TEXT DEFAULT '',
                criado_em TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_caixamov_sessao ON caixa_movimentos(sessao_id);
            """
        )

    # ── Sincronização ──
    def vendas_pendentes_sync(self, limite: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, uuid, total, desconto, forma_pagamento, criado_em "
                "FROM vendas WHERE sincronizado = 0 ORDER BY id LIMIT ?", (limite,)
            ).fetchall()
            return [dict(r) for r in rows]

    def set_venda_uuid(self, venda_id: int, valor: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE vendas SET uuid = ? WHERE id = ?", (valor, venda_id))

    def marcar_vendas_sincronizadas(self, ids: list[int]) -> None:
        if not ids:
            return
        marcas = ",".join("?" * len(ids))
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE vendas SET sincronizado = 1 WHERE id IN ({marcas})", ids
            )

    # ── Fiscal: configuração do emitente ──
    def get_config_fiscal(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM config_fiscal WHERE id = 1").fetchone()
            if not row:
                return {"habilitado": 0, "ambiente": "homologacao",
                        "gateway": "focusnfe", "serie": 1, "proximo_numero": 1}
            return dict(row)

    def salvar_config_fiscal(self, campos: dict, agora: str) -> dict[str, Any]:
        permitidos = {
            "habilitado", "razao_social", "nome_fantasia", "cnpj", "inscricao_estadual",
            "regime_tributario", "logradouro", "numero", "bairro", "municipio",
            "codigo_municipio", "uf", "cep", "csc", "csc_id", "ambiente", "gateway",
            "gateway_token", "serie", "proximo_numero",
        }
        dados = {k: v for k, v in campos.items() if k in permitidos and v is not None}
        with self._lock, self._conn:
            existe = self._conn.execute("SELECT 1 FROM config_fiscal WHERE id = 1").fetchone()
            if not existe:
                self._conn.execute("INSERT INTO config_fiscal (id) VALUES (1)")
            if dados:
                sets = ", ".join(f"{k} = ?" for k in dados)
                self._conn.execute(
                    f"UPDATE config_fiscal SET {sets}, atualizado_em = ? WHERE id = 1",
                    list(dados.values()) + [agora],
                )
        return self.get_config_fiscal()

    # ── Maquininha (Mercado Pago Point) ──
    def get_config_maquininha(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM config_maquininha WHERE id = 1"
            ).fetchone()
            if not row:
                return {"habilitado": 0, "provedor": "mercadopago",
                        "imprimir_comprovante": 1}
            return dict(row)

    def salvar_config_maquininha(self, campos: dict, agora: str) -> dict[str, Any]:
        permitidos = {
            "habilitado", "provedor", "access_token", "device_id",
            "store_id", "pos_id", "imprimir_comprovante",
        }
        dados = {k: v for k, v in campos.items() if k in permitidos and v is not None}
        with self._lock, self._conn:
            existe = self._conn.execute(
                "SELECT 1 FROM config_maquininha WHERE id = 1"
            ).fetchone()
            if not existe:
                self._conn.execute("INSERT INTO config_maquininha (id) VALUES (1)")
            if dados:
                sets = ", ".join(f"{k} = ?" for k in dados)
                self._conn.execute(
                    f"UPDATE config_maquininha SET {sets}, atualizado_em = ? WHERE id = 1",
                    list(dados.values()) + [agora],
                )
        return self.get_config_maquininha()

    def consumir_numero_nfce(self) -> tuple[int, int]:
        """Reserva o próximo número/série de NFC-e de forma atômica."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT serie, proximo_numero FROM config_fiscal WHERE id = 1"
            ).fetchone()
            serie = row["serie"] if row else 1
            numero = row["proximo_numero"] if row else 1
            self._conn.execute(
                "UPDATE config_fiscal SET proximo_numero = ? WHERE id = 1", (numero + 1,)
            )
            return serie, numero

    # ── Fiscal: notas ──
    def criar_nota(self, dados: dict) -> dict[str, Any]:
        cols = ("venda_id", "user_id", "ref", "modelo", "numero", "serie", "ambiente",
                "status", "chave", "protocolo", "mensagem", "xml_url", "danfe_url",
                "qrcode_url", "payload", "criado_em", "atualizado_em")
        with self._lock, self._conn:
            cur = self._conn.execute(
                f"INSERT INTO notas_fiscais ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' for _ in cols)})",
                tuple(dados.get(c) for c in cols),
            )
            return self.get_nota(cur.lastrowid)

    def get_nota(self, nota_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE id = ?", (nota_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_nota_por_ref(self, ref: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE ref = ?", (ref,)
            ).fetchone()
            return dict(row) if row else None

    def get_nota_por_venda(self, venda_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE venda_id = ? ORDER BY id DESC LIMIT 1",
                (venda_id,),
            ).fetchone()
            return dict(row) if row else None

    def atualizar_nota(self, nota_id: int, campos: dict, agora: str) -> dict[str, Any] | None:
        permitidos = {"numero", "serie", "ambiente", "status", "chave", "protocolo",
                      "mensagem", "xml_url", "danfe_url", "qrcode_url", "payload"}
        dados = {k: v for k, v in campos.items() if k in permitidos}
        if not dados:
            return self.get_nota(nota_id)
        sets = ", ".join(f"{k} = ?" for k in dados)
        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE notas_fiscais SET {sets}, atualizado_em = ? WHERE id = ?",
                list(dados.values()) + [agora, nota_id],
            )
        return self.get_nota(nota_id)

    def notas_pendentes(self, limite: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE status IN ('pendente','processando') "
                "ORDER BY id LIMIT ?", (limite,)
            ).fetchall()
            return [dict(r) for r in rows]

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
                   "estoque_minimo", "codigo_barras", "unidade", "ativo", "atualizado_em",
                   "ncm", "cest", "cfop", "origem", "unidade_tributavel", "cst_csosn",
                   "aliquota_icms", "cst_pis", "aliquota_pis", "cst_cofins", "aliquota_cofins"}
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

    def get_produto_by_codigo(self, user_id: int, codigo: str) -> dict[str, Any] | None:
        """Busca produto ativo pelo código de barras (para casar itens do XML)."""
        codigo = (codigo or "").strip()
        if not codigo:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM produtos WHERE user_id = ? AND codigo_barras = ? AND ativo = 1",
                (user_id, codigo),
            ).fetchone()
        return dict(row) if row else None

    def entrada_estoque(self, produto_id: int, user_id: int, quantidade: float,
                        agora: str, novo_custo: float | None = None) -> dict[str, Any] | None:
        """Soma quantidade ao estoque; opcionalmente atualiza o preço de custo."""
        with self._lock, self._conn:
            sets = "estoque = estoque + ?, atualizado_em = ?"
            vals: list = [quantidade, agora]
            if novo_custo is not None:
                sets += ", preco_custo = ?"
                vals.append(novo_custo)
            vals += [produto_id, user_id]
            self._conn.execute(
                f"UPDATE produtos SET {sets} WHERE id = ? AND user_id = ?", vals
            )
        return self.get_produto(produto_id, user_id)

    def registrar_movimentacao(self, user_id: int, produto_id: int, tipo: str,
                               quantidade: float, agora: str,
                               custo_unitario: float | None = None,
                               origem: str = "manual", documento: str = "",
                               observacao: str = "") -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO movimentacoes_estoque (user_id, produto_id, tipo, quantidade, "
                "custo_unitario, origem, documento, observacao, criado_em) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, produto_id, tipo, quantidade, custo_unitario, origem,
                 documento, observacao, agora),
            )

    def list_movimentacoes(self, user_id: int, produto_id: int | None = None,
                          limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            q = ("SELECT m.*, p.nome AS produto_nome FROM movimentacoes_estoque m "
                 "LEFT JOIN produtos p ON p.id = m.produto_id WHERE m.user_id = ?")
            params: list = [user_id]
            if produto_id is not None:
                q += " AND m.produto_id = ?"
                params.append(produto_id)
            q += " ORDER BY m.id DESC LIMIT ?"
            params.append(limit)
            rows = self._conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    # ── Caixa (abertura/fechamento) ──
    def get_caixa_aberto(self, user_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM caixa_sessoes WHERE user_id = ? AND fechado_em IS NULL "
                "ORDER BY id DESC LIMIT 1", (user_id,)
            ).fetchone()
        return dict(row) if row else None

    def abrir_caixa(self, user_id: int, valor_abertura: float, agora: str) -> dict[str, Any]:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO caixa_sessoes (user_id, valor_abertura, aberto_em, criado_em) "
                "VALUES (?,?,?,?)", (user_id, valor_abertura, agora, agora),
            )
            row = self._conn.execute(
                "SELECT * FROM caixa_sessoes WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        return dict(row)

    def registrar_movimento_caixa(self, sessao_id: int, user_id: int, tipo: str,
                                  valor: float, motivo: str, agora: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO caixa_movimentos (sessao_id, user_id, tipo, valor, motivo, criado_em) "
                "VALUES (?,?,?,?,?,?)", (sessao_id, user_id, tipo, valor, motivo, agora),
            )

    def resumo_caixa(self, sessao: dict) -> dict[str, Any]:
        """Totais da sessão: vendas por forma de pagamento, sangrias/suprimentos
        e dinheiro esperado em caixa."""
        user_id = sessao["user_id"]
        ini = sessao["aberto_em"]
        fim = sessao.get("fechado_em")
        with self._lock:
            if fim:
                vrows = self._conn.execute(
                    "SELECT forma_pagamento, COUNT(*) qtd, COALESCE(SUM(total),0) total "
                    "FROM vendas WHERE user_id = ? AND status = 'concluida' "
                    "AND criado_em >= ? AND criado_em <= ? GROUP BY forma_pagamento",
                    (user_id, ini, fim),
                ).fetchall()
            else:
                vrows = self._conn.execute(
                    "SELECT forma_pagamento, COUNT(*) qtd, COALESCE(SUM(total),0) total "
                    "FROM vendas WHERE user_id = ? AND status = 'concluida' "
                    "AND criado_em >= ? GROUP BY forma_pagamento", (user_id, ini),
                ).fetchall()
            mrows = self._conn.execute(
                "SELECT tipo, COALESCE(SUM(valor),0) total, COUNT(*) qtd "
                "FROM caixa_movimentos WHERE sessao_id = ? GROUP BY tipo",
                (sessao["id"],),
            ).fetchall()

        por_forma = {r["forma_pagamento"]: {"qtd": r["qtd"], "total": r["total"]} for r in vrows}
        vendas_total = sum(v["total"] for v in por_forma.values())
        vendas_qtd = sum(v["qtd"] for v in por_forma.values())
        dinheiro = por_forma.get("dinheiro", {}).get("total", 0.0)
        mov = {r["tipo"]: r["total"] for r in mrows}
        suprimentos = mov.get("suprimento", 0.0)
        sangrias = mov.get("sangria", 0.0)
        esperado = sessao["valor_abertura"] + dinheiro + suprimentos - sangrias
        return {
            "vendas_qtd": vendas_qtd,
            "vendas_total": round(vendas_total, 2),
            "por_forma": por_forma,
            "vendas_dinheiro": round(dinheiro, 2),
            "suprimentos": round(suprimentos, 2),
            "sangrias": round(sangrias, 2),
            "valor_abertura": round(sessao["valor_abertura"], 2),
            "dinheiro_esperado": round(esperado, 2),
        }

    def fechar_caixa(self, sessao_id: int, valor_fechamento: float, esperado: float,
                    agora: str, observacao: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE caixa_sessoes SET fechado_em = ?, valor_fechamento = ?, "
                "valor_esperado = ?, diferenca = ?, observacao = ? WHERE id = ?",
                (agora, valor_fechamento, esperado, round(valor_fechamento - esperado, 2),
                 observacao, sessao_id),
            )
            row = self._conn.execute(
                "SELECT * FROM caixa_sessoes WHERE id = ?", (sessao_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_caixa_historico(self, user_id: int, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM caixa_sessoes WHERE user_id = ? AND fechado_em IS NOT NULL "
                "ORDER BY id DESC LIMIT ?", (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

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

    # ── Backup / restauração ──
    def caminho_db(self) -> str:
        return str(DB_PATH)

    def backup_para(self, destino) -> None:
        """Cópia consistente do banco (usa a API de backup do SQLite, segura
        mesmo com o servidor em uso)."""
        with self._lock:
            dest = sqlite3.connect(str(destino))
            try:
                self._conn.backup(dest)
            finally:
                dest.close()

    def reconectar(self) -> None:
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute("PRAGMA journal_mode = WAL")

    def restaurar_de(self, origem) -> None:
        """Substitui o banco atual por um arquivo de backup, após validar.

        Lança ValueError se o arquivo não for um banco válido do VendaFácil.
        """
        from pathlib import Path
        import shutil
        # Valida: precisa abrir e ter a tabela 'users'.
        try:
            teste = sqlite3.connect(str(origem))
            try:
                teste.execute("SELECT 1 FROM users LIMIT 1")
            finally:
                teste.close()
        except sqlite3.Error:
            raise ValueError("Arquivo inválido: não é um backup do VendaFácil.")
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            for suf in ("-wal", "-shm"):
                p = Path(str(DB_PATH) + suf)
                if p.exists():
                    p.unlink()
            shutil.copyfile(str(origem), str(DB_PATH))
            self.reconectar()


# Singleton
db = Database()
