import sqlite3, os
from datetime import datetime
from .config import DB_PATH

class SQLiteMemory:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            role TEXT,
            content TEXT
        )""")
        self.conn.commit()

    def save(self, role, content):
        self.conn.execute(
            "INSERT INTO memory (timestamp, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), role, content)
        )
        self.conn.commit()

    def load(self):
        cur = self.conn.cursor()
        cur.execute("SELECT role, content FROM memory ORDER BY id DESC LIMIT 20")
        return cur.fetchall()

    def reset(self):
        self.conn.execute("DELETE FROM memory")
        self.conn.commit()
