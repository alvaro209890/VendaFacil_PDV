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

    def close(self) -> None:
        self._conn.close()


# Singleton
db = Database()
