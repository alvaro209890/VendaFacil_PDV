import sqlite3
import tempfile
import threading
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from paths import DATA_DIR
from dinheiro import decimal, moeda, somar


class _SomaDinheiro:
    """Agregado SQLite: soma decimal sem drift intermediário de REAL."""
    def __init__(self):
        self.total = decimal(0)

    def step(self, valor):
        if valor is not None:
            self.total += decimal(valor)

    def finalize(self):
        return moeda(self.total)

class EstoqueConcorrente(ValueError):
    """O estoque mudou ou uma baixa foi recusada dentro da transação."""


class NotaEntradaDuplicada(ValueError):
    """A chave já foi confirmada para este usuário."""


DB_DIR = DATA_DIR
DB_PATH = DB_DIR / "vendafacil.db"


def abrir_sqlite_leitura(caminho: Path, *, check_same_thread: bool = True) -> sqlite3.Connection:
    return sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True,
                           check_same_thread=check_same_thread)


def verificar_integridade(caminho: Path) -> None:
    """Abre sem criar arquivo e exige que o SQLite consiga ler todo o banco."""
    try:
        with closing(abrir_sqlite_leitura(caminho)) as conn:
            if conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]:
                return
    except sqlite3.Error:
        pass
    raise ValueError("O banco não passou na verificação de integridade.")


