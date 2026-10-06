# 记录纠错功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户撤销上一条录入、并在「记录列表」标签页里就地编辑/删除任意记录，使统计与真实对局一致。

**Architecture:** 沿用 `main.py → ui.py → storage.py → SQLite` 三层。`storage.py` 新增 update/delete/查询接口并集中日期校验（唯一权威）；`ui.py` 新增第 4 个标签页与录入区的两个控件；`stats.py` / `charts.py` 不变，因为它们只接收记录列表。

**Tech Stack:** Python 3.13、stdlib `sqlite3`（WAL）、`tkinter` / `tkinter.ttk`、`unittest`、matplotlib（图表部分不受影响）。

**Spec:** `docs/superpowers/specs/2026-10-06-record-correction-design.md`

## Global Constraints

- 不新增第三方依赖：只用 stdlib `sqlite3`、`tkinter`、`tkinter.ttk`、`datetime`。
- 数据库 schema 不变 —— 不做迁移，不新增列。
- 所有用户可见文案为中文（与现有 UI 一致）。
- 测试命令：`python -m unittest discover -s tests`；现有 37 个测试必须全部通过。
- 每个任务结束时提交一次，提交信息结尾 `Co-Authored-By: Claude Code <noreply@anthropic.com>`。
- 非法日期统一抛 `ValueError`；非法 flag 依赖 SQLite CHECK 约束抛 `sqlite3.IntegrityError`。

## Review Focus

这些是 spec 隐含但没有任务明确覆盖的输入/失败模式，每条都在对应任务里有测试：

1. **日期字段留空** —— 应视为当天，而不是报错。（Task 3）
2. **撤销时数据库为空** —— 应提示「没有可撤销的记录」，不崩溃。（Task 3）
3. **焦点在输入框内时按数字键** —— 现有实现会误改选择，输入 `2` 会写入非法值崩溃。（Task 3）
4. **筛选选中的日期因删除而消失** —— 下拉应回落到「全部」，列表不应显示幽灵行。（Task 5）
5. **编辑面板未选中任何行时点更新** —— 应无操作，不写库。（Task 5）

---

### Task 1: storage 查询与日期校验

**Files:**
- Modify: `storage.py`（新增 `_validate_date`、`get_records`、`get_dates`；改 `insert_duel`）
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: 现有 `Storage.insert_duel(coin_win, went_first, duel_win, note=None, date=None) -> int`、`get_all() -> list[dict]`
- Produces:
  - `_validate_date(value: str) -> str`（模块级函数，失败抛 `ValueError`）
  - `get_records(self, date: str | None = None) -> list[dict]`（按 `id` 倒序）
  - `get_dates(self) -> list[str]`（去重、倒序）

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_storage.py`（在 `test_daily_counts` 之后）：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_storage -v`
Expected: FAIL —— `AttributeError: 'Storage' object has no attribute 'get_records'`（以及 `get_dates`、非法日期未抛 ValueError）。

- [ ] **Step 3: 实现**

在 `storage.py` 的 `SCHEMA` 之后、`class Storage` 之前：

```python
def _validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"无效日期: {value!r}，应为 YYYY-MM-DD")
    return value
```

改 `insert_duel` 的开头（在 `now = datetime.now()` 之后）：

```python
        date = _validate_date(date) if date is not None else now.strftime("%Y-%m-%d")
```

并把 INSERT 语句里的 `date or now.strftime("%Y-%m-%d")` 换成 `date`。

在 `get_all` 之后新增：

```python
    def get_records(self, date: str | None = None) -> list[dict]:
        if date is None:
            rows = self.conn.execute("SELECT * FROM duels ORDER BY id DESC").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM duels WHERE date = ? ORDER BY id DESC", (date,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_dates(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT date FROM duels ORDER BY date DESC"
        ).fetchall()
        return [r["date"] for r in rows]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests`
Expected: `Ran 42 tests ... OK`

- [ ] **Step 5: 提交**

