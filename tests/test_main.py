# tests/test_main.py
import os
import sys
import tempfile
import unittest

from main import main


class MainTest(unittest.TestCase):
    def test_corrupted_db_exits_with_friendly_message(self):
        tmp = tempfile.TemporaryDirectory()
        db_path = os.path.join(tmp.name, "duels.db")
        with open(db_path, "wb") as f:
            f.write(b"this is not a sqlite database")

        old_argv = sys.argv
        sys.argv = ["main.py", "--db", db_path]
        try:
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
        finally:
            sys.argv = old_argv
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
