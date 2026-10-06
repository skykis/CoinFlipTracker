# tests/test_storage.py
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime

from storage import Storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "duels.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_init_creates_db_file(self):
        Storage(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

    def test_insert_and_get_all(self):
        s = Storage(self.db_path)
        rid = s.insert_duel(1, 0, 1, note="test")
        recs = s.get_all()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["id"], rid)
        self.assertEqual(recs[0]["coin_win"], 1)
        self.assertEqual(recs[0]["went_first"], 0)
        self.assertEqual(recs[0]["duel_win"], 1)
        self.assertEqual(recs[0]["note"], "test")
        self.assertEqual(recs[0]["date"], datetime.now().strftime("%Y-%m-%d"))

    def test_insert_rejects_invalid_flag_values(self):
        s = Storage(self.db_path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                s.insert_duel(2, 1, 1)
        finally:
            s.close()

    def test_get_by_date_filters(self):
        s = Storage(self.db_path)
        s.insert_duel(1, 1, 1, date="2026-10-05")
        s.insert_duel(0, 0, 0, date="2026-10-06")
        self.assertEqual(len(s.get_by_date("2026-10-05")), 1)
        self.assertEqual(len(s.get_by_date("2026-10-06")), 1)
        self.assertEqual(len(s.get_by_date("2020-01-01")), 0)

    def test_daily_counts(self):
        s = Storage(self.db_path)
        s.insert_duel(1, 1, 0, date="2026-10-06")
        s.insert_duel(0, 0, 1, date="2026-10-06")
        s.insert_duel(1, 0, 1, date="2026-10-05")
        counts = s.get_daily_counts()
        self.assertEqual(len(counts), 2)
        day = next(c for c in counts if c["date"] == "2026-10-06")
        self.assertEqual(day["total"], 2)
        self.assertEqual(day["coin_wins"], 1)


if __name__ == "__main__":
    unittest.main()
