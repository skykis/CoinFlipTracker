# ui.py
import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from stats import compute_stats
from storage import InvalidDateError, Storage

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

COLUMNS = (
    ("date", "日期", 90),
    ("time", "时间", 60),
    ("coin", "硬币", 60),
    ("first", "先后手", 70),
    ("duel", "决斗", 60),
    ("note", "备注", 160),
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
        # 平台默认按钮背景，取一次即可 —— 高亮后还原用它
        probe = tk.Button(self.root)
        self._default_bg = probe.cget("bg")
        probe.destroy()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill="x", padx=10, pady=10)

        for field, label, choices in OPTIONS:
            self._buttons[field] = self._make_choice_group(
                input_frame, field, label, choices, self.selections,
                on_change=self._update_save_state,
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

        self.list_tab = tk.Frame(self.notebook)
        self.notebook.add(self.list_tab, text="记录列表")

        filter_frame = tk.Frame(self.list_tab)
        filter_frame.pack(fill="x", padx=6, pady=6)
        tk.Label(filter_frame, text="日期筛选").pack(side="left")
        self.filter_combo = ttk.Combobox(filter_frame, state="readonly", values=["全部"])
        self.filter_combo.set("全部")
        self.filter_combo.pack(side="left")
        self.list_count_label = tk.Label(filter_frame, text="共 0 条")
        self.list_count_label.pack(side="left", padx=8)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._load_records())

        # Treeview 不会自带滚动条，长期累计的几百行会被裁掉
        self.record_scrollbar = ttk.Scrollbar(self.list_tab, orient="vertical")
        self.record_table = ttk.Treeview(
            self.list_tab,
            columns=[c for c, _, _ in COLUMNS],
            show="headings",
            yscrollcommand=self.record_scrollbar.set,
        )
        for col, heading, width in COLUMNS:
            self.record_table.heading(col, text=heading)
            self.record_table.column(col, width=width)
        self.record_scrollbar.pack(side="right", fill="y")
        self.record_table.pack(fill="both", padx=6)
        self.record_table.bind("<<TreeviewSelect>>", lambda e: self._on_row_select())

        self.edit_frame = tk.Frame(self.list_tab)
        self.edit_frame.pack(fill="x", padx=6, pady=6)
        self.edit_selections = {"coin_win": None, "went_first": None, "duel_win": None}
        self._edit_buttons = {}
        for field, label, choices in OPTIONS:
            self._edit_buttons[field] = self._make_choice_group(
                self.edit_frame, field, label, choices, self.edit_selections
            )
        self.edit_note = tk.Entry(self.edit_frame, width=20)
        self.edit_note.pack(side="left")
        self.edit_date = tk.Entry(self.edit_frame, width=10)
        self.edit_date.pack(side="left")
        self.update_btn = tk.Button(
            self.edit_frame, text="更新", command=self.update_selected, state="disabled"
        )
        self.update_btn.pack(side="left")
        self.delete_btn = tk.Button(
            self.edit_frame, text="删除", command=self.delete_selected, state="disabled"
        )
        self.delete_btn.pack(side="left")
        self.cancel_btn = tk.Button(self.edit_frame, text="取消", command=self.clear_edit)
        self.cancel_btn.pack(side="left")
        self.selected_id = None
        self._records_by_id = {}

        for key, (field, value) in SHORTCUTS.items():
            self.root.bind(key, lambda e, f=field, v=value: self._shortcut(f, v))
        self.root.bind("<Return>", lambda e: self._on_return())
        self.root.bind("<Control-z>", lambda e: self._undo_by_shortcut())

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass  # window was already closed by the user

    def _make_choice_group(self, parent, field, label, choices, store, on_change=None):
        group = tk.Frame(parent)
        group.pack(side="left", padx=8)
        tk.Label(group, text=label).pack()
        buttons = {}
        for text, value in choices:
            btn = tk.Button(
                group, text=text,
                command=lambda f=field, v=value, s=store, b=buttons, c=on_change: self._choose(f, v, s, b, c),
            )
            btn.pack(side="left")
            buttons[value] = btn
        return buttons

    def _choose(self, field, value, store, buttons, on_change=None):
        store[field] = value
        for v, btn in buttons.items():
            btn.config(bg=HIGHLIGHT_BG if v == value else self._default_bg)
        if on_change is not None:
            on_change()

    def _update_save_state(self) -> None:
        self.save_btn.config(state="normal" if self.can_save() else "disabled")

    def select(self, field: str, value: int) -> None:
        self._choose(field, value, self.selections, self._buttons[field], self._update_save_state)

    def can_save(self) -> bool:
        return all(v is not None for v in self.selections.values())

    def _entry_has_focus(self) -> bool:
        return isinstance(self.root.focus_get(), tk.Entry)

    def _shortcut(self, field: str, value: int) -> None:
        if self._entry_has_focus():
            return
        self.select(field, value)

    def _on_return(self) -> None:
        # ttk.Notebook has no current(); select() with no args returns the raised tab
        if self.notebook.index(self.notebook.select()) == self.notebook.index(self.list_tab):
            # 列表标签页里 Enter 不保存录入区；若编辑面板已打开，则写回选中记录
            if self.selected_id is not None:
                self.update_selected()
            return
        self.save()

    def show_message(self, text: str) -> None:
        self.message_label.config(text=text)

    def _undo_by_shortcut(self) -> None:
        # 焦点在文本框时 Ctrl+Z 是用户的"撤销打字"反射，不能删数据库记录
        if self._entry_has_focus():
            return
        self.undo_last()

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
        except InvalidDateError:
            self.show_message("日期格式应为 YYYY-MM-DD")
            return None
        except ValueError as e:
            self.show_message(f"操作失败：{e}")
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

    def _load_records(self) -> None:
        chosen = self.filter_combo.get()
        date = None if chosen == "全部" else chosen
        records = self.storage.get_records(date)
        self.record_table.delete(*self.record_table.get_children())
        for r in records:
            self.record_table.insert(
                "", "end", iid=str(r["id"]),
                values=(
                    r["date"],
                    r["created_at"][11:16],
                    "赢" if r["coin_win"] else "输",
                    "先手" if r["went_first"] else "后手",
                    "胜" if r["duel_win"] else "负",
                    r["note"] or "",
                ),
            )
        self._records_by_id = {str(r["id"]): r for r in records}
        self.list_count_label.config(text=f"共 {len(records)} 条")
        if self.selected_id is not None and str(self.selected_id) not in self._records_by_id:
            self.clear_edit()

    def _on_row_select(self) -> None:
        selected = self.record_table.selection()
        if not selected:
            return
        record = self._records_by_id.get(selected[0])
        if record is None:
            return
        self.selected_id = record["id"]
        for field in ("coin_win", "went_first", "duel_win"):
            self._choose(field, record[field], self.edit_selections, self._edit_buttons[field])
        self.edit_note.delete(0, "end")
        if record["note"]:
            self.edit_note.insert(0, record["note"])
        self.edit_date.delete(0, "end")
        self.edit_date.insert(0, record["date"])
        self.update_btn.config(state="normal")
        self.delete_btn.config(state="normal")

    def clear_edit(self) -> None:
        self.selected_id = None
        # 不清除表格选中，重新点击同一行不会触发 <<TreeviewSelect>>，面板无法重开
        self.record_table.selection_set()
        self.edit_selections = {k: None for k in ("coin_win", "went_first", "duel_win")}
        for buttons in self._edit_buttons.values():
            for btn in buttons.values():
                btn.config(bg=self._default_bg)
        self.edit_note.delete(0, "end")
        self.edit_date.delete(0, "end")
        self.update_btn.config(state="disabled")
        self.delete_btn.config(state="disabled")

    def update_selected(self) -> None:
        if self.selected_id is None:
            return
        if not all(v is not None for v in self.edit_selections.values()):
            self.show_message("请先选择硬币/先后手/决斗")
            return
        date = self.edit_date.get().strip()
        if not date:
            # 编辑面板的日期已预填，留空是用户主动清空 —— 不能像录入区那样默认当天
            self.show_message("日期不能留空（格式 YYYY-MM-DD）")
            return
        try:
            ok = self.storage.update_duel(
                self.selected_id,
                self.edit_selections["coin_win"],
                self.edit_selections["went_first"],
                self.edit_selections["duel_win"],
                self.edit_note.get().strip() or None,
                date,
            )
        except InvalidDateError:
            self.show_message("日期格式应为 YYYY-MM-DD")
            return
        except ValueError as e:
            self.show_message(f"操作失败：{e}")
            return
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}")
            return
        if ok:
            self.show_message(f"已更新记录 #{self.selected_id}")
            self.refresh()
            if str(self.selected_id) in self._records_by_id:
                self.record_table.selection_set(str(self.selected_id))
        else:
            self.show_message("该记录已不存在")
            self.clear_edit()
            self.refresh()

    def delete_selected(self) -> None:
        if self.selected_id is None:
            return
        removed_id = self.selected_id
        try:
            ok = self.storage.delete_duel(removed_id)
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}")
            return
        self.show_message(f"已删除记录 #{removed_id}" if ok else "该记录已不存在")
        self.clear_edit()
        self.refresh()

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

        dates = self.storage.get_dates()
        self.filter_combo["values"] = ["全部"] + dates
        if self.filter_combo.get() != "全部" and self.filter_combo.get() not in dates:
            self.filter_combo.set("全部")
        self._load_records()
