# ui.py
import tkinter as tk
from tkinter import ttk
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

        self.notebook = ttk.Notebook(self.root)
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
