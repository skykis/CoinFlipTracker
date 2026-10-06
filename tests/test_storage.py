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

    def test_get_records_returns_newest_first(self):
        s = Storage(self.db_path)
        first = s.insert_duel(1, 1, 1)
        second = s.insert_duel(0, 0, 0)
        self.assertEqual([r["id"] for r in s.get_records()], [second, first])

    def test_get_records_filters_by_date(self):
        s = Storage(self.db_path)
        s.insert_duel(1, 1, 1, date="2026-10-05")
        s.insert_duel(0, 0, 0, date="2026-10-06")
        self.assertEqual(len(s.get_records("2026-10-05")), 1)
        self.assertEqual(len(s.get_records()), 2)

    def test_get_dates_returns_unique_dates_desc(self):
        s = Storage(self.db_path)
        s.insert_duel(1, 1, 1, date="2026-10-05")
        s.insert_duel(1, 1, 1, date="2026-10-05")
        s.insert_duel(1, 1, 1, date="2026-10-06")
        self.assertEqual(s.get_dates(), ["2026-10-06", "2026-10-05"])

    def test_get_dates_on_empty_db(self):
        s = Storage(self.db_path)
        self.assertEqual(s.get_dates(), [])

    def test_insert_rejects_invalid_date(self):
        s = Storage(self.db_path)
        with self.assertRaises(ValueError):
            s.insert_duel(1, 1, 1, date="2026-13-40")

    def test_update_duel_changes_fields(self):
        s = Storage(self.db_path)
        rid = s.insert_duel(1, 1, 1, note="oops", date="2026-10-05")
        self.assertTrue(s.update_duel(rid, 0, 0, 0, "fixed", "2026-10-04"))
        rec = s.get_all()[0]
        self.assertEqual(
            (rec["coin_win"], rec["went_first"], rec["duel_win"], rec["note"], rec["date"]),
            (0, 0, 0, "fixed", "2026-10-04"),
        )

    def test_update_missing_id_returns_false(self):
        s = Storage(self.db_path)
        self.assertFalse(s.update_duel(999, 1, 1, 1, None, "2026-10-06"))

    def test_update_rejects_invalid_date(self):
        s = Storage(self.db_path)
        rid = s.insert_duel(1, 1, 1)
        with self.assertRaises(ValueError):
            s.update_duel(rid, 1, 1, 1, None, "not-a-date")

    def test_delete_duel_removes_record(self):
        s = Storage(self.db_path)
        rid = s.insert_duel(1, 1, 1)
        self.assertTrue(s.delete_duel(rid))
        self.assertEqual(s.get_all(), [])
        self.assertFalse(s.delete_duel(rid))

    def test_delete_last_removes_newest_record(self):
        s = Storage(self.db_path)
        first = s.insert_duel(1, 1, 1)
        second = s.insert_duel(0, 0, 0)
        self.assertEqual(s.delete_last(), second)
        self.assertEqual([r["id"] for r in s.get_all()], [first])

    def test_delete_last_on_empty_db_returns_none(self):
        s = Storage(self.db_path)
        self.assertIsNone(s.delete_last())

    def test_get_by_date_returns_oldest_first(self):
        # 统计连串取 records[-1] 作为最新一条，所以 get_by_date 必须升序
        s = Storage(self.db_path)
        first = s.insert_duel(1, 1, 1, date="2026-10-06")
        second = s.insert_duel(0, 0, 0, date="2026-10-06")
        self.assertEqual([r["id"] for r in s.get_by_date("2026-10-06")], [first, second])
        s.close()

    def test_non_padded_date_is_normalized(self):
        s = Storage(self.db_path)
        s.insert_duel(1, 1, 1, date="2026-1-5")
        self.assertEqual(s.get_all()[0]["date"], "2026-01-05")
        self.assertEqual(s.get_dates(), ["2026-01-05"])
        s.close()


if __name__ == "__main__":
    unittest.main()
