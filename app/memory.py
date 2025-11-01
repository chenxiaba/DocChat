import os
import sqlite3
from datetime import datetime
from typing import Optional

from .core.config import Settings, get_settings


class SQLiteMemory:
    def __init__(
        self, db_path: Optional[str] = None, settings: Optional[Settings] = None
    ) -> None:
        self.settings = settings or get_settings()
        self.db_path = db_path or self.settings.db_path
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            role TEXT,
            content TEXT
        )"""
        )
        self.conn.commit()

    def save(self, role, content):
        self.conn.execute(
            "INSERT INTO memory (timestamp, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), role, content),
        )
        self.conn.commit()

    def load(self):
        cur = self.conn.cursor()
        cur.execute("SELECT role, content FROM memory ORDER BY id DESC LIMIT 20")
        return cur.fetchall()

    def reset(self):
        self.conn.execute("DELETE FROM memory")
        self.conn.commit()
