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


class InvalidDateError(ValueError):
    """日期不符合 YYYY-MM-DD —— 让调用方能区分日期错误与其他 ValueError。"""


def _validate_date(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateError(f"无效日期: {value!r}，应为 YYYY-MM-DD")
    # 归一化 "2026-1-5" → "2026-01-05"，否则 GROUP BY date 会把同一天拆成两行
    return parsed.strftime("%Y-%m-%d")


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
        date = _validate_date(date) if date is not None else now.strftime("%Y-%m-%d")
        cur = self.conn.execute(
            "INSERT INTO duels (created_at, date, coin_win, went_first, duel_win, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now.isoformat(), date,
             int(coin_win), int(went_first), int(duel_win), note),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM duels ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_records(self, date: str | None = None) -> list[dict]:
        if date is None:
            rows = self.conn.execute("SELECT * FROM duels ORDER BY id DESC").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM duels WHERE date = ? ORDER BY id DESC", (date,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_dates(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT date FROM duels ORDER BY date DESC"
        ).fetchall()
        return [r["date"] for r in rows]

    def update_duel(
        self,
        duel_id: int,
        coin_win: int,
        went_first: int,
        duel_win: int,
        note: str | None,
        date: str,
    ) -> bool:
        _validate_date(date)
        cur = self.conn.execute(
            "UPDATE duels SET date = ?, coin_win = ?, went_first = ?, duel_win = ?, note = ? "
            "WHERE id = ?",
            (date, int(coin_win), int(went_first), int(duel_win), note, duel_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_duel(self, duel_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM duels WHERE id = ?", (duel_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_last(self) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM duels ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        self.conn.execute("DELETE FROM duels WHERE id = ?", (row["id"],))
        self.conn.commit()
        return row["id"]

    def get_by_date(self, date: str) -> list[dict]:
        # 与 get_records 同一查询，只是顺序相反：统计连串取 records[-1] 作为最新一条
        return list(reversed(self.get_records(date)))

    def get_daily_counts(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT date, COUNT(*) AS total, SUM(coin_win) AS coin_wins "
            "FROM duels GROUP BY date ORDER BY date"
        ).fetchall()
        return [dict(r) for r in rows]
