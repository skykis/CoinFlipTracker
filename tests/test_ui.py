# tests/test_ui.py
import os
import tempfile
import unittest
import tkinter as tk

from storage import Storage
from ui import TrackerApp


class UITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(os.path.join(self.tmp.name, "duels.db"))
        self.root = tk.Tk()
        self.app = TrackerApp(self.storage, root=self.root)

    def tearDown(self):
        self.root.destroy()
        self.storage.close()
        self.tmp.cleanup()

    def test_incomplete_input_not_saved(self):
        self.app.select("coin_win", 1)
        self.assertFalse(self.app.can_save())
        self.assertIsNone(self.app.save())
        self.assertEqual(len(self.storage.get_all()), 0)

    def test_complete_input_saved_and_reset(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        rid = self.app.save()
        self.assertIsNotNone(rid)
        rec = self.storage.get_all()[0]
        self.assertEqual(rec["coin_win"], 1)
        self.assertEqual(rec["went_first"], 0)
        self.assertEqual(rec["duel_win"], 1)
        self.assertFalse(self.app.can_save())

    def test_refresh_with_no_data_does_not_crash(self):
        self.app.refresh()


if __name__ == "__main__":
    unittest.main()
