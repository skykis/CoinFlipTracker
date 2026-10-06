# CoinFlipTracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop app (tkinter + SQLite + matplotlib) that manually logs Master Duel coin flips, first/second choice, and duel results, and reports today/cumulative stats with streaks and daily trend charts.

**Architecture:** Four focused modules — `storage.py` (SQLite persistence), `stats.py` (pure computation, no DB), `charts.py` (matplotlib figure generation), `ui.py` (tkinter app wiring everything), plus `main.py` entry point. Tests use stdlib `unittest`; UI logic is testable by constructing `TrackerApp` with an explicit `tk.Tk` root.

**Tech Stack:** Python 3.13 (stdlib `sqlite3`, `tkinter`, `unittest`), `matplotlib` (only third-party dependency).

**Spec:** `docs/superpowers/specs/2026-10-06-coinflip-tracker-design.md`

## Global Constraints

- Python 3.13.2 on Windows 11; no dependency other than `matplotlib`.
- Tests run with `python -m unittest discover -s tests -v` from the project root.
- Default database path `data/duels.db`; `data/` is gitignored.
- All boolean-ish fields stored as INTEGER 1/0.
- Every git commit message ends with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

## Review Focus

- **Incomplete input**: save must be impossible and write nothing when any of the three selections is unset — tested in Task 4.
- **Empty database**: stats return zeros and charts return placeholder figures without crashing — tested in Tasks 2 and 3.
- **Streak edge cases**: single record, all-same, alternating sequences — tested in Task 2.
- **Date grouping**: records are grouped by the local date at insert time; inserts spanning midnight land on different days — tested in Task 1 via an explicit `date` override parameter.
- **matplotlib missing**: chart area shows a text message while input and stats keep working — guarded import in Task 4; verify manually by running with matplotlib uninstalled.

---

### Task 1: Storage module (SQLite)

