# main.py
import argparse
import os
import sqlite3
import sys

from storage import Storage
from ui import TrackerApp


def main():
    parser = argparse.ArgumentParser(description="Master Duel coin flip tracker")
    parser.add_argument("--db", default="data/duels.db", help="SQLite database path")
    args = parser.parse_args()

    db_dir = os.path.dirname(args.db)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        storage = Storage(args.db)
    except sqlite3.Error as e:
        print(f"无法打开数据库 {args.db}: {e}")
        print("请备份或删除该文件后重试。")
        sys.exit(1)

    app = TrackerApp(storage)
    try:
        app.run()
    finally:
        storage.close()


if __name__ == "__main__":
    main()
