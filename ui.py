# ui.py
import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from stats import compute_stats
from storage import Storage

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from charts import draw_coin_rate, draw_daily_counts, draw_per_duel
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

OPTIONS = [
    ("coin_win", "硬币", [("赢", 1), ("输", 0)]),
    ("went_first", "先后手", [("先手", 1), ("后手", 0)]),
    ("duel_win", "决斗", [("胜", 1), ("负", 0)]),
]

# 每个标签页绑定一个固定的 Figure：TkAgg 会把 figure 尺寸调整为 canvas 尺寸，
# 若每次刷新都换成新 figure，渲染尺寸与 PhotoImage 不一致，旧图会残留。
CHARTS = (
    ("硬币胜率趋势", draw_coin_rate),
    ("每日对数", draw_daily_counts),
    ("逐局趋势", draw_per_duel),
)

HIGHLIGHT_BG = "lightyellow"

SHORTCUTS = {
    "1": ("coin_win", 1),
    "2": ("coin_win", 0),
    "3": ("went_first", 1),
    "4": ("went_first", 0),
    "5": ("duel_win", 1),
    "6": ("duel_win", 0),
}


def format_stats(stats: dict, label: str, records: list[dict]) -> str:
    def streak_text(n: int, last_value: int) -> str:
        if n == 0:
            return "连串 0"
        return f"连串 {n}{'赢' if last_value else '输'}"

    coin_dir = records[-1]["coin_win"] if records else 0
    duel_dir = records[-1]["duel_win"] if records else 0
    return (
        f"{label}: {stats['total']} 局 | "
        f"硬币 {stats['coin_wins']}赢/{stats['coin_losses']}输 "
        f"({stats['coin_win_rate']:.1%}) {streak_text(stats['coin_streak'], coin_dir)} "
        f"(最长 {stats['coin_longest_win']}/{stats['coin_longest_loss']}) | "
        f"先手 {stats['first_count']} ({stats['first_share']:.1%}) / 后手 {stats['second_count']} | "
        f"决斗 {stats['duel_wins']}胜/{stats['duel_losses']}负 "
        f"({stats['duel_win_rate']:.1%}) {streak_text(stats['duel_streak'], duel_dir)} "
        f"(最长 {stats['duel_longest_win']}/{stats['duel_longest_loss']})"
    )


