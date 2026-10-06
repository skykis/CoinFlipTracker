# storage.py
import sqlite3
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS duels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    date TEXT NOT NULL,
    coin_win INTEGER NOT NULL CHECK (coin_win IN (0, 1)),
    went_first INTEGER NOT NULL CHECK (went_first IN (0, 1)),
    duel_win INTEGER NOT NULL CHECK (duel_win IN (0, 1)),
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_duels_date ON duels (date);
"""


class Storage:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        try:
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(SCHEMA)
        except sqlite3.Error:
            self.conn.close()
            raise

    def close(self) -> None:
        self.conn.close()

    def __del__(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    def insert_duel(
        self,
        coin_win: int,
        went_first: int,
        duel_win: int,
        note: str | None = None,
        date: str | None = None,
    ) -> int:
        now = datetime.now()
        cur = self.conn.execute(
            "INSERT INTO duels (created_at, date, coin_win, went_first, duel_win, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now.isoformat(), date or now.strftime("%Y-%m-%d"),
             int(coin_win), int(went_first), int(duel_win), note),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM duels ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_by_date(self, date: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM duels WHERE date = ? ORDER BY id", (date,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_daily_counts(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT date, COUNT(*) AS total, SUM(coin_win) AS coin_wins "
            "FROM duels GROUP BY date ORDER BY date"
        ).fetchall()
        return [dict(r) for r in rows]