**Files:**
- Create: `storage.py`
- Create: `tests/test_storage.py`
- Create: `requirements.txt`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: `Storage(path)` class with methods `insert_duel(coin_win: int, went_first: int, duel_win: int, note: str | None = None, date: str | None = None) -> int`, `get_all() -> list[dict]`, `get_by_date(date: str) -> list[dict]`, `get_daily_counts() -> list[dict]` (keys: `date`, `total`, `coin_wins`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_storage.py
import os
import tempfile
import unittest

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
        self.assertTrue(recs[0]["date"])

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_storage -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'storage'`

- [ ] **Step 3: Write minimal implementation**

```python
# storage.py
import sqlite3
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS duels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    date TEXT NOT NULL,
    coin_win INTEGER NOT NULL,
    went_first INTEGER NOT NULL,
    duel_win INTEGER NOT NULL,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_duels_date ON duels (date);
"""


class Storage:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def insert_duel(self, coin_win, went_first, duel_win, note=None, date=None):
        now = datetime.now()
        cur = self.conn.execute(
            "INSERT INTO duels (created_at, date, coin_win, went_first, duel_win, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (now.isoformat(), date or now.strftime("%Y-%m-%d"),
             int(coin_win), int(went_first), int(duel_win), note),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_all(self):
        rows = self.conn.execute("SELECT * FROM duels ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_by_date(self, date):
        rows = self.conn.execute(
            "SELECT * FROM duels WHERE date = ? ORDER BY id", (date,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_daily_counts(self):
        rows = self.conn.execute(
            "SELECT date, COUNT(*) AS total, SUM(coin_win) AS coin_wins "
            "FROM duels GROUP BY date ORDER BY date"
        ).fetchall()
        return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `python -m unittest tests.test_storage -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Create `requirements.txt` and `.gitignore`**

```
# requirements.txt
matplotlib
```

```
# .gitignore
data/
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 6: Commit**

```bash
git add storage.py tests/test_storage.py requirements.txt .gitignore
git commit -m "Add storage module with SQLite persistence

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: Stats module (pure computation)

**Files:**
- Create: `stats.py`
- Create: `tests/test_stats.py`

**Interfaces:**
- Consumes: nothing (records are plain dicts with keys `coin_win`, `went_first`, `duel_win`).
- Produces: `compute_stats(records: list[dict]) -> dict` with keys `total`, `coin_wins`, `coin_losses`, `coin_win_rate`, `first_count`, `second_count`, `first_share`, `duel_wins`, `duel_losses`, `duel_win_rate`, `coin_streak`, `coin_longest_win`, `coin_longest_loss`, `duel_streak`, `duel_longest_win`, `duel_longest_loss`; `current_streak(records, field) -> int`; `longest_streak(records, field, value) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stats.py
import unittest

from stats import compute_stats, current_streak, longest_streak


def rec(coin_win, went_first, duel_win):
    return {"coin_win": coin_win, "went_first": went_first, "duel_win": duel_win}


class StatsTest(unittest.TestCase):
    def test_empty(self):
        s = compute_stats([])
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["coin_win_rate"], 0.0)
        self.assertEqual(s["coin_streak"], 0)
        self.assertEqual(s["coin_longest_win"], 0)

    def test_basic_counts_and_rates(self):
        records = [rec(1, 1, 1), rec(0, 0, 1), rec(1, 0, 0)]
        s = compute_stats(records)
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["coin_wins"], 2)
        self.assertEqual(s["coin_losses"], 1)
        self.assertAlmostEqual(s["coin_win_rate"], 2 / 3)
        self.assertEqual(s["first_count"], 1)
        self.assertEqual(s["second_count"], 2)
        self.assertAlmostEqual(s["first_share"], 1 / 3)
        self.assertEqual(s["duel_wins"], 2)
        self.assertAlmostEqual(s["duel_win_rate"], 2 / 3)

    def test_current_streak_single(self):
        self.assertEqual(current_streak([rec(1, 1, 1)], "coin_win"), 1)

    def test_current_streak_all_same(self):
        records = [rec(1, 1, 1), rec(1, 1, 0), rec(1, 0, 1)]
        self.assertEqual(current_streak(records, "coin_win"), 3)

    def test_current_streak_alternating(self):
        records = [rec(1, 1, 1), rec(0, 1, 1), rec(1, 0, 0)]
        self.assertEqual(current_streak(records, "coin_win"), 1)

    def test_longest_streak_spec_example(self):
        # WWLLW -> current streak 1, longest win streak 2
        records = [rec(1, 1, 1), rec(1, 1, 1), rec(0, 0, 0), rec(0, 0, 0), rec(1, 1, 1)]
        self.assertEqual(current_streak(records, "coin_win"), 1)
        self.assertEqual(longest_streak(records, "coin_win", 1), 2)
        self.assertEqual(longest_streak(records, "coin_win", 0), 2)

    def test_duel_streaks_independent_of_coin(self):
        records = [rec(1, 1, 0), rec(0, 1, 1), rec(1, 0, 1)]
        s = compute_stats(records)
        self.assertEqual(s["coin_streak"], 1)
        self.assertEqual(s["duel_streak"], 2)
        self.assertEqual(s["duel_longest_win"], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_stats -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stats'`

- [ ] **Step 3: Write minimal implementation**

```python
# stats.py
def current_streak(records, field):
    if not records:
        return 0
    streak = 1
    last = records[-1][field]
    for r in reversed(records[:-1]):
        if r[field] == last:
            streak += 1
        else:
            break
    return streak


def longest_streak(records, field, value):
    best = 0
    run = 0
    for r in records:
        if r[field] == value:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def compute_stats(records):
    total = len(records)
    coin_wins = sum(r["coin_win"] for r in records)
    first_count = sum(r["went_first"] for r in records)
    duel_wins = sum(r["duel_win"] for r in records)
    return {
        "total": total,
        "coin_wins": coin_wins,
        "coin_losses": total - coin_wins,
        "coin_win_rate": coin_wins / total if total else 0.0,
        "first_count": first_count,
        "second_count": total - first_count,
        "first_share": first_count / total if total else 0.0,
        "duel_wins": duel_wins,
        "duel_losses": total - duel_wins,
        "duel_win_rate": duel_wins / total if total else 0.0,
        "coin_streak": current_streak(records, "coin_win"),
        "coin_longest_win": longest_streak(records, "coin_win", 1),
        "coin_longest_loss": longest_streak(records, "coin_win", 0),
        "duel_streak": current_streak(records, "duel_win"),
        "duel_longest_win": longest_streak(records, "duel_win", 1),
        "duel_longest_loss": longest_streak(records, "duel_win", 0),
    }
```

- [ ] **Step 4: Run tests and make sure they pass**

Run: `python -m unittest tests.test_stats -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add stats.py tests/test_stats.py
git commit -m "Add stats module with streak and rate computation

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: Charts module (matplotlib figures)

**Files:**
- Create: `charts.py`
- Create: `tests/test_charts.py`

**Interfaces:**
- Consumes: daily counts dicts from `Storage.get_daily_counts()` (keys `date`, `total`, `coin_wins`).
- Produces: `build_figures(daily_counts: list[dict]) -> list[Figure]` — `[rate_figure, counts_figure]`; empty input returns two placeholder figures.

- [ ] **Step 1: Install matplotlib**

Run: `pip install matplotlib`

- [ ] **Step 2: Write the failing test**

```python
# tests/test_charts.py
import unittest

from matplotlib.figure import Figure

from charts import build_figures


class ChartsTest(unittest.TestCase):
    def test_empty_returns_placeholder_figures(self):
        figures = build_figures([])
        self.assertEqual(len(figures), 2)
        for fig in figures:
            self.assertIsInstance(fig, Figure)

    def test_with_data_returns_figures(self):
        daily = [
            {"date": "2026-10-05", "total": 3, "coin_wins": 2},
            {"date": "2026-10-06", "total": 4, "coin_wins": 1},
        ]
        figures = build_figures(daily)
        self.assertEqual(len(figures), 2)
        for fig in figures:
            self.assertIsInstance(fig, Figure)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m unittest tests.test_charts -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'charts'`

- [ ] **Step 4: Write minimal implementation**

```python
# charts.py
from matplotlib.figure import Figure


def build_figures(daily_counts):
    rate_fig = Figure(figsize=(8, 4))
    counts_fig = Figure(figsize=(8, 4))
    rate_ax = rate_fig.subplots()
    counts_ax = counts_fig.subplots()

    if not daily_counts:
        for ax in (rate_ax, counts_ax):
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
            ax.axis("off")
        return [rate_fig, counts_fig]

    dates = [d["date"] for d in daily_counts]
    rates = [d["coin_wins"] / d["total"] * 100 for d in daily_counts]
    totals = [d["total"] for d in daily_counts]

    rate_ax.plot(dates, rates, marker="o")
    rate_ax.axhline(50, linestyle="--", color="gray")
    rate_ax.set_ylabel("Coin win rate (%)")
    rate_ax.set_title("Daily coin win rate")

    counts_ax.bar(dates, totals)
    counts_ax.set_ylabel("Duels")
    counts_ax.set_title("Duels per day")

    return [rate_fig, counts_fig]
```

- [ ] **Step 5: Run tests and make sure they pass**

Run: `python -m unittest tests.test_charts -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add charts.py tests/test_charts.py
git commit -m "Add charts module generating daily trend figures

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: UI, entry point, and README

**Files:**
- Create: `ui.py`
- Create: `main.py`
- Create: `tests/test_ui.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `Storage` methods from Task 1, `compute_stats` from Task 2, `build_figures` from Task 3.
- Produces: `TrackerApp(storage, root=None)` class with `select(field, value)`, `can_save() -> bool`, `save() -> int | None`, `refresh()`; `main()` entry point accepting `--db` (default `data/duels.db`).

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_ui -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui'`

- [ ] **Step 3: Write `ui.py`**

```python
# ui.py
import tkinter as tk
from datetime import datetime

from stats import compute_stats

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from charts import build_figures
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

OPTIONS = [
    ("coin_win", "硬币", [("赢", 1), ("输", 0)]),
    ("went_first", "先后手", [("先手", 1), ("后手", 0)]),
    ("duel_win", "决斗", [("胜", 1), ("负", 0)]),
]

SHORTCUTS = {
    "1": ("coin_win", 1),
    "2": ("coin_win", 0),
    "3": ("went_first", 1),
    "4": ("went_first", 0),
    "5": ("duel_win", 1),
    "6": ("duel_win", 0),
}


def format_stats(stats, label):
    return (
        f"{label}: {stats['total']} 局 | "
        f"硬币 {stats['coin_wins']}赢/{stats['coin_losses']}输 "
        f"({stats['coin_win_rate']:.1%}) 连串 {stats['coin_streak']} "
        f"(最长 {stats['coin_longest_win']}/{stats['coin_longest_loss']}) | "
        f"先手 {stats['first_count']} ({stats['first_share']:.1%}) | "
        f"决斗 {stats['duel_wins']}胜/{stats['duel_losses']}负 "
        f"({stats['duel_win_rate']:.1%}) 连串 {stats['duel_streak']}"
    )


class TrackerApp:
    def __init__(self, storage, root=None):
        self.storage = storage
        self.root = root if root is not None else tk.Tk()
        self.root.title("CoinFlipTracker")
        self.selections = {"coin_win": None, "went_first": None, "duel_win": None}
        self._buttons = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", padx=10, pady=10)

        for field, label, choices in OPTIONS:
            group = tk.Frame(input_frame)
            group.pack(side="left", padx=8)
            tk.Label(group, text=label).pack()
            buttons = {}
            for text, value in choices:
                btn = tk.Button(
                    group, text=text,
                    command=lambda f=field, v=value: self.select(f, v),
                )
                btn.pack(side="left")
                buttons[value] = btn
            self._buttons[field] = buttons

        self.save_btn = tk.Button(input_frame, text="保存 (Enter)", state="disabled")
        self.save_btn.pack(side="right")

        stats_frame = tk.Frame(self.root)
        stats_frame.pack(fill="x", padx=10)
        self.today_label = tk.Label(stats_frame, anchor="w")
        self.total_label = tk.Label(stats_frame, anchor="w")
        self.today_label.pack()
        self.total_label.pack()

        self.notebook = tk.Notebook(self.root)
        self.notebook.pack(fill="both", padx=10, pady=10)

        if MATPLOTLIB_OK:
            self.canvases = []
            for title in ("硬币胜率趋势", "每日对数"):
                tab = tk.Frame(self.notebook)
                self.notebook.add(tab, text=title)
                canvas = FigureCanvasTkAgg(None, master=tab)
                canvas.get_tk_widget().pack(fill="both")
                self.canvases.append(canvas)
        else:
            tab = tk.Frame(self.notebook)
            self.notebook.add(tab, text="图表")
            tk.Label(tab, text="matplotlib 未安装，图表不可用（pip install matplotlib）").pack()

        for key, (field, value) in SHORTCUTS.items():
            self.root.bind(key, lambda e, f=field, v=value: self.select(f, v))
        self.root.bind("<Return>", lambda e: self.save())

    def select(self, field, value):
        self.selections[field] = value
        for v, btn in self._buttons[field].items():
            btn.config(bg="lightyellow" if v == value else "systemButtonFace")
        self.save_btn.config(state="normal" if self.can_save() else "disabled")

    def can_save(self):
        return all(v is not None for v in self.selections.values())

    def save(self):
        if not self.can_save():
            return None
        rid = self.storage.insert_duel(
            self.selections["coin_win"],
            self.selections["went_first"],
            self.selections["duel_win"],
        )
        self.selections = {k: None for k in self.selections}
        for buttons in self._buttons.values():
            for btn in buttons.values():
                btn.config(bg="systemButtonFace")
        self.save_btn.config(state="disabled")
        self.refresh()
        return rid

    def refresh(self):
        today = datetime.now().strftime("%Y-%m-%d")
        all_records = self.storage.get_all()
        today_records = self.storage.get_by_date(today)
        self.today_label.config(text=format_stats(compute_stats(today_records), "当天"))
        self.total_label.config(text=format_stats(compute_stats(all_records), "累计"))
        if MATPLOTLIB_OK:
            figures = build_figures(self.storage.get_daily_counts())
            for canvas, fig in zip(self.canvases, figures):
                canvas.figure = fig
                canvas.draw()
```

- [ ] **Step 4: Write `main.py`**

```python
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
    app.root.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests and make sure they pass**

Run: `python -m unittest discover -s tests -v`
Expected: PASS (all tests from Tasks 1–4)

- [ ] **Step 6: Manual smoke test**

Run: `python main.py`
Verify: window opens; click 赢/先手/胜 → save button enables → save → stats update; keyboard 1/3/5/Enter works; chart tabs show "No data yet" then update after saves; close window cleanly.

- [ ] **Step 7: Write `README.md`**

```markdown
# CoinFlipTracker

游戏王 Master Duel 硬币/先后手/决斗胜负统计工具（手动录入，长期记录当天与累计）。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 录入

- 点击三组按钮：硬币（赢/输）、先后手（先手/后手）、决斗（胜/负），按 Enter 或"保存"。
- 快捷键：1/2 硬币赢/输，3/4 先手/后手，5/6 决斗胜/负，Enter 保存。

## 数据

- SQLite 数据库默认位于 `data/duels.db`，可用 `--db` 指定路径。
- 统计：当天与累计的硬币胜率、先手占比、决斗胜率、连串（当前/最长）。
- 图表标签页：按日硬币胜率趋势与每日对数。

## 测试

```bash
python -m unittest discover -s tests -v
```
```

- [ ] **Step 8: Commit**

```bash
git add ui.py main.py tests/test_ui.py README.md
git commit -m "Add tkinter UI, entry point, and README

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Plan Self-Review Notes

- Spec coverage: storage (Task 1), stats incl. streaks (Task 2), charts (Task 3), UI/shortcuts/error handling/README (Task 4); acceptance criteria 1–4 covered by tests + manual smoke test.
- Type consistency: `Storage.insert_duel` signature used identically in Tasks 1, 4; `build_figures` returns list of 2 Figures used by `TrackerApp.refresh`; `compute_stats` keys used by `format_stats`.
- Review Focus items each have a test: incomplete input (Task 4), empty DB (Tasks 2/3/4), streak edges (Task 2), date grouping (Task 1), matplotlib-missing (guarded import in Task 4, manual check).