class TrackerApp:
    def __init__(self, storage: Storage, root: tk.Tk | None = None):
        self.storage = storage
        self.root = root if root is not None else tk.Tk()
        self.root.title("CoinFlipTracker")
        self.selections = {"coin_win": None, "went_first": None, "duel_win": None}
        self._buttons = {}
        self._default_bg = ""
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", padx=10, pady=10)

        for field, label, choices in OPTIONS:
            self._buttons[field] = self._make_choice_group(
                input_frame, field, label, choices, self.selections
            )

        date_group = tk.Frame(input_frame)
        date_group.pack(side="left", padx=8)
        tk.Label(date_group, text="日期").pack()
        self.date_entry = tk.Entry(date_group, width=10)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side="left")

        self.note_label = tk.Label(input_frame, text="备注(可选)")
        self.note_label.pack(side="right")
        self.note_entry = tk.Entry(input_frame, width=20)
        self.note_entry.pack(side="right")
        self.save_btn = tk.Button(
            input_frame, text="保存 (Enter)", state="disabled", command=self.save
        )
        self.save_btn.pack(side="right")
        self.undo_btn = tk.Button(input_frame, text="撤销上一条", command=self.undo_last)
        self.undo_btn.pack(side="right")

        stats_frame = tk.Frame(self.root)
        stats_frame.pack(fill="x", padx=10)
        self.today_label = tk.Label(stats_frame, anchor="w")
        self.total_label = tk.Label(stats_frame, anchor="w")
        self.today_label.pack()
        self.total_label.pack()
        self.message_label = tk.Label(stats_frame, anchor="w", text="")
        self.message_label.pack()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", padx=10, pady=10)

        if MATPLOTLIB_OK:
            self.canvases = []
            self.figures = []
            for title, _ in CHARTS:
                tab = tk.Frame(self.notebook)
                self.notebook.add(tab, text=title)
                fig = Figure(figsize=(8, 4))
                canvas = FigureCanvasTkAgg(fig, master=tab)
                canvas.get_tk_widget().pack(fill="both")
                self.figures.append(fig)
                self.canvases.append(canvas)
        else:
            tab = tk.Frame(self.notebook)
            self.notebook.add(tab, text="图表")
            self.fallback_label = tk.Label(
                tab, text="matplotlib 未安装，图表不可用（pip install matplotlib）"
            )
            self.fallback_label.pack()

        for key, (field, value) in SHORTCUTS.items():
            self.root.bind(key, lambda e, f=field, v=value: self._shortcut(f, v))
        self.root.bind("<Return>", lambda e: self._on_return())

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass  # window was already closed by the user

    def _make_choice_group(self, parent, field, label, choices, store):
        group = tk.Frame(parent)
        group.pack(side="left", padx=8)
        tk.Label(group, text=label).pack()
        buttons = {}
        for text, value in choices:
            btn = tk.Button(
                group, text=text,
                command=lambda f=field, v=value, s=store, b=buttons: self._choose(f, v, s, b),
            )
            btn.pack(side="left")
            self._default_bg = btn.cget("bg")
            buttons[value] = btn
        return buttons

    def _choose(self, field, value, store, buttons):
        store[field] = value
        for v, btn in buttons.items():
            btn.config(bg=HIGHLIGHT_BG if v == value else self._default_bg)

    def select(self, field: str, value: int) -> None:
        self.selections[field] = value
        for v, btn in self._buttons[field].items():
            btn.config(bg=HIGHLIGHT_BG if v == value else self._default_bg)
        self.save_btn.config(state="normal" if self.can_save() else "disabled")

    def can_save(self) -> bool:
        return all(v is not None for v in self.selections.values())

    def _shortcut(self, field: str, value: int) -> None:
        if isinstance(self.root.focus_get(), tk.Entry):
            return
        self.select(field, value)

    def _on_return(self) -> None:
        self.save()

    def show_message(self, text: str) -> None:
        self.message_label.config(text=text)

    def undo_last(self) -> None:
        try:
            removed = self.storage.delete_last()
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}")
            return
        if removed is None:
            self.show_message("没有可撤销的记录")
        else:
            self.show_message(f"已撤销记录 #{removed}")
        self.refresh()

    def save(self) -> int | None:
        if not self.can_save():
            return None
        try:
            rid = self.storage.insert_duel(
                self.selections["coin_win"],
                self.selections["went_first"],
                self.selections["duel_win"],
                note=self.note_entry.get().strip() or None,
                date=self.date_entry.get().strip() or None,
            )
        except ValueError:
            self.show_message("日期格式应为 YYYY-MM-DD")
            return None
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}")
            return None
        self.note_entry.delete(0, "end")
        self.selections = {k: None for k in self.selections}
        for buttons in self._buttons.values():
            for btn in buttons.values():
                btn.config(bg=self._default_bg)
        self.save_btn.config(state="disabled")
        self.show_message("")
        self.refresh()
        return rid

    def refresh(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        all_records = self.storage.get_all()
        today_records = self.storage.get_by_date(today)
        self.today_label.config(
            text=format_stats(compute_stats(today_records), "当天", today_records)
        )
        self.total_label.config(
            text=format_stats(compute_stats(all_records), "累计", all_records)
        )
        if MATPLOTLIB_OK:
            daily_counts = self.storage.get_daily_counts()
            drawers = (
                (draw_coin_rate, daily_counts),
                (draw_daily_counts, daily_counts),
                (draw_per_duel, all_records),
            )
            for (drawer, data), canvas, fig in zip(drawers, self.canvases, self.figures):
                fig.clear()
                drawer(fig.subplots(), data)
                canvas.draw()
