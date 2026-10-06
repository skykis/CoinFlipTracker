# ui.py
import sqlite3
import tkinter as tk
from tkinter import ttk
from datetime import datetime

import theme
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

SHORTCUTS = {
    "1": ("coin_win", 1),
    "2": ("coin_win", 0),
    "3": ("went_first", 1),
    "4": ("went_first", 0),
    "5": ("duel_win", 1),
    "6": ("duel_win", 0),
}

# 按钮上印出快捷键，用户不需要记
SHORTCUT_KEYS = {(field, value): key for key, (field, value) in SHORTCUTS.items()}

METRICS = (
    ("total", "局数"),
    ("coin", "硬币胜率"),
    ("coin_streak", "硬币连串"),
    ("first", "先手占比"),
    ("duel", "决斗胜率"),
    ("duel_streak", "决斗连串"),
)

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

# 录入区与编辑面板共用同一列结构：0..5 六个等宽按钮列，然后日期/备注/动作
BUTTON_COLS = 6
DATE_COL = 6
NOTE_COL = 7
ACTION_COL = 8


def format_metrics(stats: dict, label: str, records: list[dict]) -> dict[str, tuple[str, str]]:
    def streak_text(n: int, last_value: int) -> str:
        if n == 0:
            return "—"
        return f"{n}{'赢' if last_value else '输'}"

    coin_dir = records[-1]["coin_win"] if records else 0
    duel_dir = records[-1]["duel_win"] if records else 0
    return {
        "total": (str(stats["total"]), label),
        "coin": (f"{stats['coin_win_rate']:.1%}", f"{stats['coin_wins']}赢/{stats['coin_losses']}输"),
        "coin_streak": (
            streak_text(stats["coin_streak"], coin_dir),
            f"最长 {stats['coin_longest_win']}/{stats['coin_longest_loss']}",
        ),
        "first": (
            f"{stats['first_share']:.1%}",
            f"先手 {stats['first_count']} / 后手 {stats['second_count']}",
        ),
        "duel": (f"{stats['duel_win_rate']:.1%}", f"{stats['duel_wins']}胜/{stats['duel_losses']}负"),
        "duel_streak": (
            streak_text(stats["duel_streak"], duel_dir),
            f"最长 {stats['duel_longest_win']}/{stats['duel_longest_loss']}",
        ),
    }