```bash
git add storage.py tests/test_storage.py
git commit -m "Add record query and date validation to storage

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: storage 更新、删除、撤销

**Files:**
- Modify: `storage.py`（新增 `update_duel`、`delete_duel`、`delete_last`）
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `_validate_date(value: str) -> str`（Task 1）
- Produces:
  - `update_duel(self, duel_id: int, coin_win: int, went_first: int, duel_win: int, note: str | None, date: str) -> bool`
  - `delete_duel(self, duel_id: int) -> bool`
  - `delete_last(self) -> int | None`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_storage.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_storage -v`
Expected: FAIL —— `AttributeError: 'Storage' object has no attribute 'update_duel'`

- [ ] **Step 3: 实现**

在 `storage.py` 的 `get_dates` 之后：

```python
    def update_duel(
        self,
        duel_id: int,
        coin_win: int,
        went_first: int,
        duel_win: int,
        note: str | None,
        date: str,
    ) -> bool:
        _validate_date(date)
        cur = self.conn.execute(
            "UPDATE duels SET date = ?, coin_win = ?, went_first = ?, duel_win = ?, note = ? "
            "WHERE id = ?",
            (date, int(coin_win), int(went_first), int(duel_win), note, duel_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete_duel(self, duel_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM duels WHERE id = ?", (duel_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_last(self) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM duels ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        self.conn.execute("DELETE FROM duels WHERE id = ?", (row["id"],))
        self.conn.commit()
        return row["id"]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests`
Expected: `Ran 48 tests ... OK`

- [ ] **Step 5: 提交**

