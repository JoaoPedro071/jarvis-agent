import os
import sqlite3
from contextlib import contextmanager


@contextmanager
def conexao():
    """Abre o banco, entrega a conexão e garante commit e fechamento."""
    caminho = os.environ.get("JARVIS_DB", "jarvis.db")
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row  # permite acessar colunas pelo nome
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            postponed_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