class TrackerApp:
    def __init__(self, storage: Storage, root: tk.Tk | None = None):
        self.storage = storage
        self.root = root if root is not None else tk.Tk()
        self.root.title("CoinFlipTracker")
        self.style = theme.apply_style(self.root)
        self.selections = {"coin_win": None, "went_first": None, "duel_win": None}
        self._buttons = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.root.geometry("900x640")
        self.root.minsize(820, 560)

        root_frame = ttk.Frame(self.root, style="Root.TFrame")
        root_frame.pack(fill="both", expand=True, padx=14, pady=14)
        root_frame.grid_columnconfigure(0, weight=1)
        root_frame.grid_rowconfigure(4, weight=1)

        header = ttk.Frame(root_frame, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text="CoinFlipTracker", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", padx=14, pady=10
        )
        ttk.Label(header, text=datetime.now().strftime("%Y-%m-%d"), style="Subtle.TLabel").grid(
            row=0, column=1, sticky="e", padx=14, pady=10
        )

        entry = ttk.Frame(root_frame, style="Card.TFrame")
        entry.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        # uniform 让六个按钮列等宽 —— 行列对齐靠它，而不是逐个写死宽度
        for col in range(BUTTON_COLS):
            entry.grid_columnconfigure(col, uniform="btn", minsize=78)
        entry.grid_columnconfigure(DATE_COL, minsize=110)
        entry.grid_columnconfigure(NOTE_COL, minsize=170, weight=1)
        entry.grid_columnconfigure(ACTION_COL, minsize=90)
        entry.grid_columnconfigure(ACTION_COL + 1, minsize=90)

        col = 0
        for field, label, choices in OPTIONS:
            self._buttons[field] = self._make_choice_group(
                entry, field, label, choices, self.selections,
                start_col=col, on_change=self._update_save_state,
            )
            col += 2

        ttk.Label(entry, text="日期", style="Section.TLabel").grid(
            row=0, column=DATE_COL, sticky="w", padx=4, pady=(10, 4)
        )
        self.date_entry = ttk.Entry(entry, width=12)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=1, column=DATE_COL, sticky="ew", padx=4, pady=(0, 12))

        self.note_label = ttk.Label(entry, text="备注（可选）", style="Section.TLabel")
        self.note_label.grid(row=0, column=NOTE_COL, sticky="w", padx=4, pady=(10, 4))
        self.note_entry = ttk.Entry(entry, width=22)
        self.note_entry.grid(row=1, column=NOTE_COL, sticky="ew", padx=4, pady=(0, 12))

        self.save_btn = ttk.Button(
            entry, text="保存", style="Primary.TButton", command=self.save, state="disabled"
        )
        self.save_btn.grid(row=1, column=ACTION_COL, sticky="ew", padx=4, pady=(0, 12))
        self.undo_btn = ttk.Button(
            entry, text="撤销上一条", style="Ghost.TButton", command=self.undo_last
        )
        self.undo_btn.grid(row=1, column=ACTION_COL + 1, sticky="ew", padx=(0, 10), pady=(0, 12))

        stats = ttk.Frame(root_frame, style="Card.TFrame")
        stats.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        for i in range(len(METRICS)):
            stats.grid_columnconfigure(i, uniform="metric", minsize=112)
        self.today_values, self.today_details = self._make_stats_section(stats, 0, "当天")
        ttk.Separator(stats, orient="horizontal").grid(
            row=4, column=0, columnspan=len(METRICS), sticky="ew", padx=14, pady=6
        )
        self.total_values, self.total_details = self._make_stats_section(stats, 5, "累计")

        self.message_label = ttk.Label(root_frame, text="", style="Status.TLabel")
        self.message_label.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        self.notebook = ttk.Notebook(root_frame)
        self.notebook.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

        if MATPLOTLIB_OK:
            self.canvases = []
            self.figures = []
            for title, _ in CHARTS:
                tab = ttk.Frame(self.notebook, style="Card.TFrame")
                self.notebook.add(tab, text=title)
                fig = Figure(figsize=(8, 4))
                canvas = FigureCanvasTkAgg(fig, master=tab)
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
                self.figures.append(fig)
                self.canvases.append(canvas)
        else:
            tab = ttk.Frame(self.notebook, style="Card.TFrame")
            self.notebook.add(tab, text="图表")
            self.fallback_label = ttk.Label(
                tab, text="matplotlib 未安装，图表不可用（pip install matplotlib）"
            )
            self.fallback_label.pack(padx=12, pady=12)

        self.list_tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(self.list_tab, text="记录列表")

        filter_frame = ttk.Frame(self.list_tab, style="Card.TFrame")
        filter_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        filter_frame.grid_columnconfigure(2, weight=1)
        ttk.Label(filter_frame, text="日期筛选", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.filter_combo = ttk.Combobox(filter_frame, state="readonly", values=["全部"])
        self.filter_combo.set("全部")
        self.filter_combo.grid(row=0, column=1, sticky="w", padx=8)
        self.list_count_label = ttk.Label(filter_frame, text="共 0 条", style="Subtle.TLabel")
        self.list_count_label.grid(row=0, column=2, sticky="w", padx=8)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._load_records())

        # Treeview 不会自带滚动条，长期累计的几百行会被裁掉
        self.record_scrollbar = ttk.Scrollbar(self.list_tab, orient="vertical")
        self.record_table = ttk.Treeview(
            self.list_tab,
            columns=[c for c, _, _ in COLUMNS],
            show="headings",
            yscrollcommand=self.record_scrollbar.set,
        )
        self.record_table.tag_configure("oddrow", background=theme.ROW_ALT)
        for col, heading, width in COLUMNS:
            self.record_table.heading(col, text=heading)
            self.record_table.column(col, width=width)
        self.record_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10))
        self.record_table.grid(row=1, column=0, sticky="nsew", padx=10)
        self.list_tab.grid_rowconfigure(1, weight=1)
        self.list_tab.grid_columnconfigure(0, weight=1)
        self.record_table.bind("<<TreeviewSelect>>", lambda e: self._on_row_select())

        edit_frame = ttk.Frame(self.list_tab, style="Card.TFrame")
        edit_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        for col in range(BUTTON_COLS):
            edit_frame.grid_columnconfigure(col, uniform="editbtn", minsize=78)
        edit_frame.grid_columnconfigure(NOTE_COL, minsize=170, weight=1)
        edit_frame.grid_columnconfigure(DATE_COL, minsize=110)
        for col in range(ACTION_COL, ACTION_COL + 3):
            edit_frame.grid_columnconfigure(col, minsize=80)

        self.edit_selections = {"coin_win": None, "went_first": None, "duel_win": None}
        self._edit_buttons = {}
        col = 0
        for field, label, choices in OPTIONS:
            self._edit_buttons[field] = self._make_choice_group(
                edit_frame, field, label, choices, self.edit_selections, start_col=col
            )
            col += 2

        ttk.Label(edit_frame, text="备注", style="Section.TLabel").grid(
            row=0, column=NOTE_COL, sticky="w", padx=4, pady=(10, 4)
        )
        self.edit_note = ttk.Entry(edit_frame, width=22)
        self.edit_note.grid(row=1, column=NOTE_COL, sticky="ew", padx=4, pady=(0, 10))
        ttk.Label(edit_frame, text="日期", style="Section.TLabel").grid(
            row=0, column=DATE_COL, sticky="w", padx=4, pady=(10, 4)
        )
        self.edit_date = ttk.Entry(edit_frame, width=12)
        self.edit_date.grid(row=1, column=DATE_COL, sticky="ew", padx=4, pady=(0, 10))
        self.update_btn = ttk.Button(
            edit_frame, text="更新", style="Primary.TButton",
            command=self.update_selected, state="disabled",
        )
        self.update_btn.grid(row=1, column=ACTION_COL, sticky="ew", padx=4, pady=(0, 10))
        self.delete_btn = ttk.Button(
            edit_frame, text="删除", style="Danger.TButton",
            command=self.delete_selected, state="disabled",
        )
        self.delete_btn.grid(row=1, column=ACTION_COL + 1, sticky="ew", padx=4, pady=(0, 10))
        self.cancel_btn = ttk.Button(
            edit_frame, text="取消", style="Ghost.TButton", command=self.clear_edit
        )
        self.cancel_btn.grid(row=1, column=ACTION_COL + 2, sticky="ew", padx=(0, 10), pady=(0, 10))

        self.selected_id = None
        self._records_by_id = {}

        for key, (field, value) in SHORTCUTS.items():
            self.root.bind(key, lambda e, f=field, v=value: self._shortcut(f, v))
        self.root.bind("<Return>", lambda e: self._on_return())
        self.root.bind("<Control-z>", lambda e: self._undo_by_shortcut())

    def _make_choice_group(self, parent, field, label, choices, store, start_col=0, on_change=None):
        ttk.Label(parent, text=label, style="Section.TLabel").grid(
            row=0, column=start_col, columnspan=2, sticky="w", padx=4, pady=(10, 4)
        )
        buttons = {}
        for i, (text, value) in enumerate(choices):
            key = SHORTCUT_KEYS[(field, value)]
            btn = ttk.Button(
                parent,
                text=f"{text} {key}",
                style="Choice.TButton",
                command=lambda f=field, v=value, s=store, b=buttons, c=on_change: self._choose(
                    f, v, s, b, c
                ),
            )
            btn.grid(row=1, column=start_col + i, sticky="ew", padx=4, pady=(0, 12))
            buttons[value] = btn
        return buttons

    def _make_stats_section(self, parent, row, title):
        ttk.Label(parent, text=title, style="Section.TLabel").grid(
            row=row, column=0, columnspan=len(METRICS), sticky="w", padx=14, pady=(10, 2)
        )
        values, details = {}, {}
        for i, (key, name) in enumerate(METRICS):
            ttk.Label(parent, text=name, style="Subtle.TLabel").grid(
                row=row + 1, column=i, sticky="w", padx=14
            )
            value_label = ttk.Label(parent, text="—", style="Metric.TLabel")
            value_label.grid(row=row + 2, column=i, sticky="w", padx=14)
            detail_label = ttk.Label(parent, text="", style="MetricDetail.TLabel")
            detail_label.grid(row=row + 3, column=i, sticky="w", padx=14, pady=(0, 10))
            values[key] = value_label
            details[key] = detail_label
        return values, details

    def run(self) -> None:
        try:
            self.root.mainloop()
        finally:
            try:
                self.root.destroy()
            except tk.TclError:
                pass  # window was already closed by the user

    def _choose(self, field, value, store, buttons, on_change=None):
        store[field] = value
        for v, btn in buttons.items():
            btn.config(style="Selected.TButton" if v == value else "Choice.TButton")
        if on_change is not None:
            on_change()

    def _update_save_state(self) -> None:
        self.save_btn.config(state="normal" if self.can_save() else "disabled")

    def select(self, field: str, value: int) -> None:
        self._choose(field, value, self.selections, self._buttons[field], self._update_save_state)

    def can_save(self) -> bool:
        return all(v is not None for v in self.selections.values())

    def _entry_has_focus(self) -> bool:
        return isinstance(self.root.focus_get(), (tk.Entry, ttk.Entry))

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

    def show_message(self, text: str, kind: str = "info") -> None:
        style = {"success": "Success.TLabel", "error": "Error.TLabel"}.get(kind, "Status.TLabel")
        self.message_label.config(text=text, style=style)

    def _reset_button_styles(self, buttons_by_field) -> None:
        for buttons in buttons_by_field.values():
            for btn in buttons.values():
                btn.config(style="Choice.TButton")

    def _undo_by_shortcut(self) -> None:
        # 焦点在文本框时 Ctrl+Z 是用户的"撤销打字"反射，不能删数据库记录
        if self._entry_has_focus():
            return
        self.undo_last()

    def undo_last(self) -> None:
        try:
            removed = self.storage.delete_last()
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}", kind="error")
            return
        if removed is None:
            self.show_message("没有可撤销的记录", kind="error")
        else:
            self.show_message(f"已撤销记录 #{removed}", kind="success")
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
            self.show_message("日期格式应为 YYYY-MM-DD", kind="error")
            return None
        except ValueError as e:
            self.show_message(f"操作失败：{e}", kind="error")
            return None
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}", kind="error")
            return None
        self.note_entry.delete(0, "end")
        # 原地重置 —— 按钮闭包捕获的是同一个 dict 对象，替换对象会让点击失效
        for key in self.selections:
            self.selections[key] = None
        self._reset_button_styles(self._buttons)
        self.save_btn.config(state="disabled")
        self.show_message(f"已保存记录 #{rid}", kind="success")
        self.refresh()
        return rid

    def _load_records(self) -> None:
        chosen = self.filter_combo.get()
        date = None if chosen == "全部" else chosen
        records = self.storage.get_records(date)
        self.record_table.delete(*self.record_table.get_children())
        for i, r in enumerate(records):
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
                tags=("oddrow",) if i % 2 else (),
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
        for key in self.edit_selections:
            self.edit_selections[key] = None
        self._reset_button_styles(self._edit_buttons)
        self.edit_note.delete(0, "end")
        self.edit_date.delete(0, "end")
        self.update_btn.config(state="disabled")
        self.delete_btn.config(state="disabled")

    def update_selected(self) -> None:
        if self.selected_id is None:
            return
        if not all(v is not None for v in self.edit_selections.values()):
            self.show_message("请先选择硬币/先后手/决斗", kind="error")
            return
        date = self.edit_date.get().strip()
        if not date:
            # 编辑面板的日期已预填，留空是用户主动清空 —— 不能像录入区那样默认当天
            self.show_message("日期不能留空（格式 YYYY-MM-DD）", kind="error")
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
            self.show_message("日期格式应为 YYYY-MM-DD", kind="error")
            return
        except ValueError as e:
            self.show_message(f"操作失败：{e}", kind="error")
            return
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}", kind="error")
            return
        if ok:
            self.show_message(f"已更新记录 #{self.selected_id}", kind="success")
            self.refresh()
            if str(self.selected_id) in self._records_by_id:
                self.record_table.selection_set(str(self.selected_id))
        else:
            self.show_message("该记录已不存在", kind="error")
            self.clear_edit()
            self.refresh()

    def delete_selected(self) -> None:
        if self.selected_id is None:
            return
        removed_id = self.selected_id
        try:
            ok = self.storage.delete_duel(removed_id)
        except sqlite3.Error as e:
            self.show_message(f"数据库操作失败：{e}", kind="error")
            return
        self.show_message(
            f"已删除记录 #{removed_id}" if ok else "该记录已不存在",
            kind="success" if ok else "error",
        )
        self.clear_edit()
        self.refresh()

    def refresh(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        all_records = self.storage.get_all()
        today_records = self.storage.get_by_date(today)
        today_metrics = format_metrics(compute_stats(today_records), "当天", today_records)
        total_metrics = format_metrics(compute_stats(all_records), "累计", all_records)
        for key, label in self.today_values.items():
            label.config(text=today_metrics[key][0])
        for key, label in self.today_details.items():
            label.config(text=today_metrics[key][1])
        for key, label in self.total_values.items():
            label.config(text=total_metrics[key][0])
        for key, label in self.total_details.items():
            label.config(text=total_metrics[key][1])
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