```bash
git add storage.py tests/test_storage.py
git commit -m "Add update, delete and undo-last to storage

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: ui 录入区 —— 日期输入、撤销、提示、快捷键守卫

**Files:**
- Modify: `ui.py`（`_build_ui`、`save`、新增 `_make_choice_group`、`_choose`、`_shortcut`、`_on_return`、`undo_last`、`show_message`）
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `Storage.insert_duel(..., date=...)`、`Storage.delete_last() -> int | None`（Task 1/2）
- Produces:
  - `_make_choice_group(self, parent, field: str, label: str, choices: list[tuple[str, int]], store: dict) -> dict[int, tk.Button]`
  - `_choose(self, field: str, value: int, store: dict, buttons: dict) -> None`
  - `show_message(self, text: str) -> None`（写入 `self.message_label`）
  - `undo_last(self) -> None`
  - `self.date_entry`、`self.undo_btn`、`self.message_label`

- [ ] **Step 1: 写失败测试**

在 `tests/test_ui.py` 顶部补 `from datetime import datetime`，追加测试（放在 `test_stats_display_streak_direction_and_all_fields` 之前）：

```python
    def test_date_field_defaults_to_today(self):
        self.assertEqual(self.app.date_entry.get(), datetime.now().strftime("%Y-%m-%d"))

    def test_save_uses_specified_date(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.app.date_entry.delete(0, "end")
        self.app.date_entry.insert(0, "2026-10-01")
        self.app.save()
        self.assertEqual(self.storage.get_all()[0]["date"], "2026-10-01")

    def test_empty_date_field_defaults_to_today(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.app.date_entry.delete(0, "end")
        self.app.save()
        self.assertEqual(self.storage.get_all()[0]["date"], datetime.now().strftime("%Y-%m-%d"))

    def test_invalid_date_is_not_saved(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.app.date_entry.delete(0, "end")
        self.app.date_entry.insert(0, "2026/10/01")
        self.assertIsNone(self.app.save())
        self.assertEqual(len(self.storage.get_all()), 0)
        self.assertIn("YYYY-MM-DD", self.app.message_label.cget("text"))

    def test_blank_note_is_stored_as_none(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.app.note_entry.insert(0, "   ")
        self.app.save()
        self.assertIsNone(self.storage.get_all()[0]["note"])

    def test_undo_last_removes_newest_record(self):
        self.storage.insert_duel(1, 1, 1)
        self.storage.insert_duel(0, 0, 0)
        self.app.refresh()
        self.app.undo_last()
        self.assertEqual(len(self.storage.get_all()), 1)
        self.assertIn("撤销", self.app.message_label.cget("text"))

    def test_undo_with_no_records_reports_and_does_not_crash(self):
        self.app.undo_last()
        self.assertIn("没有可撤销", self.app.message_label.cget("text"))
        self.assertEqual(len(self.storage.get_all()), 0)

    def test_shortcut_ignored_when_entry_has_focus(self):
        self.app.note_entry.focus_set()
        self.app._shortcut("coin_win", 1)
        self.assertIsNone(self.app.selections["coin_win"])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_ui -v`
Expected: FAIL —— `AttributeError: 'TrackerApp' object has no attribute 'date_entry'` 等 8 条测试失败。

- [ ] **Step 3: 实现**

`ui.py` 顶部补 `import sqlite3`。

新增 `_make_choice_group` 与 `_choose`（放在 `select` 之前）：

```python
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
```

把 `_build_ui` 里手工创建三组按钮的循环替换为：

```python
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
```

在 `self.save_btn.pack(side="right")` 之后：

```python
        self.undo_btn = tk.Button(input_frame, text="撤销上一条", command=self.undo_last)
        self.undo_btn.pack(side="right")
```

在 `self.total_label.pack()` 之后：

```python
        self.message_label = tk.Label(stats_frame, anchor="w", text="")
        self.message_label.pack()
```

替换绑定部分：

```python
        for key, (field, value) in SHORTCUTS.items():
            self.root.bind(key, lambda e, f=field, v=value: self._shortcut(f, v))
        self.root.bind("<Return>", lambda e: self._on_return())
```

新增方法：

```python
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
```

改 `save`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests`
Expected: `Ran 56 tests ... OK`

- [ ] **Step 5: 提交**

```bash
git add ui.py tests/test_ui.py
git commit -m "Add date entry, undo-last, message line and shortcut focus guard

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: ui 记录列表标签页 —— 筛选、表格、选中填充编辑面板

**Files:**
- Modify: `ui.py`（新增 `COLUMNS` 常量、`_build_ui` 中的列表标签页、`_load_records`、`_on_row_select`、`clear_edit`；改 `refresh`、`_on_return`）
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `Storage.get_records(date=None) -> list[dict]`、`Storage.get_dates() -> list[str]`（Task 1）、`_make_choice_group`、`_choose`、`show_message`（Task 3）
- Produces:
  - `COLUMNS = (("date", "日期", 90), ("time", "时间", 60), ("coin", "硬币", 60), ("first", "先后手", 70), ("duel", "决斗", 60), ("note", "备注", 160))`
  - `self.list_tab`、`self.filter_combo`、`self.record_table`、`self.list_count_label`
  - `self.edit_selections: dict[str, int | None]`、`self._edit_buttons: dict[str, dict[int, tk.Button]]`、`self.edit_note`、`self.edit_date`、`self.selected_id: int | None`
  - `_load_records(self) -> None`、`_on_row_select(self) -> None`、`clear_edit(self) -> None`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_ui.py`：

```python
    def test_fourth_tab_is_record_list(self):
        self.assertEqual(self.app.notebook.tab(3, "text"), "记录列表")

    def test_list_shows_all_records_and_count(self):
        self.storage.insert_duel(1, 1, 1, note="first")
        self.storage.insert_duel(0, 0, 0, note="second")
        self.app.refresh()
        self.assertEqual(len(self.app.record_table.get_children()), 2)
        self.assertEqual(self.app.list_count_label.cget("text"), "共 2 条")

    def test_date_filter_limits_rows(self):
        self.storage.insert_duel(1, 1, 1, date="2026-10-05")
        self.storage.insert_duel(0, 0, 0, date="2026-10-06")
        self.app.refresh()
        self.app.filter_combo.set("2026-10-05")
        self.app._load_records()
        children = self.app.record_table.get_children()
        self.assertEqual(len(children), 1)
        self.assertEqual(self.app.record_table.item(children[0], "values")[0], "2026-10-05")

    def test_selecting_row_populates_edit_panel(self):
        rid = self.storage.insert_duel(1, 0, 1, note="oops", date="2026-10-05")
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.assertEqual(self.app.selected_id, rid)
        self.assertEqual(
            self.app.edit_selections, {"coin_win": 1, "went_first": 0, "duel_win": 1}
        )
        self.assertEqual(self.app.edit_note.get(), "oops")
        self.assertEqual(self.app.edit_date.get(), "2026-10-05")

    def test_clear_edit_resets_panel(self):
        rid = self.storage.insert_duel(1, 0, 1, note="oops", date="2026-10-05")
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.clear_edit()
        self.assertIsNone(self.app.selected_id)
        self.assertEqual(self.app.edit_note.get(), "")
        self.assertEqual(self.app.edit_date.get(), "")

    def test_enter_in_list_tab_does_not_save(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 1)
        self.app.select("duel_win", 1)
        self.app.notebook.select(3)
        self.app._on_return()
        self.assertEqual(len(self.storage.get_all()), 0)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_ui -v`
Expected: FAIL —— `AttributeError: 'TrackerApp' object has no attribute 'record_table'`

- [ ] **Step 3: 实现**

`ui.py` 常量区（`CHARTS` 之后）新增：

```python
COLUMNS = (
    ("date", "日期", 90),
    ("time", "时间", 60),
    ("coin", "硬币", 60),
    ("first", "先后手", 70),
    ("duel", "决斗", 60),
    ("note", "备注", 160),
)
```

在 `_build_ui` 的图表标签页（或 fallback 分支）之后、快捷键绑定之前：

```python
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

        self.record_table = ttk.Treeview(self.list_tab, columns=[c for c, _, _ in COLUMNS], show="headings")
        for col, heading, width in COLUMNS:
            self.record_table.heading(col, text=heading)
            self.record_table.column(col, width=width)
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
        self.selected_id = None
        self._records_by_id = {}
```

新增方法：

```python
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

    def clear_edit(self) -> None:
        self.selected_id = None
        self.edit_selections = {k: None for k in ("coin_win", "went_first", "duel_win")}
        for buttons in self._edit_buttons.values():
            for btn in buttons.values():
                btn.config(bg=self._default_bg)
        self.edit_note.delete(0, "end")
        self.edit_date.delete(0, "end")
```

改 `_on_return`：

```python
    def _on_return(self) -> None:
        if self.notebook.current() == self.notebook.index(self.list_tab):
            return
        self.save()
```

改 `refresh` —— 在图表绘制之后（函数末尾）追加：

```python
        dates = self.storage.get_dates()
        self.filter_combo["values"] = ["全部"] + dates
        if self.filter_combo.get() != "全部" and self.filter_combo.get() not in dates:
            self.filter_combo.set("全部")
        self._load_records()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests`
Expected: `Ran 62 tests ... OK`

- [ ] **Step 5: 提交**

```bash
git add ui.py tests/test_ui.py
git commit -m "Add record list tab with date filter and inline edit panel

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: ui 更新 / 删除 / 取消 与列表联动

**Files:**
- Modify: `ui.py`（新增 `update_selected`、`delete_selected`；`_build_ui` 中编辑面板的三个按钮）
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `Storage.update_duel(...) -> bool`、`Storage.delete_duel(...) -> bool`（Task 2）、`self.selected_id`、`self.edit_selections`、`self.edit_note`、`self.edit_date`、`self._records_by_id`、`show_message`（Task 3/4）
- Produces:
  - `update_selected(self) -> None`
  - `delete_selected(self) -> None`
  - `self.update_btn`、`self.delete_btn`、`self.cancel_btn`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_ui.py`：

```python
    def test_update_writes_back_and_refreshes_stats(self):
        rid = self.storage.insert_duel(1, 1, 1, date=datetime.now().strftime("%Y-%m-%d"))
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.edit_selections["coin_win"] = 0
        self.app.update_selected()
        self.assertEqual(self.storage.get_all()[0]["coin_win"], 0)
        self.assertIn("硬币 0赢/1输", self.app.today_label.cget("text"))

    def test_update_with_invalid_date_keeps_record(self):
        rid = self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.edit_date.delete(0, "end")
        self.app.edit_date.insert(0, "10/06/2026")
        self.app.update_selected()
        self.assertEqual(
            self.storage.get_all()[0]["date"], datetime.now().strftime("%Y-%m-%d")
        )
        self.assertIn("YYYY-MM-DD", self.app.message_label.cget("text"))

    def test_update_without_selection_does_nothing(self):
        self.app.update_selected()
        self.assertEqual(len(self.storage.get_all()), 0)

    def test_update_missing_record_reports_gone(self):
        rid = self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.storage.delete_duel(rid)  # 模拟选中记录已被外部删除
        self.app.update_selected()
        self.assertIn("已不存在", self.app.message_label.cget("text"))

    def test_delete_removes_row_and_clears_panel(self):
        rid = self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.delete_selected()
        self.assertEqual(self.storage.get_all(), [])
        self.assertIsNone(self.app.selected_id)
        self.assertEqual(self.app.update_btn.cget("state"), "disabled")

    def test_filter_resets_when_selected_date_has_no_records(self):
        rid = self.storage.insert_duel(1, 1, 1, date="2026-10-05")
        self.app.refresh()
        self.app.filter_combo.set("2026-10-05")
        self.app._load_records()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.delete_selected()
        self.assertEqual(self.app.filter_combo.get(), "全部")
        self.assertEqual(len(self.app.record_table.get_children()), 0)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_ui -v`
Expected: FAIL —— `AttributeError: 'TrackerApp' object has no attribute 'update_selected'`

- [ ] **Step 3: 实现**

在 `_build_ui` 的编辑面板（`self.edit_date.pack(side="left")` 之后）：

```python
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
```

在 `_on_row_select` 末尾（`self.edit_date.insert(0, record["date"])` 之后）：

```python
        self.update_btn.config(state="normal")
        self.delete_btn.config(state="normal")
```

在 `clear_edit` 末尾：

```python
        self.update_btn.config(state="disabled")
        self.delete_btn.config(state="disabled")
```

新增方法：

```python
    def update_selected(self) -> None:
        if self.selected_id is None:
            return
        if not all(v is not None for v in self.edit_selections.values()):
            self.show_message("请先选择硬币/先后手/决斗")
            return
        try:
            ok = self.storage.update_duel(
                self.selected_id,
                self.edit_selections["coin_win"],
                self.edit_selections["went_first"],
                self.edit_selections["duel_win"],
                self.edit_note.get().strip() or None,
                self.edit_date.get().strip(),
            )
        except ValueError:
            self.show_message("日期格式应为 YYYY-MM-DD")
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m unittest discover -s tests`
Expected: `Ran 68 tests ... OK`

- [ ] **Step 5: 手动冒烟**

Run: `python main.py`
Expected: 窗口打开；录入几条记录；切到「记录列表」，选中一行改硬币输赢并点「更新」，统计行立即变化；按 Ctrl+Z 撤销上一条；非法日期提示「日期格式应为 YYYY-MM-DD」。

- [ ] **Step 6: 提交**

```bash
git add ui.py tests/test_ui.py
git commit -m "Add inline update, delete and cancel for records

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Self-Review 结论

- **Spec 覆盖**：需求 1（撤销）→ Task 2/3；需求 2（列表+筛选）→ Task 1/4；需求 3（就地编辑）→ Task 2/5；需求 4（删除）→ Task 2/5；需求 5（补录日期）→ Task 1/3；需求 6（错误提示）→ Task 3/5；快捷键缺陷修复 → Task 3。
- **类型一致**：`get_records(date=None)`、`update_duel(duel_id, coin_win, went_first, duel_win, note, date)`、`delete_duel(duel_id)`、`delete_last()` 在各任务中签名一致。
- **无占位符**：每个步骤都给出可运行的代码与期望输出。
