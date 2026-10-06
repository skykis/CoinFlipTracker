# main.py
import argparse
import os

from storage import Storage
from ui import TrackerApp


def main():
    parser = argparse.ArgumentParser(description="Master Duel coin flip tracker")
    parser.add_argument("--db", default="data/duels.db", help="SQLite database path")
    args = parser.parse_args()

    db_dir = os.path.dirname(args.db)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    storage = Storage(args.db)
    app = TrackerApp(storage)
    try:
        app.root.mainloop()
    finally:
        storage.close()


if __name__ == "__main__":
    main()