class Database:
    def __init__(self, caminho: Path | None = None, *, somente_leitura: bool = False) -> None:
        self._lock = threading.RLock()
        self._caminho = caminho if caminho is not None else DB_PATH
        self.arquivo_principal = self._caminho
        self.modo_consulta = somente_leitura
        self.backup_recuperacao: Path | None = None
        if somente_leitura:
            self._conn = abrir_sqlite_leitura(self._caminho, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.create_aggregate("SOMA_DINHEIRO", 1, _SomaDinheiro)
            self._conn.execute("PRAGMA query_only = ON")
            return
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        self.reconectar()
        try:
            self._init_schema()
        except Exception:
            self.close()
            raise

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
                    estoque REAL NOT NULL DEFAULT 0,
                    estoque_minimo REAL NOT NULL DEFAULT 5,
                    codigo_barras TEXT DEFAULT '',
                    unidade TEXT NOT NULL DEFAULT 'UN',
                    unidade_compra TEXT NOT NULL DEFAULT '',
                    quantidade_por_embalagem REAL NOT NULL DEFAULT 1,
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
                documento TEXT DEFAULT '',
                inscricao_estadual TEXT DEFAULT '',
                indicador_ie TEXT DEFAULT '9',
                logradouro TEXT DEFAULT '',
                numero TEXT DEFAULT '',
                bairro TEXT DEFAULT '',
                municipio TEXT DEFAULT '',
                codigo_municipio TEXT DEFAULT '',
                uf TEXT DEFAULT '',
                cep TEXT DEFAULT '',
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
        for col in ("cancelada_em", "motivo_cancelamento", "sincronizado_em"):
            if col not in cols:
                self._conn.execute(f"ALTER TABLE vendas ADD COLUMN {col} TEXT")
        if "sincronizado" not in cols:
            self._conn.execute(
                "ALTER TABLE vendas ADD COLUMN sincronizado INTEGER NOT NULL DEFAULT 0"
            )
        if "uuid" not in cols:
            self._conn.execute("ALTER TABLE vendas ADD COLUMN uuid TEXT")
        if "pagamento_detalhe" not in cols:
            # JSON com o vínculo do pagamento eletrônico (cartão/PIX integrado):
            # tipo_integracao, adquirente_cnpj, bandeira, autorizacao (cAut), etc.
            self._conn.execute("ALTER TABLE vendas ADD COLUMN pagamento_detalhe TEXT")
        if "sessao_id" not in cols:
            self._conn.execute("ALTER TABLE vendas ADD COLUMN sessao_id INTEGER")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS pagamentos_fiado ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, conta_id INTEGER NOT NULL, "
            "valor REAL NOT NULL, forma TEXT NOT NULL DEFAULT 'dinheiro', "
            "criado_em TEXT NOT NULL)"
        )
        pfiado = {r["name"] for r in self._conn.execute("PRAGMA table_info(pagamentos_fiado)")}
        if "sessao_id" not in pfiado:
            self._conn.execute("ALTER TABLE pagamentos_fiado ADD COLUMN sessao_id INTEGER")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS notas_entrada ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, chave TEXT NOT NULL, "
            "documento TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL, "
            "UNIQUE(user_id, chave))"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cobrancas_maquininha ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, order_id TEXT NOT NULL, "
            "payment_id TEXT NOT NULL, valor REAL NOT NULL DEFAULT 0, "
            "forma TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, "
            "venda_id INTEGER, comprovante TEXT NOT NULL DEFAULT '', "
            "criado_em TEXT NOT NULL, UNIQUE(user_id, payment_id))"
        )

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

        # Campos de embalagem/conversao. O estoque sempre fica na unidade de
        # venda (unidade); entradas por XML/manual podem vir em caixa/fardo/etc.
        pcols = {r["name"] for r in self._conn.execute("PRAGMA table_info(produtos)")}
        embalagem = {
            "unidade_compra": "TEXT NOT NULL DEFAULT ''",
            "quantidade_por_embalagem": "REAL NOT NULL DEFAULT 1",
            "vende_por_unidade": "INTEGER NOT NULL DEFAULT 0",
            "preco_embalagem": "REAL NOT NULL DEFAULT 0",
            "preco_unidade": "REAL NOT NULL DEFAULT 0",
            "codigo_barras_unidade": "TEXT NOT NULL DEFAULT ''",
        }
        for col, ddl in embalagem.items():
            if col not in pcols:
                self._conn.execute(f"ALTER TABLE produtos ADD COLUMN {col} {ddl}")

        ccols = {r["name"] for r in self._conn.execute("PRAGMA table_info(clientes)")}
        icols = {r["name"] for r in self._conn.execute("PRAGMA table_info(itens_venda)")}
        for col, ddl in {"modo_venda": "TEXT", "unidade_venda": "TEXT",
                         "quantidade_estoque": "REAL", "custo_unitario_estoque": "REAL"}.items():
            if col not in icols:
                self._conn.execute(f"ALTER TABLE itens_venda ADD COLUMN {col} {ddl}")
        cliente_fiscal = {
            "documento": "TEXT DEFAULT ''",
            "inscricao_estadual": "TEXT DEFAULT ''",
            "indicador_ie": "TEXT DEFAULT '9'",
            "logradouro": "TEXT DEFAULT ''",
            "numero": "TEXT DEFAULT ''",
            "bairro": "TEXT DEFAULT ''",
            "municipio": "TEXT DEFAULT ''",
            "codigo_municipio": "TEXT DEFAULT ''",
            "uf": "TEXT DEFAULT ''",
            "cep": "TEXT DEFAULT ''",
        }
        for col, ddl in cliente_fiscal.items():
            if col not in ccols:
                self._conn.execute(f"ALTER TABLE clientes ADD COLUMN {col} {ddl}")

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
                provedor_fiscal TEXT DEFAULT 'sefaz_mt_direto',
                gateway_token TEXT DEFAULT '',
                certificado_a1_b64 TEXT DEFAULT '',
                certificado_senha TEXT DEFAULT '',
                certificado_nome TEXT DEFAULT '',
                certificado_validade TEXT DEFAULT '',
                serie INTEGER NOT NULL DEFAULT 1,
                proximo_numero INTEGER NOT NULL DEFAULT 1,
                serie_nfce INTEGER NOT NULL DEFAULT 1,
                proximo_numero_nfce INTEGER NOT NULL DEFAULT 1,
                serie_nfe INTEGER NOT NULL DEFAULT 1,
                proximo_numero_nfe INTEGER NOT NULL DEFAULT 1,
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
                xml_assinado TEXT,
                xml_autorizado TEXT,
                tipo_emissao TEXT DEFAULT '1',
                recibo TEXT,
                motivo_rejeicao TEXT,
                destinatario_snapshot TEXT,
                autorizado_em TEXT,
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
                adquirente_cnpj TEXT DEFAULT '',
                pix_integrado INTEGER NOT NULL DEFAULT 0,
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

            CREATE TABLE IF NOT EXISTS config_loja (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                pix_chave TEXT DEFAULT '',
                pix_nome TEXT DEFAULT '',
                pix_cidade TEXT DEFAULT '',
                atualizado_em TEXT
            );
            """
        )

        fcols = {r["name"] for r in self._conn.execute("PRAGMA table_info(config_fiscal)")}
        fiscal_cols = {
            "cnae": "TEXT DEFAULT ''",
            "provedor_fiscal": "TEXT DEFAULT 'sefaz_mt_direto'",
            "certificado_a1_b64": "TEXT DEFAULT ''",
            "certificado_senha": "TEXT DEFAULT ''",
            "certificado_nome": "TEXT DEFAULT ''",
            "certificado_validade": "TEXT DEFAULT ''",
            "serie_nfce": "INTEGER NOT NULL DEFAULT 1",
            "proximo_numero_nfce": "INTEGER NOT NULL DEFAULT 1",
            "serie_nfe": "INTEGER NOT NULL DEFAULT 1",
            "proximo_numero_nfe": "INTEGER NOT NULL DEFAULT 1",
            # Responsável Técnico (infRespTec) — desligado por padrão. MT não exige
            # hoje; ligar só se/quando a UF passar a exigir. Ver docs/RESPONSAVEL_TECNICO.md
            "resp_tec_habilitado": "INTEGER NOT NULL DEFAULT 0",
            "resp_tec_cnpj": "TEXT DEFAULT ''",
            "resp_tec_contato": "TEXT DEFAULT ''",
            "resp_tec_email": "TEXT DEFAULT ''",
            "resp_tec_fone": "TEXT DEFAULT ''",
            "resp_tec_csrt": "TEXT DEFAULT ''",
            "resp_tec_id_csrt": "TEXT DEFAULT ''",
            # Versão do QR Code da NFC-e: 2 (padrão, com CSC) ou 3 (NT 2025.001,
            # assinatura digital, sem CSC). MT aceita a 2.0 em produção.
            "qrcode_versao": "TEXT DEFAULT '2'",
            # Percentual aproximado dos tributos (tabela IBPT) p/ Lei 12.741/2012;
            # 0 = não informar valor (mantém só a referência ao IBPT no cupom).
            "ibpt_percentual": "REAL DEFAULT 0",
        }
        for col, ddl in fiscal_cols.items():
            if col not in fcols:
                self._conn.execute(f"ALTER TABLE config_fiscal ADD COLUMN {col} {ddl}")

        mcols = {r["name"] for r in self._conn.execute("PRAGMA table_info(config_maquininha)")}
        if "adquirente_cnpj" not in mcols:
            # CNPJ da credenciadora (Mercado Pago) p/ o grupo <card> da NFC-e.
            self._conn.execute("ALTER TABLE config_maquininha ADD COLUMN adquirente_cnpj TEXT DEFAULT ''")
        if "pix_integrado" not in mcols:
            # Cobrar PIX pela Point (transação integrada, com endToEndId p/ a NFC-e).
            self._conn.execute("ALTER TABLE config_maquininha ADD COLUMN pix_integrado INTEGER NOT NULL DEFAULT 0")

        ncols = {r["name"] for r in self._conn.execute("PRAGMA table_info(notas_fiscais)")}
        nota_cols = {
            "xml_assinado": "TEXT",
            "xml_autorizado": "TEXT",
            "tipo_emissao": "TEXT DEFAULT '1'",
            "recibo": "TEXT",
            "motivo_rejeicao": "TEXT",
            "destinatario_snapshot": "TEXT",
            "autorizado_em": "TEXT",
        }
        for col, ddl in nota_cols.items():
            if col not in ncols:
                self._conn.execute(f"ALTER TABLE notas_fiscais ADD COLUMN {col} {ddl}")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS inutilizacoes_fiscais (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            cnpj TEXT NOT NULL, modelo TEXT NOT NULL, ambiente TEXT NOT NULL,
            ano INTEGER NOT NULL, serie INTEGER NOT NULL, inicio INTEGER NOT NULL,
            fim INTEGER NOT NULL, justificativa TEXT NOT NULL, status TEXT NOT NULL,
            cstat TEXT, protocolo TEXT, mensagem TEXT, xml_pedido TEXT, xml_retorno TEXT,
            criado_em TEXT NOT NULL, atualizado_em TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id))""")

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
                f"UPDATE vendas SET sincronizado = 1, sincronizado_em = ? WHERE id IN ({marcas})",
                [datetime.now(timezone.utc).isoformat(), *ids],
            )

    def contagens_diagnostico(self, user_id: int) -> tuple[int, int, str | None]:
        with self._lock:
            pendentes, contingencia = self._conn.execute(
                "SELECT COUNT(CASE WHEN status IN ('pendente','processando') THEN 1 END), "
                "COUNT(CASE WHEN status = 'contingencia' THEN 1 END) "
                "FROM notas_fiscais WHERE user_id = ?", (user_id,)
            ).fetchone()
            ultima = self._conn.execute(
                "SELECT MAX(sincronizado_em) FROM vendas WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            return pendentes, contingencia, ultima

    # ── Fiscal: configuração do emitente ──
    def get_config_fiscal(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM config_fiscal WHERE id = 1").fetchone()
            if not row:
                return {"habilitado": 0, "ambiente": "homologacao",
                        "gateway": "focusnfe", "provedor_fiscal": "sefaz_mt_direto",
                        "serie": 1, "proximo_numero": 1,
                        "serie_nfce": 1, "proximo_numero_nfce": 1,
                        "serie_nfe": 1, "proximo_numero_nfe": 1}
            return dict(row)

    def salvar_config_fiscal(self, campos: dict, agora: str) -> dict[str, Any]:
        permitidos = {
            "habilitado", "razao_social", "nome_fantasia", "cnpj", "inscricao_estadual",
            "cnae",
            "regime_tributario", "logradouro", "numero", "bairro", "municipio",
            "codigo_municipio", "uf", "cep", "csc", "csc_id", "ambiente", "gateway",
            "provedor_fiscal", "gateway_token", "certificado_a1_b64", "certificado_senha",
            "certificado_nome", "certificado_validade", "serie", "proximo_numero",
            "serie_nfce", "proximo_numero_nfce", "serie_nfe", "proximo_numero_nfe",
            "resp_tec_habilitado", "resp_tec_cnpj", "resp_tec_contato",
            "resp_tec_email", "resp_tec_fone", "resp_tec_csrt", "resp_tec_id_csrt",
            "qrcode_versao", "ibpt_percentual",
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
                        "imprimir_comprovante": 1, "adquirente_cnpj": ""}
            return dict(row)

    def salvar_config_maquininha(self, campos: dict, agora: str) -> dict[str, Any]:
        permitidos = {
            "habilitado", "provedor", "access_token", "device_id",
            "store_id", "pos_id", "imprimir_comprovante", "adquirente_cnpj",
            "pix_integrado",
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

    # ── Config da loja (PIX) ──
    def get_config_loja(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM config_loja WHERE id = 1").fetchone()
            return dict(row) if row else {"pix_chave": "", "pix_nome": "", "pix_cidade": ""}

    def salvar_config_loja(self, campos: dict, agora: str) -> dict[str, Any]:
        permitidos = {"pix_chave", "pix_nome", "pix_cidade"}
        dados = {k: v for k, v in campos.items() if k in permitidos and v is not None}
        with self._lock, self._conn:
            if not self._conn.execute("SELECT 1 FROM config_loja WHERE id = 1").fetchone():
                self._conn.execute("INSERT INTO config_loja (id) VALUES (1)")
            if dados:
                sets = ", ".join(f"{k} = ?" for k in dados)
                self._conn.execute(
                    f"UPDATE config_loja SET {sets}, atualizado_em = ? WHERE id = 1",
                    list(dados.values()) + [agora],
                )
        return self.get_config_loja()

    def consumir_numero_fiscal(self, modelo: str = "65") -> tuple[int, int]:
        """Reserva o próximo número/série por modelo fiscal."""
        serie_col, numero_col = (
            ("serie_nfe", "proximo_numero_nfe") if str(modelo) == "55"
            else ("serie_nfce", "proximo_numero_nfce")
        )
        with self._lock, self._conn:
            row = self._conn.execute(
                f"SELECT {serie_col} AS serie, {numero_col} AS proximo_numero FROM config_fiscal WHERE id = 1"
            ).fetchone()
            serie = row["serie"] if row else 1
            numero = row["proximo_numero"] if row else 1
            self._conn.execute(
                f"UPDATE config_fiscal SET {numero_col} = ? WHERE id = 1", (numero + 1,)
            )
            return serie, numero

    def consumir_numero_nfce(self) -> tuple[int, int]:
        """Reserva o próximo número/série de NFC-e de forma atômica."""
        return self.consumir_numero_fiscal("65")

    def reservar_nota_fiscal(self, venda_id: int, user_id: int, modelo: str,
                             ambiente: str | None, agora: str) -> tuple[dict[str, Any], bool]:
        """Grava a nota como processando antes de qualquer transmissão.

        A inserção e a numeração compartilham a mesma transação e revalidam a
        venda. Outra conexão que cancele durante a rede já encontra esta linha.
        """
        modelo = "55" if str(modelo) == "55" else "65"
        with self._lock, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            venda = self._conn.execute(
                "SELECT status FROM vendas WHERE id = ? AND user_id = ?",
                (venda_id, user_id),
            ).fetchone()
            if not venda:
                raise ValueError("Venda não encontrada.")
            if venda["status"] != "concluida":
                raise ValueError("Venda cancelada ou não concluída; emissão fiscal não permitida.")
            existente = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE venda_id = ? AND modelo = ? "
                "AND status IN ('autorizada','pendente','processando','contingencia') "
                "ORDER BY id DESC LIMIT 1",
                (venda_id, modelo),
            ).fetchone()
            if existente:
                return dict(existente), False
            # Reserva que nunca chegou à SEFAZ (falha local de assinatura/montagem
            # antes de transmitir) não tem chave. Ela é retomada com o MESMO
            # número: consumir outro abriria buraco de numeração que só se
            # resolve com inutilização na SEFAZ (P35).
            falha_local = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE venda_id = ? AND modelo = ? "
                "AND status = 'rejeitada' AND (chave IS NULL OR chave = '') "
                "AND NOT EXISTS (SELECT 1 FROM inutilizacoes_fiscais i WHERE i.modelo=notas_fiscais.modelo "
                "AND i.serie=notas_fiscais.serie AND i.ambiente=notas_fiscais.ambiente "
                "AND notas_fiscais.numero BETWEEN i.inicio AND i.fim "
                "AND i.status IN ('processando','inutilizada')) "
                "ORDER BY id DESC LIMIT 1",
                (venda_id, modelo),
            ).fetchone()
            if falha_local:
                self._conn.execute(
                    "UPDATE notas_fiscais SET status = 'processando', mensagem = ?, "
                    "motivo_rejeicao = NULL, atualizado_em = ? WHERE id = ?",
                    ("Retomando o mesmo número reservado; a tentativa anterior "
                     "falhou antes de transmitir.", agora, falha_local["id"]),
                )
                retomada = self._conn.execute(
                    "SELECT * FROM notas_fiscais WHERE id = ?", (falha_local["id"],)
                ).fetchone()
                return dict(retomada), True
            if modelo == "55":
                row = self._conn.execute(
                    "SELECT serie_nfe AS serie, proximo_numero_nfe AS proximo "
                    "FROM config_fiscal WHERE id = 1"
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT serie_nfce AS serie, proximo_numero_nfce AS proximo "
                    "FROM config_fiscal WHERE id = 1"
                ).fetchone()
            if not row:
                # Sem a linha de configuração não há numeração confiável: série e
                # número cairiam sempre em 1 e a primeira nota de cada venda
                # repetiria a chave de acesso (P35).
                raise ValueError(
                    "Configuração fiscal do emitente não cadastrada; salve as "
                    "Configurações Fiscais antes de emitir.")
            serie = int(row["serie"] or 1)
            numero = int(row["proximo"] or 1)
            ocupado = self._conn.execute(
                "SELECT 1 FROM inutilizacoes_fiscais WHERE modelo=? AND serie=? AND ambiente=? "
                "AND ? BETWEEN inicio AND fim AND status IN ('processando','inutilizada') LIMIT 1",
                (modelo, serie, ambiente or "homologacao", numero)).fetchone()
            if ocupado:
                raise ValueError("Número reservado para inutilização; confira a numeração fiscal com o contador.")
            if modelo == "55":
                self._conn.execute(
                    "UPDATE config_fiscal SET proximo_numero_nfe = ? WHERE id = 1",
                    (numero + 1,),
                )
            else:
                self._conn.execute(
                    "UPDATE config_fiscal SET proximo_numero_nfce = ? WHERE id = 1",
                    (numero + 1,),
                )
            cur = self._conn.execute(
                "INSERT INTO notas_fiscais (venda_id, user_id, ref, modelo, numero, serie, "
                "ambiente, status, tipo_emissao, mensagem, criado_em, atualizado_em) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'processando', '1', ?, ?, ?)",
                (venda_id, user_id, f"v{venda_id}-{modelo}-{numero}", modelo, numero, serie,
                 ambiente or "homologacao",
                 "Transmissão em andamento; resolva o documento fiscal antes de cancelar a venda.",
                 agora, agora),
            )
            criada = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return dict(criada), True

    def reservar_inutilizacao(self, user_id: int, cnpj: str, pedido: dict, agora: str) -> tuple[dict, bool]:
        """Reserva faixa antes da rede; emissões concorrentes respeitam a reserva."""
        modelo, serie = pedido["modelo"], pedido["serie"]
        ambiente = pedido["ambiente"]
        inicio, fim, ano = pedido["inicio"], pedido["fim"], pedido["ano"]
        with self._lock, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            existente = self._conn.execute(
                "SELECT * FROM inutilizacoes_fiscais WHERE cnpj=? AND modelo=? AND ambiente=? "
                "AND ano=? AND serie=? AND inicio=? AND fim=? "
                "AND status IN ('processando','inutilizada') ORDER BY id DESC LIMIT 1",
                (cnpj, modelo, ambiente, ano, serie, inicio, fim)).fetchone()
            if existente:
                if existente["user_id"] != user_id:
                    raise ValueError("Faixa já solicitada por outro operador; consulte o responsável fiscal.")
                return dict(existente), False
            ativa = self._conn.execute(
                "SELECT 1 FROM notas_fiscais WHERE modelo=? AND serie=? AND ambiente=? "
                "AND numero BETWEEN ? AND ? AND (status<>'rejeitada' OR tipo_emissao='9') LIMIT 1",
                (modelo, serie, ambiente, inicio, fim)).fetchone()
            sobreposta = self._conn.execute(
                "SELECT 1 FROM inutilizacoes_fiscais WHERE cnpj=? AND modelo=? AND ambiente=? "
                "AND serie=? AND inicio<=? AND fim>=? AND status IN ('processando','inutilizada') LIMIT 1",
                (cnpj, modelo, ambiente, serie, fim, inicio)).fetchone()
            if ativa or sobreposta:
                raise ValueError("Faixa contém nota ativa, contingência ou pedido de inutilização em andamento.")
            cfg = self.get_config_fiscal()
            sufixo = "nfe" if modelo == "55" else "nfce"
            if serie == cfg.get("serie_" + sufixo, 1):
                proximo = int(cfg.get("proximo_numero_" + sufixo) or 1)
            else:
                proximo = self._conn.execute(
                    "SELECT COALESCE(MAX(numero),0)+1 FROM notas_fiscais WHERE modelo=? AND serie=? AND ambiente=?",
                    (modelo, serie, ambiente)).fetchone()[0]
            if fim >= proximo:
                raise ValueError("Não é permitido inutilizar numeração futura; informe uma quebra de sequência existente.")
            cur = self._conn.execute(
                "INSERT INTO inutilizacoes_fiscais (user_id,cnpj,modelo,ambiente,ano,serie,inicio,fim,"
                "justificativa,status,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?,'processando',?,?)",
                (user_id, cnpj, modelo, ambiente, ano, serie, inicio, fim, pedido["justificativa"], agora, agora))
            return dict(self._conn.execute("SELECT * FROM inutilizacoes_fiscais WHERE id=?", (cur.lastrowid,)).fetchone()), True

    def concluir_inutilizacao(self, ident: int, resultado: dict, agora: str) -> dict:
        campos = {k: resultado.get(k) for k in ("status", "cstat", "protocolo", "mensagem", "xml_pedido", "xml_retorno")}
        with self._lock, self._conn:
            self._conn.execute("UPDATE inutilizacoes_fiscais SET " + ",".join(k + "=?" for k in campos)
                               + ",atualizado_em=? WHERE id=?", [*campos.values(), agora, ident])
            return dict(self._conn.execute("SELECT * FROM inutilizacoes_fiscais WHERE id=?", (ident,)).fetchone())

    def listar_inutilizacoes(self, user_id: int) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(
                "SELECT * FROM inutilizacoes_fiscais WHERE user_id=? ORDER BY id DESC LIMIT 100", (user_id,))]

    # ── Fiscal: notas ──
    def criar_nota(self, dados: dict) -> dict[str, Any]:
        cols = ("venda_id", "user_id", "ref", "modelo", "numero", "serie", "ambiente",
                "status", "chave", "protocolo", "mensagem", "xml_url", "danfe_url",
                "qrcode_url", "payload", "xml_assinado", "xml_autorizado", "tipo_emissao",
                "recibo", "motivo_rejeicao", "destinatario_snapshot", "autorizado_em",
                "criado_em", "atualizado_em")
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

    def get_nota_por_venda(self, venda_id: int, modelo: str | None = None) -> dict[str, Any] | None:
        with self._lock:
            if modelo:
                row = self._conn.execute(
                    "SELECT * FROM notas_fiscais WHERE venda_id = ? AND modelo = ? ORDER BY id DESC LIMIT 1",
                    (venda_id, str(modelo)),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT * FROM notas_fiscais WHERE venda_id = ? ORDER BY id DESC LIMIT 1",
                    (venda_id,),
                ).fetchone()
            return dict(row) if row else None

    def atualizar_nota(self, nota_id: int, campos: dict, agora: str) -> dict[str, Any] | None:
        permitidos = {"numero", "serie", "ambiente", "status", "chave", "protocolo",
                      "mensagem", "xml_url", "danfe_url", "qrcode_url", "payload",
                      "xml_assinado", "xml_autorizado", "tipo_emissao", "recibo",
                      "motivo_rejeicao", "destinatario_snapshot", "autorizado_em"}
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

    def notas_para_export(self, user_id: int, inicio: str | None = None,
                          fim: str | None = None) -> list[dict[str, Any]]:
        """Notas com XML (autorizadas/canceladas) do período, p/ entregar ao contador."""
        q = ("SELECT id, modelo, numero, serie, chave, status, criado_em, "
             "xml_autorizado, xml_assinado FROM notas_fiscais "
             "WHERE user_id = ? AND status IN ('autorizada','cancelada')")
        params: list = [user_id]
        if inicio and fim:
            q += " AND date(criado_em, 'localtime') BETWEEN ? AND ?"
            params += [inicio, fim]
        elif inicio:
            q += " AND date(criado_em, 'localtime') >= ?"
            params.append(inicio)
        elif fim:
            q += " AND date(criado_em, 'localtime') <= ?"
            params.append(fim)
        q += " ORDER BY criado_em"
        with self._lock:
            rows = self._conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]

    def notas_pendentes(self, limite: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notas_fiscais WHERE status IN ('pendente','processando','contingencia') "
                "ORDER BY id LIMIT ?", (limite,)
            ).fetchall()
            return [dict(r) for r in rows]

    def tem_usuario(self) -> bool:
        with self._lock:
            return self._conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None

    def create_user(self, usuario: str, nome: str, senha_hash: str, criado_em: str) -> dict[str, Any] | None:
        login = usuario.strip().lower()
        with self._lock, self._conn:
            try:
                cursor = self._conn.execute(
                    "INSERT INTO users (email, nome, senha_hash, criado_em) VALUES (?, ?, ?, ?)",
                    (login, nome.strip(), senha_hash, criado_em),
                )
                return {"id": cursor.lastrowid, "usuario": login, "email": login, "nome": nome.strip()}
            except sqlite3.IntegrityError:
                return None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.get_user_by_usuario(email)

    def get_user_by_usuario(self, usuario: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, email AS usuario, email, nome, senha_hash FROM users WHERE email = ?",
                (usuario.strip().lower(),),
            ).fetchone()
        return dict(row) if row else None

    def update_last_login(self, usuario: str, timestamp: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET ultimo_login = ? WHERE email = ?",
                (timestamp, usuario.strip().lower()),
            )

    def update_password(self, email: str, senha_hash: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE users SET senha_hash = ? WHERE email = ?",
                (senha_hash, email.strip().lower()),
            )
        return cursor.rowcount > 0

    def upsert_user(self, usuario: str, nome: str, senha_hash: str, agora: str) -> dict[str, Any]:
        login = usuario.strip().lower()
        user = self.get_user_by_usuario(login)
        with self._lock, self._conn:
            if user:
                self._conn.execute(
                    "UPDATE users SET nome = ?, senha_hash = ? WHERE email = ?",
                    (nome.strip() or user["nome"], senha_hash, login),
                )
                return self.get_user_by_usuario(login) or user
            cursor = self._conn.execute(
                "INSERT INTO users (email, nome, senha_hash, criado_em) VALUES (?, ?, ?, ?)",
                (login, nome.strip() or login, senha_hash, agora),
            )
            return {"id": cursor.lastrowid, "usuario": login, "email": login, "nome": nome.strip() or login}

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
                       preco_venda: float, estoque: float, estoque_minimo: float,
                       codigo_barras: str, unidade: str, agora: str,
                       categoria_id: int | None = None,
                       unidade_compra: str = "",
                       quantidade_por_embalagem: float = 1,
                       vende_por_unidade: bool = False, preco_embalagem: float = 0,
                       preco_unidade: float = 0, codigo_barras_unidade: str = "",
                       fiscais: dict | None = None) -> dict[str, Any] | None:
        cols = ["user_id", "categoria_id", "nome", "preco_custo", "preco_venda", "estoque",
                "estoque_minimo", "codigo_barras", "unidade", "unidade_compra",
                "quantidade_por_embalagem", "criado_em", "atualizado_em"]
        vals = [user_id, categoria_id, nome.strip(), preco_custo, preco_venda, estoque,
                estoque_minimo, codigo_barras.strip(), unidade.strip().upper(),
                (unidade_compra or unidade).strip().upper(),
                max(float(quantidade_por_embalagem or 1), 0.0001), agora, agora]
        cols += ["vende_por_unidade", "preco_embalagem", "preco_unidade", "codigo_barras_unidade"]
        vals += [int(vende_por_unidade), preco_embalagem, preco_unidade, codigo_barras_unidade.strip()]
        permitidos = {"ncm", "cest", "cfop", "origem", "unidade_tributavel", "cst_csosn",
                      "aliquota_icms", "cst_pis", "aliquota_pis", "cst_cofins", "aliquota_cofins"}
        for chave, valor in (fiscais or {}).items():
            if chave in permitidos and valor is not None:
                cols.append(chave)
                vals.append(valor)
        with self._lock, self._conn:
            cursor = self._conn.execute(
                f"INSERT INTO produtos ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                vals,
            )
            return self.get_produto(cursor.lastrowid)

    def update_produto(self, produto_id: int, user_id: int, **kwargs) -> dict[str, Any] | None:
        allowed = {"nome", "categoria_id", "preco_custo", "preco_venda", "estoque",
                   "estoque_minimo", "codigo_barras", "unidade", "ativo", "atualizado_em",
                   "unidade_compra", "quantidade_por_embalagem",
                   "vende_por_unidade", "preco_embalagem", "preco_unidade", "codigo_barras_unidade",
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

    def definir_estoque(self, produto_id: int, user_id: int, novo_estoque: float,
                        agora: str) -> dict[str, Any] | None:
        """Define o estoque para um valor absoluto (ajuste/inventário)."""
        novo = max(0.0, float(novo_estoque))
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE produtos SET estoque = ?, atualizado_em = ? WHERE id = ? AND user_id = ?",
                (novo, agora, produto_id, user_id),
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

    def nota_entrada_importada(self, user_id: int, chave: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM notas_entrada WHERE user_id = ? AND chave = ?",
                (user_id, chave),
            ).fetchone()
        return row is not None

    def registrar_nota_entrada(self, user_id: int, chave: str, documento: str, agora: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO notas_entrada (user_id, chave, documento, criado_em) VALUES (?, ?, ?, ?)",
                (user_id, chave, documento, agora),
            )

    def importar_entrada_atomica(self, user_id: int, chave: str, documento: str,
                                 itens: list[dict], agora: str) -> dict[str, int]:
        """Produto, estoque, fiscal, movimentos e chave: todos ou nenhum."""
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                if chave:
                    if self._conn.execute(
                        "SELECT 1 FROM notas_entrada WHERE user_id = ? AND chave = ?",
                        (user_id, chave),
                    ).fetchone():
                        raise NotaEntradaDuplicada("NF-e já importada.")
                    cur = self._conn.execute(
                        "INSERT INTO notas_entrada (user_id, chave, documento, criado_em) VALUES (?,?,?,?)",
                        (user_id, chave, documento, agora),
                    )
                    if cur.rowcount != 1:
                        raise sqlite3.IntegrityError("Chave de entrada não foi gravada.")
                criados = atualizados = 0
                for it in itens:
                    pid = it.get("produto_id")
                    codigo = it.get("codigo_barras") or ""
                    if not pid and codigo:
                        existente = self._conn.execute(
                            "SELECT id FROM produtos WHERE user_id = ? AND codigo_barras = ? AND ativo = 1",
                            (user_id, codigo),
                        ).fetchone()
                        pid = existente["id"] if existente else None
                    if pid:
                        existente = self._conn.execute(
                            "SELECT id FROM produtos WHERE id = ? AND user_id = ? AND ativo = 1",
                            (pid, user_id),
                        ).fetchone()
                        if not existente:
                            raise ValueError("Produto da entrada não encontrado ou inativo.")
                        custo = it["preco_custo"] if it["atualizar_custo"] and it["preco_custo"] > 0 else None
                        cur = self._conn.execute(
                            "UPDATE produtos SET estoque = estoque + ?, preco_custo = COALESCE(?, preco_custo), "
                            "atualizado_em = ? WHERE id = ? AND user_id = ? AND ativo = 1",
                            (it["quantidade"], custo, agora, pid, user_id),
                        )
                        if cur.rowcount != 1:
                            raise sqlite3.IntegrityError("Estoque da entrada não foi atualizado.")
                        atualizados += 1
                    else:
                        cur = self._conn.execute(
                            "INSERT INTO produtos (user_id, nome, preco_custo, preco_venda, estoque, "
                            "estoque_minimo, codigo_barras, unidade, unidade_compra, quantidade_por_embalagem, "
                            "ncm, cfop, criado_em, atualizado_em) VALUES (?,?,?,?,?,5,?,?,?,?,?,?,?,?)",
                            (user_id, it["nome"].strip(), it["preco_custo"], it["preco_venda"],
                             it["quantidade"], codigo, it["unidade"], it["unidade_compra"],
                             it["quantidade_por_embalagem"], it.get("ncm") or "", it.get("cfop") or "", agora, agora),
                        )
                        if cur.rowcount != 1:
                            raise sqlite3.IntegrityError("Produto da entrada não foi criado.")
                        pid = cur.lastrowid
                        criados += 1
                    observacao = f"{it['nome']} ({it.get('quantidade_xml') or it['quantidade']} {it['unidade_compra'] or it['unidade']})"
                    cur = self._conn.execute(
                        "INSERT INTO movimentacoes_estoque (user_id, produto_id, tipo, quantidade, "
                        "custo_unitario, origem, documento, observacao, criado_em) VALUES (?,?,'entrada',?,?,'xml',?,?,?)",
                        (user_id, pid, it["quantidade"], it["preco_custo"], documento, observacao, agora),
                    )
                    if cur.rowcount != 1:
                        raise sqlite3.IntegrityError("Movimento da entrada não foi gravado.")
                self._conn.commit()
                return {"criados": criados, "atualizados": atualizados, "total": criados + atualizados}
            except Exception:
                self._conn.rollback()
                raise

    def cobranca_aprovada_sem_venda(self, user_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM cobrancas_maquininha WHERE user_id = ? AND status = 'approved' "
                "AND venda_id IS NULL ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def salvar_cobranca_aprovada(self, user_id: int, order_id: str, payment_id: str,
                                 valor: float, forma: str, comprovante: str, agora: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO cobrancas_maquininha "
                "(user_id, order_id, payment_id, valor, forma, status, comprovante, criado_em) "
                "VALUES (?, ?, ?, ?, ?, 'approved', ?, ?) "
                "ON CONFLICT(user_id, payment_id) DO UPDATE SET "
                "order_id = excluded.order_id, comprovante = excluded.comprovante "
                "WHERE cobrancas_maquininha.venda_id IS NULL",
                (user_id, order_id, payment_id, moeda(valor), forma, comprovante, agora),
            )

    def venda_da_cobranca(self, user_id: int, payment_id: str) -> int | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT venda_id FROM cobrancas_maquininha "
                "WHERE user_id = ? AND payment_id = ? AND venda_id IS NOT NULL",
                (user_id, payment_id),
            ).fetchone()
        return int(row["venda_id"]) if row else None

    def vincular_cobranca_venda(self, user_id: int, payment_id: str, venda_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE cobrancas_maquininha SET venda_id = ? "
                "WHERE user_id = ? AND payment_id = ? AND venda_id IS NULL",
                (venda_id, user_id, payment_id),
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
                "VALUES (?,?,?,?)", (user_id, moeda(valor_abertura), agora, agora),
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
                "VALUES (?,?,?,?,?,?)", (sessao_id, user_id, tipo, moeda(valor), motivo, agora),
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
                    "SELECT forma_pagamento, COUNT(*) qtd, COALESCE(SOMA_DINHEIRO(total),0) total "
                    "FROM vendas WHERE user_id = ? AND status = 'concluida' AND ("
                    "sessao_id = ? OR (sessao_id IS NULL AND criado_em >= ? AND criado_em <= ?)) "
                    "GROUP BY forma_pagamento",
                    (user_id, sessao["id"], ini, fim),
                ).fetchall()
            else:
                vrows = self._conn.execute(
                    "SELECT forma_pagamento, COUNT(*) qtd, COALESCE(SOMA_DINHEIRO(total),0) total "
                    "FROM vendas WHERE user_id = ? AND status = 'concluida' AND ("
                    "sessao_id = ? OR (sessao_id IS NULL AND criado_em >= ?)) "
                    "GROUP BY forma_pagamento",
                    (user_id, sessao["id"], ini),
                ).fetchall()
            mrows = self._conn.execute(
                "SELECT tipo, COALESCE(SOMA_DINHEIRO(valor),0) total, COUNT(*) qtd "
                "FROM caixa_movimentos WHERE sessao_id = ? GROUP BY tipo",
                (sessao["id"],),
            ).fetchall()
            recebido = self._conn.execute(
                "SELECT COALESCE(SOMA_DINHEIRO(valor),0) total FROM pagamentos_fiado "
                "WHERE user_id = ? AND sessao_id = ? AND lower(trim(forma)) = 'dinheiro'",
                (user_id, sessao["id"]),
            ).fetchone()["total"]

        por_forma = {r["forma_pagamento"]: {"qtd": r["qtd"], "total": r["total"]} for r in vrows}
        vendas_total = somar(v["total"] for v in por_forma.values())
        vendas_qtd = sum(v["qtd"] for v in por_forma.values())
        dinheiro = por_forma.get("dinheiro", {}).get("total", 0.0)
        mov = {r["tipo"]: r["total"] for r in mrows}
        suprimentos = mov.get("suprimento", 0.0)
        sangrias = mov.get("sangria", 0.0)
        esperado = somar([sessao["valor_abertura"], dinheiro, suprimentos, recebido]) - decimal(sangrias)
        return {
            "vendas_qtd": vendas_qtd,
            "vendas_total": moeda(vendas_total),
            "por_forma": por_forma,
            "vendas_dinheiro": moeda(dinheiro),
            "suprimentos": moeda(suprimentos),
            "sangrias": moeda(sangrias),
            "recebimentos_fiado": moeda(recebido),
            "valor_abertura": moeda(sessao["valor_abertura"]),
            "dinheiro_esperado": moeda(esperado),
        }

    def fechar_caixa(self, sessao_id: int, valor_fechamento: float, esperado: float,
                    agora: str, observacao: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE caixa_sessoes SET fechado_em = ?, valor_fechamento = ?, "
                "valor_esperado = ?, diferenca = ?, observacao = ? WHERE id = ?",
                (agora, moeda(valor_fechamento), moeda(esperado),
                 moeda(decimal(moeda(valor_fechamento)) - decimal(moeda(esperado))),
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

    def resumo_vendas_hoje(self, user_id: int) -> dict[str, Any]:
        """Dia comercial de MT, independente do fuso do host e da paginação."""
        dia = datetime.now(timezone(timedelta(hours=-4))).date().isoformat()
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) quantidade, COALESCE(SOMA_DINHEIRO(total), 0) total "
                "FROM vendas WHERE user_id = ? AND status = 'concluida' "
                "AND date(criado_em, '-4 hours') = ?", (user_id, dia),
            ).fetchone()
        return {"data": dia, "fuso": "America/Cuiaba", "quantidade": row["quantidade"],
                "total": row["total"]}

    def get_venda(self, venda_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        with self._lock:
            q = "SELECT * FROM vendas WHERE id = ?"
            params: tuple = (venda_id,)
            if user_id is not None:
                q += " AND user_id = ?"
                params = (venda_id, user_id)
            row = self._conn.execute(q, params).fetchone()
        return dict(row) if row else None

    def checkout_atomico(self, user_id: int, cliente_id: int | None,
                         total: float, desconto: float, forma_pagamento: str,
                         observacao: str, itens: list[dict], agora: str,
                         pagamento_detalhe: str | None = None) -> dict[str, Any]:
        """Estoque, venda, histórico e fiado pertencem ao mesmo COMMIT.

        Não chamar métodos que abrem ``with self._conn`` aqui: esses contextos
        aninhados poderiam antecipar o commit. BEGIN IMMEDIATE também serializa
        escritores de outras conexões/processos, não só o RLock desta instância.
        Os preços são o snapshot calculado pelo checkout autenticado.
        """
        with self._lock, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            if not itens:
                raise ValueError("Adicione pelo menos um item à venda.")
            if forma_pagamento == "fiado" and not cliente_id:
                raise ValueError("Selecione um cliente para venda fiada.")
            if cliente_id is not None:
                cliente = self.get_cliente(cliente_id, user_id)
                if not cliente or not cliente["ativo"]:
                    raise ValueError("Cliente não encontrado ou desativado.")
            quantidades = {}
            produtos = {}
            for item in itens:
                quantidade = decimal(item.get("quantidade_estoque", item["quantidade"]))
                if quantidade <= 0:
                    raise ValueError("Quantidade deve ser maior que zero.")
                pid = item["produto_id"]
                produto = self.get_produto(pid, user_id)
                if not produto or not produto["ativo"]:
                    raise ValueError("Produto não encontrado ou desativado.")
                produtos[pid] = produto
                quantidades[pid] = quantidades.get(pid, decimal(0)) + quantidade
            for pid, quantidade in quantidades.items():
                estoque = decimal(produtos[pid]["estoque"])
                if quantidade > estoque:
                    raise EstoqueConcorrente(f"Estoque insuficiente de '{produtos[pid]['nome']}'.")
                baixa = self._conn.execute(
                    "UPDATE produtos SET estoque = ?, atualizado_em = ? WHERE id = ? AND user_id = ?",
                    (float(estoque - quantidade), agora, pid, user_id),
                )
                if baixa.rowcount != 1:
                    raise EstoqueConcorrente("Não foi possível baixar o estoque. Tente novamente.")
            aberta = self._conn.execute(
                "SELECT id FROM caixa_sessoes WHERE user_id = ? AND fechado_em IS NULL "
                "ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            cur = self._conn.execute(
                "INSERT INTO vendas (user_id, cliente_id, total, desconto, forma_pagamento, "
                "status, observacao, criado_em, pagamento_detalhe, sessao_id) "
                "VALUES (?, ?, ?, ?, ?, 'concluida', ?, ?, ?, ?)",
                (user_id, cliente_id, moeda(total), moeda(desconto), forma_pagamento,
                 observacao, agora, pagamento_detalhe, aberta["id"] if aberta else None),
            )
            venda_id = cur.lastrowid
            for item in itens:
                self._conn.execute(
                    "INSERT INTO itens_venda (venda_id, produto_id, nome_produto, quantidade, "
                    "preco_unitario, subtotal, modo_venda, unidade_venda, quantidade_estoque, custo_unitario_estoque) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (venda_id, item["produto_id"], item["nome_produto"], item["quantidade"],
                     item["preco_unitario"], moeda(item["subtotal"]), item.get("modo_venda"),
                     item.get("unidade_venda"), item.get("quantidade_estoque", item["quantidade"]), item.get("custo_unitario_estoque")),
                )
                self._conn.execute(
                    "INSERT INTO movimentacoes_estoque (user_id, produto_id, tipo, quantidade, "
                    "custo_unitario, origem, documento, observacao, criado_em) "
                    "VALUES (?, ?, 'saida', ?, NULL, 'venda', ?, ?, ?)",
                    (user_id, item["produto_id"], item.get("quantidade_estoque", item["quantidade"]), str(venda_id),
                     item["nome_produto"], agora),
                )
            if forma_pagamento == "fiado":
                self._conn.execute(
                    "INSERT INTO contas_receber (user_id, venda_id, cliente_id, valor_total, "
                    "valor_pendente, data_vencimento, status, observacao, criado_em, atualizado_em) "
                    "VALUES (?, ?, ?, ?, ?, NULL, 'pendente', ?, ?, ?)",
                    (user_id, venda_id, cliente_id, moeda(total), moeda(total),
                     f"Venda #{venda_id} — {len(itens)} item(ns)", agora, agora),
                )
            return self.get_venda(venda_id)

    def cancelar_venda(self, venda_id: int, user_id: int, motivo: str,
                       agora: str) -> dict[str, Any] | None:
        """Estorno comercial exatamente uma vez, com motivo e trilha de estoque."""
        motivo = motivo.strip()
        if not 3 <= len(motivo) <= 255:
            raise ValueError("Informe um motivo de cancelamento com 3 a 255 caracteres.")
        with self._lock, self._conn:
            self._conn.execute("BEGIN IMMEDIATE")
            venda = self.get_venda(venda_id, user_id)
            if not venda:
                return None
            if venda["status"] != "concluida":
                raise ValueError("Venda já cancelada ou não concluída.")
            nota_ativa = self._conn.execute(
                "SELECT id FROM notas_fiscais WHERE venda_id = ? "
                "AND status IN ('autorizada','pendente','processando','contingencia') LIMIT 1",
                (venda_id,),
            ).fetchone()
            if nota_ativa:
                raise ValueError("Resolva o documento fiscal antes de cancelar a venda: "
                                 "cancele a nota autorizada ou consulte a nota ainda pendente.")
            if venda.get("sessao_id"):
                sessao = self._conn.execute(
                    "SELECT fechado_em FROM caixa_sessoes WHERE id = ?",
                    (venda["sessao_id"],),
                ).fetchone()
                if sessao and sessao["fechado_em"]:
                    raise ValueError("Caixa dessa venda já foi fechado.")
            contas = self._conn.execute(
                "SELECT valor_total, valor_pendente, status FROM contas_receber "
                "WHERE venda_id = ? AND user_id = ?", (venda_id, user_id),
            ).fetchall()
            if any(c["status"] in ("pago", "parcial") or
                   decimal(c["valor_pendente"]) < decimal(c["valor_total"]) for c in contas):
                raise ValueError("Estorne o recebimento antes de cancelar a venda fiada.")
            for item in self.get_itens_venda(venda_id):
                produto = self.get_produto(item["produto_id"], user_id)
                if not produto:
                    raise ValueError("Produto da venda não encontrado; estorno não realizado.")
                quantidade_devolvida = item.get("quantidade_estoque") if item.get("quantidade_estoque") is not None else item["quantidade"]
                estoque = decimal(produto["estoque"]) + decimal(quantidade_devolvida)
                atualizacao = self._conn.execute(
                    "UPDATE produtos SET estoque = ?, atualizado_em = ? WHERE id = ? AND user_id = ?",
                    (float(estoque), agora, produto["id"], user_id),
                )
                if atualizacao.rowcount != 1:
                    raise ValueError("Não foi possível devolver o estoque; estorno não realizado.")
                movimento = self._conn.execute(
                    "INSERT INTO movimentacoes_estoque (user_id, produto_id, tipo, quantidade, "
                    "origem, documento, observacao, criado_em) "
                    "VALUES (?, ?, 'entrada', ?, 'cancelamento_venda', ?, ?, ?)",
                    (user_id, produto["id"], quantidade_devolvida, str(venda_id), motivo, agora),
                )
                if movimento.rowcount != 1:
                    raise ValueError("Não foi possível registrar a devolução; estorno não realizado.")
            estorno = self._conn.execute(
                "UPDATE contas_receber SET status = 'cancelado', valor_pendente = 0, "
                "atualizado_em = ? WHERE venda_id = ? AND user_id = ?",
                (agora, venda_id, user_id),
            )
            if estorno.rowcount != len(contas):
                raise ValueError("Não foi possível estornar o fiado; cancelamento não realizado.")
            atualizacao = self._conn.execute(
                "UPDATE vendas SET status = 'cancelada', cancelada_em = ?, "
                "motivo_cancelamento = ?, sincronizado = 0 WHERE id = ? AND user_id = ?",
                (agora, motivo, venda_id, user_id),
            )
            if atualizacao.rowcount != 1:
                raise ValueError("Não foi possível cancelar a venda; estorno não realizado.")
            return self.get_venda_completa(venda_id, user_id)

    def create_venda(self, user_id: int, cliente_id: int | None,
                     total: float, desconto: float,
                     forma_pagamento: str, observacao: str, itens: list[dict],
                     agora: str, pagamento_detalhe: str | None = None) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO vendas (user_id, cliente_id, total, desconto, forma_pagamento, status, observacao, criado_em, pagamento_detalhe)
                   VALUES (?, ?, ?, ?, ?, 'concluida', ?, ?, ?)""",
                (user_id, cliente_id, moeda(total), moeda(desconto), forma_pagamento, observacao, agora, pagamento_detalhe),
            )
            venda_id = cursor.lastrowid
            for item in itens:
                self._conn.execute(
                    """INSERT INTO itens_venda (venda_id, produto_id, nome_produto, quantidade, preco_unitario, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (venda_id, item["produto_id"], item["nome_produto"],
                     item["quantidade"], item["preco_unitario"], moeda(item["subtotal"])),
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
            cursor = self._conn.execute(
                f"UPDATE categorias SET {sets} WHERE id = ? AND user_id = ?",
                vals + [categoria_id, user_id],
            )
            if cursor.rowcount != 1:
                return None
            row = self._conn.execute(
                "SELECT * FROM categorias WHERE id = ? AND user_id = ?",
                (categoria_id, user_id),
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

    def cliente_tem_divida_aberta(self, cliente_id: int, user_id: int) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM contas_receber WHERE cliente_id = ? AND user_id = ? "
                "AND status IN ('pendente', 'parcial') LIMIT 1",
                (cliente_id, user_id),
            ).fetchone()
        return row is not None

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
                       endereco: str, observacao: str, agora: str, **fiscais) -> dict[str, Any] | None:
        extra_cols = ("documento", "inscricao_estadual", "indicador_ie", "logradouro",
                      "numero", "bairro", "municipio", "codigo_municipio", "uf", "cep")
        cols = ("user_id", "nome", "telefone", "email", "endereco", "observacao",
                *extra_cols, "criado_em", "atualizado_em")
        vals = [
            user_id, nome.strip(), telefone.strip(), email.strip(), endereco.strip(), observacao.strip(),
            *[(fiscais.get(c) or "").strip() for c in extra_cols],
            agora, agora,
        ]
        with self._lock, self._conn:
            cursor = self._conn.execute(
                f"INSERT INTO clientes ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                vals,
            )
            return self.get_cliente(cursor.lastrowid)

    def update_cliente(self, cliente_id: int, user_id: int, **kwargs) -> dict[str, Any] | None:
        allowed = {"nome", "telefone", "email", "endereco", "observacao", "ativo", "atualizado_em",
                   "documento", "inscricao_estadual", "indicador_ie", "logradouro",
                   "numero", "bairro", "municipio", "codigo_municipio", "uf", "cep"}
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
            ids = [r["id"] for r in rows]
            por_conta: dict[int, list[dict[str, Any]]] = {}
            if ids:
                marcas = ",".join("?" for _ in ids)
                for pagamento in self._conn.execute(
                    "SELECT id, user_id, conta_id, valor, forma, criado_em "
                    f"FROM pagamentos_fiado WHERE conta_id IN ({marcas}) ORDER BY id",
                    ids,
                ):
                    por_conta.setdefault(pagamento["conta_id"], []).append(dict(pagamento))
        return [{**dict(r), "pagamentos": por_conta.get(r["id"], [])} for r in rows]

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
            if not row:
                return None
            resultado = dict(row)
            pagamentos = self._conn.execute(
                "SELECT id, user_id, conta_id, valor, forma, criado_em "
                "FROM pagamentos_fiado WHERE conta_id = ? ORDER BY id",
                (conta_id,),
            ).fetchall()
            resultado["pagamentos"] = [dict(p) for p in pagamentos]
            return resultado

    def create_conta_receber(self, user_id: int, cliente_id: int | None, venda_id: int | None,
                              valor_total: float, data_vencimento: str | None,
                              observacao: str, agora: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """INSERT INTO contas_receber (user_id, venda_id, cliente_id, valor_total,
                   valor_pendente, data_vencimento, status, observacao, criado_em, atualizado_em)
                   VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)""",
                (user_id, venda_id, cliente_id, moeda(valor_total), moeda(valor_total),
                 data_vencimento, observacao, agora, agora),
            )
            return self.get_conta_receber(cursor.lastrowid)

    def pagar_conta_receber(self, conta_id: int, user_id: int, valor: float, agora: str,
                             forma: str = "dinheiro") -> dict[str, Any] | None:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM contas_receber WHERE id = ? AND user_id = ?",
                (conta_id, user_id),
            ).fetchone()
            if not row:
                return None
            if row["status"] == "cancelado":
                raise ValueError("Conta cancelada não recebe pagamento.")
            pago = decimal(moeda(valor))
            pendente = decimal(row["valor_pendente"])
            if pago <= 0:
                raise ValueError("Valor deve ser maior que zero.")
            if pago > pendente:
                raise ValueError("Pagamento maior que o pendente.")
            novo_pendente = moeda(pendente - pago)
            if novo_pendente == 0:
                self._conn.execute(
                    "UPDATE contas_receber SET valor_pendente = 0, status = 'pago', atualizado_em = ? WHERE id = ?",
                    (agora, conta_id),
                )
            else:
                self._conn.execute(
                    "UPDATE contas_receber SET valor_pendente = ?, status = 'parcial', atualizado_em = ? WHERE id = ?",
                    (novo_pendente, agora, conta_id),
                )
            forma_limpa = (forma or "dinheiro").strip() or "dinheiro"
            sessao_id = None
            if forma_limpa.casefold() == "dinheiro":
                aberta = self._conn.execute(
                    "SELECT id FROM caixa_sessoes WHERE user_id = ? AND fechado_em IS NULL "
                    "ORDER BY id DESC LIMIT 1",
                    (user_id,),
                ).fetchone()
                sessao_id = aberta["id"] if aberta else None
            self._conn.execute(
                "INSERT INTO pagamentos_fiado (user_id, conta_id, valor, forma, criado_em, sessao_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, conta_id, moeda(valor), forma_limpa, agora, sessao_id),
            )
            return self.get_conta_receber(conta_id, user_id)

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
                "SELECT COUNT(*), COALESCE(SOMA_DINHEIRO(total), 0) FROM vendas WHERE user_id = ? AND status = 'concluida' AND date(criado_em, 'localtime') = ?",
                (user_id, hoje),
            ).fetchone()

            total_vendas = self._conn.execute(
                "SELECT COALESCE(SOMA_DINHEIRO(total), 0) FROM vendas WHERE user_id = ? AND status = 'concluida'",
                (user_id,),
            ).fetchone()[0]

            ultimas_vendas_rows = self._conn.execute(
                "SELECT id, total, forma_pagamento, criado_em FROM vendas WHERE user_id = ? AND status = 'concluida' ORDER BY criado_em DESC LIMIT 5",
                (user_id,),
            ).fetchall()

            produtos_baixo = self._conn.execute(
                "SELECT id, nome, estoque, estoque_minimo FROM produtos WHERE user_id = ? AND ativo = 1 AND estoque <= estoque_minimo ORDER BY estoque LIMIT 5",
                (user_id,),
            ).fetchall()

            # Novos indicadores
            contas_pendentes = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SOMA_DINHEIRO(valor_pendente), 0) FROM contas_receber "
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

    # ── Relatórios ──
    def relatorio_vendas(self, user_id: int, inicio: str, fim: str) -> dict[str, Any]:
        """Relatório de vendas concluídas no período [inicio, fim] (datas locais
        YYYY-MM-DD), consistente com o filtro do Dashboard (date(criado_em))."""
        with self._lock:
            resumo = self._conn.execute(
                "SELECT COUNT(*) qtd, COALESCE(SOMA_DINHEIRO(total),0) total, COALESCE(SOMA_DINHEIRO(desconto),0) desconto "
                "FROM vendas WHERE user_id=? AND status='concluida' "
                "AND date(criado_em, 'localtime') BETWEEN ? AND ?", (user_id, inicio, fim)
            ).fetchone()
            por_forma = self._conn.execute(
                "SELECT forma_pagamento, COUNT(*) qtd, COALESCE(SOMA_DINHEIRO(total),0) total FROM vendas "
                "WHERE user_id=? AND status='concluida' AND date(criado_em, 'localtime') BETWEEN ? AND ? "
                "GROUP BY forma_pagamento ORDER BY total DESC", (user_id, inicio, fim)
            ).fetchall()
            por_dia = self._conn.execute(
                "SELECT date(criado_em, 'localtime') dia, COUNT(*) qtd, COALESCE(SOMA_DINHEIRO(total),0) total FROM vendas "
                "WHERE user_id=? AND status='concluida' AND date(criado_em, 'localtime') BETWEEN ? AND ? "
                "GROUP BY dia ORDER BY dia", (user_id, inicio, fim)
            ).fetchall()
            top = self._conn.execute(
                "SELECT i.produto_id, i.nome_produto, SUM(i.quantidade) qtd, SOMA_DINHEIRO(i.subtotal) total "
                "FROM itens_venda i JOIN vendas v ON v.id=i.venda_id "
                "WHERE v.user_id=? AND v.status='concluida' AND date(v.criado_em, 'localtime') BETWEEN ? AND ? "
                "GROUP BY i.produto_id, i.nome_produto ORDER BY total DESC LIMIT 10",
                (user_id, inicio, fim)
            ).fetchall()
            margem = self._conn.execute(
                "SELECT i.preco_unitario, COALESCE(i.custo_unitario_estoque,p.preco_custo,0) preco_custo, i.quantidade, COALESCE(i.quantidade_estoque,i.quantidade) quantidade_estoque "
                "FROM itens_venda i JOIN vendas v ON v.id=i.venda_id "
                "LEFT JOIN produtos p ON p.id=i.produto_id "
                "WHERE v.user_id=? AND v.status='concluida' AND date(v.criado_em, 'localtime') BETWEEN ? AND ?",
                (user_id, inicio, fim)
            ).fetchall()
        faturamento = resumo["total"]
        qtd = resumo["qtd"]
        desconto = resumo["desconto"]
        # Lucro estimado: margem por item (custo atual) menos os descontos da venda.
        lucro = somar(decimal(r["preco_unitario"]) * decimal(r["quantidade"])
                      - decimal(r["preco_custo"]) * decimal(r["quantidade_estoque"]) for r in margem) - decimal(desconto)
        return {
            "inicio": inicio, "fim": fim,
            "faturamento": moeda(faturamento),
            "qtd_vendas": qtd,
            "ticket_medio": moeda(decimal(faturamento) / decimal(qtd)) if qtd else 0.0,
            "desconto_total": moeda(desconto),
            "lucro_estimado": moeda(lucro),
            "por_forma": [dict(r) for r in por_forma],
            "por_dia": [dict(r) for r in por_dia],
            "top_produtos": [dict(r) for r in top],
        }

    def relatorio_fiscal_segregado(self, user_id: int, inicio: str, fim: str) -> dict[str, Any]:
        """Faturamento do período separado por tratamento tributário, para a
        apuração do Simples Nacional (PGDAS-D).

        O objetivo é evitar a bitributação: produtos com ICMS já recolhido por
        Substituição Tributária (CSOSN 500) e com PIS/COFINS monofásico, ST ou
        alíquota zero (CST 04/05/06) NÃO devem ser tributados de novo no DAS — devem ser
        informados como receita "com substituição tributária / tributação
        concentrada". Aqui somamos a receita de cada grupo a partir dos itens
        vendidos, cruzando com a classificação fiscal atual do produto.
        """
        with self._lock:
            linhas = self._conn.execute(
                "SELECT i.produto_id, i.nome_produto, "
                "       COALESCE(p.ncm,'') ncm, "
                "       COALESCE(NULLIF(p.cst_csosn,''),'102') csosn, "
                "       COALESCE(NULLIF(p.cst_pis,''),'07') cst_pis, "
                "       COALESCE(NULLIF(p.cst_cofins,''),'07') cst_cofins, "
                "       SUM(i.quantidade) qtd, SOMA_DINHEIRO(i.subtotal) total "
                "FROM itens_venda i JOIN vendas v ON v.id=i.venda_id "
                "LEFT JOIN produtos p ON p.id=i.produto_id "
                "WHERE v.user_id=? AND v.status='concluida' "
                "AND date(v.criado_em, 'localtime') BETWEEN ? AND ? "
                "GROUP BY i.produto_id, i.nome_produto, ncm, csosn, cst_pis, cst_cofins "
                "ORDER BY total DESC",
                (user_id, inicio, fim)
            ).fetchall()

        # CSOSN de ICMS já recolhido por ST (não tributar ICMS de novo no DAS).
        ICMS_ST = {"500"}
        # CST PIS/COFINS de tributação concentrada (monofásico), ST ou alíquota zero.
        PC_CONCENTRADO = {"04", "05", "06"}

        icms_st = icms_normal = decimal(0)
        pc_concentrado = pc_normal = decimal(0)
        receita_segregada = receita_normal = decimal(0)
        total_geral = decimal(0)
        itens: list[dict[str, Any]] = []
        for r in linhas:
            valor = decimal(r["total"] or 0)
            total_geral += valor
            csosn = str(r["csosn"]).strip()
            cst_pis = str(r["cst_pis"]).strip().zfill(2)
            cst_cofins = str(r["cst_cofins"]).strip().zfill(2)
            icms_recolhido = csosn in ICMS_ST
            pc_recolhido = cst_pis in PC_CONCENTRADO or cst_cofins in PC_CONCENTRADO
            if icms_recolhido:
                icms_st += valor
            else:
                icms_normal += valor
            if pc_recolhido:
                pc_concentrado += valor
            else:
                pc_normal += valor
            # Segregado no PGDAS-D = tem ICMS-ST e/ou PIS-COFINS concentrado.
            if icms_recolhido or pc_recolhido:
                receita_segregada += valor
            else:
                receita_normal += valor
            itens.append({
                "produto_id": r["produto_id"],
                "nome_produto": r["nome_produto"],
                "ncm": r["ncm"],
                "csosn": csosn,
                "cst_pis": cst_pis,
                "cst_cofins": cst_cofins,
                "qtd": round(r["qtd"] or 0.0, 3),
                "total": moeda(valor),
                "icms_substituicao": icms_recolhido,
                "pis_cofins_concentrado": pc_recolhido,
            })

        return {
            "inicio": inicio, "fim": fim,
            "total_geral": moeda(total_geral),
            "icms": {
                "substituicao_tributaria": moeda(icms_st),
                "tributado_normal": moeda(icms_normal),
            },
            "pis_cofins": {
                "monofasico_st": moeda(pc_concentrado),
                "tributado_normal": moeda(pc_normal),
            },
            "receita_segregada": moeda(receita_segregada),
            "receita_tributada_integral": moeda(receita_normal),
            "itens": itens,
        }

    def close(self) -> None:
        self._conn.close()

    # ── Backup / restauração ──
    def caminho_db(self) -> str:
        return str(self.arquivo_principal)

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
        self._conn = sqlite3.connect(str(self._caminho), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.create_aggregate("SOMA_DINHEIRO", 1, _SomaDinheiro)
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA synchronous = FULL")
        with self._conn:
            self._conn.execute("PRAGMA journal_mode = WAL")

    def restaurar_de(self, origem: Path, antes_de_trocar: Callable[[], object] | None = None) -> None:
        """Valida e migra uma cópia antes da troca transacional pelo SQLite."""
        origem = Path(origem)
        verificar_integridade(origem)
        with tempfile.TemporaryDirectory(prefix=".vf-restaurar-", dir=self._caminho.parent) as pasta:
            copia = Path(pasta) / "restaurar.db"
            try:
                with closing(abrir_sqlite_leitura(origem)) as fonte:
                    tabelas = {linha[0] for linha in fonte.execute(
                        "SELECT name FROM sqlite_schema WHERE type = 'table'"
                    )}
                    if not {"users", "produtos", "clientes", "vendas", "itens_venda"} <= tabelas:
                        raise ValueError("Arquivo inválido: não é um backup do VendaFácil.")
                    with closing(sqlite3.connect(copia)) as destino:
                        fonte.backup(destino)
                migrada = Database(copia)
            except sqlite3.Error as exc:
                raise ValueError("Arquivo incompatível com o banco do VendaFácil.") from exc
            try:
                with self._lock:
                    if antes_de_trocar is not None:
                        antes_de_trocar()
                    migrada._conn.backup(self._conn)
            finally:
                migrada.close()


def abrir_banco_local() -> Database:
    """Mantém o banco original intacto quando a validação na abertura falha."""
    try:
        if DB_PATH.is_file():
            verificar_integridade(DB_PATH)
        return Database()
    except (sqlite3.DatabaseError, ValueError):
        pasta = DB_PATH.parent / "backups"
        candidatos = sorted(pasta.glob("vendafacil-*.db"), key=lambda p: p.stat().st_mtime_ns,
                            reverse=True)
        for arquivo in candidatos:
            try:
                verificar_integridade(arquivo)
                copia = Database(arquivo, somente_leitura=True)
                try:
                    copia._conn.execute("SELECT id, email, senha_hash FROM users LIMIT 1")
                    copia._conn.execute("SELECT id, nome FROM produtos LIMIT 1")
                except sqlite3.Error:
                    copia.close()
                    continue
                copia.arquivo_principal = DB_PATH
                copia.backup_recuperacao = arquivo
                return copia
            except (ValueError, sqlite3.Error):
                continue
        consulta = Database(Path(":memory:"))
        consulta.arquivo_principal = DB_PATH
        consulta.modo_consulta = True
        consulta._conn.execute("PRAGMA query_only = ON")
        return consulta


# Singleton
db = abrir_banco_local()
