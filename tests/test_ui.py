# tests/test_ui.py
import os
import tempfile
import unittest
import tkinter as tk
from datetime import datetime

import ui
from storage import Storage
from ui import TrackerApp


class UITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(os.path.join(self.tmp.name, "duels.db"))
        self.root = tk.Tk()
        self.app = TrackerApp(self.storage, root=self.root)

    def tearDown(self):
        self.storage.close()
        try:
            self.root.destroy()
        except tk.TclError:
            pass  # already destroyed by run()
        self.tmp.cleanup()

    def test_incomplete_input_not_saved(self):
        self.app.select("coin_win", 1)
        self.assertFalse(self.app.can_save())
        self.assertIsNone(self.app.save())
        self.assertEqual(len(self.storage.get_all()), 0)

    def test_save_button_click_saves_record(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.assertTrue(self.app.save_btn.cget("state") == "normal")
        self.app.save_btn.invoke()
        self.assertEqual(len(self.storage.get_all()), 1)

    def test_note_field_is_labelled(self):
        self.assertIn("备注", self.app.note_label.cget("text"))

    def test_note_entry_cleared_after_save(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.app.note_entry.insert(0, "vs red deck")
        self.app.save()
        self.assertEqual(self.app.note_entry.get(), "")

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

    def test_note_recorded_when_provided(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)
        self.app.note_entry.insert(0, "vs red deck")
        rid = self.app.save()
        self.assertIsNotNone(rid)
        rec = self.storage.get_all()[0]
        self.assertEqual(rec["note"], "vs red deck")

    def test_buttons_reset_to_platform_default_background_after_save(self):
        fresh = tk.Button(self.root)
        default_bg = fresh.cget("bg")
        fresh.destroy()
        self.app.select("coin_win", 1)
        self.app.select("went_first", 1)
        self.app.select("duel_win", 1)
        self.app.save()
        for buttons in self.app._buttons.values():
            for btn in buttons.values():
                self.assertEqual(btn.cget("bg"), default_bg)

    def test_each_canvas_is_created_with_its_own_figure(self):
        self.assertEqual(len(self.app.figures), 3)
        for canvas, fig in zip(self.app.canvases, self.app.figures):
            self.assertIs(canvas.figure, fig)

    def test_refresh_reuses_figures_instead_of_replacing_them(self):
        # 替换 figure 会让渲染尺寸与 Tk PhotoImage 不一致，旧图残留在底部 → 坐标轴重复
        before = [canvas.figure for canvas in self.app.canvases]
        self.app.refresh()
        for canvas, fig in zip(self.app.canvases, before):
            self.assertIs(canvas.figure, fig)

    def test_chart_tabs_include_per_duel_chart(self):
        self.assertEqual(
            [self.app.notebook.tab(i, "text") for i in range(3)],
            ["硬币胜率趋势", "每日对数", "逐局趋势"],
        )
        self.assertEqual(len(self.app.canvases), 3)

    def test_matplotlib_missing_shows_fallback_tab(self):
        original = ui.MATPLOTLIB_OK
        ui.MATPLOTLIB_OK = False
        try:
            root = tk.Tk()
            try:
                app = TrackerApp(self.storage, root=root)
                self.assertEqual(app.notebook.tab(0, "text"), "图表")
                self.assertFalse(hasattr(app, "canvases"))
                self.assertIn("matplotlib", app.fallback_label.cget("text"))
            finally:
                root.destroy()
        finally:
            ui.MATPLOTLIB_OK = original

    def test_run_survives_window_closed_by_user(self):
        original = tk.Tk.mainloop
        def fake_mainloop(root):
            root.destroy()  # user closes the window: Tk tears down the app
        tk.Tk.mainloop = fake_mainloop
        try:
            self.app.run()
        finally:
            tk.Tk.mainloop = original

    def test_run_destroys_root_when_mainloop_ends(self):
        original = tk.Tk.mainloop
        tk.Tk.mainloop = lambda self: None
        try:
            self.app.run()
        finally:
            tk.Tk.mainloop = original
        try:
            self.app.root.winfo_exists()
        except tk.TclError:
            pass  # root destroyed
        else:
            self.fail("Tk root still alive after run()")

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
        self.app.date_entry.insert(0, "2026-13-40")
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
        # Tk focus is per-interpreter: after another Tk root in the same process
        # is destroyed, focus_get() returns None, so focus_get is stubbed while
        # the real _entry_has_focus predicate still runs.
        probe = tk.Entry(self.root)
        self.root.focus_get = lambda: probe
        self.app._shortcut("coin_win", 1)
        self.assertIsNone(self.app.selections["coin_win"])

    def test_shortcut_works_when_no_entry_has_focus(self):
        self.root.focus_get = lambda: None
        self.app._shortcut("coin_win", 1)
        self.assertEqual(self.app.selections["coin_win"], 1)

    def test_stats_display_streak_direction_and_all_fields(self):
        # coin: win, win -> streak 2 wins; duel: win, loss -> streak 1 loss
        self.storage.insert_duel(1, 1, 1)
        self.storage.insert_duel(1, 0, 0)
        self.app.refresh()
        label = self.app.today_label.cget("text")
        self.assertIn("连串 2赢", label)
        self.assertIn("连串 1输", label)
        self.assertIn("后手 1", label)
        self.assertIn("最长 1/1", label)

    def test_record_list_is_the_last_tab(self):
        # 不依赖 matplotlib 是否安装：图表标签页数量可变，记录列表始终是最后一个
        # notebook.size() 返回网格尺寸，不是标签页数量 —— 用 tabs()
        tabs = [
            self.app.notebook.tab(i, "text")
            for i in range(len(self.app.notebook.tabs()))
        ]
        self.assertEqual(tabs[-1], "记录列表")

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

    def test_ctrl_z_is_bound_to_undo(self):
        # Tk 只在进程内的第一个 root 上派发生成事件，所以绑定本身单独检查，
        # 行为由 _undo_by_shortcut 的测试验证。
        self.assertIn("<lambda>", self.root.bind("<Control-z>"))

    def test_ctrl_z_undoes_last_record(self):
        self.storage.insert_duel(1, 1, 1)
        self.storage.insert_duel(0, 0, 0)
        self.app.refresh()
        self.app._undo_by_shortcut()
        self.assertEqual(len(self.storage.get_all()), 1)
        self.assertIn("撤销", self.app.message_label.cget("text"))

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

    def test_ctrl_z_ignored_when_text_field_has_focus(self):
        self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        probe = tk.Entry(self.root)
        self.root.focus_get = lambda: probe
        self.app._undo_by_shortcut()
        self.assertEqual(len(self.storage.get_all()), 1)

    def test_undo_button_works_while_text_field_has_focus(self):
        self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        probe = tk.Entry(self.root)
        self.root.focus_get = lambda: probe
        self.app.undo_btn.invoke()
        self.assertEqual(len(self.storage.get_all()), 0)

    def test_ctrl_z_repeated_undoes_multiple_records(self):
        self.storage.insert_duel(1, 1, 1)
        self.storage.insert_duel(0, 0, 0)
        self.storage.insert_duel(1, 0, 1)
        self.app.refresh()
        self.app._undo_by_shortcut()
        self.app._undo_by_shortcut()
        self.assertEqual(len(self.storage.get_all()), 1)

    def test_edit_panel_cleared_when_selected_row_deleted(self):
        rid = self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.storage.delete_duel(rid)
        self.app.refresh()
        self.assertIsNone(self.app.selected_id)
        self.assertEqual(self.app.update_btn.cget("state"), "disabled")

    def test_edit_panel_cleared_when_filter_excludes_selected_row(self):
        rid = self.storage.insert_duel(1, 1, 1, date="2026-10-05")
        self.storage.insert_duel(0, 0, 0, date="2026-10-06")
        self.app.refresh()
        self.app.filter_combo.set("2026-10-05")
        self.app._load_records()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.filter_combo.set("2026-10-06")
        self.app._load_records()
        self.assertIsNone(self.app.selected_id)
        self.assertEqual(self.app.update_btn.cget("state"), "disabled")

    def test_cancel_clears_row_selection(self):
        rid = self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.clear_edit()
        self.assertEqual(self.app.record_table.selection(), ())

    def test_record_list_has_scrollbar(self):
        self.assertTrue(hasattr(self.app, "record_scrollbar"))
        self.assertTrue(self.app.record_table.cget("yscrollcommand"))

    def test_delete_without_selection_does_nothing(self):
        self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.delete_selected()
        self.assertEqual(len(self.storage.get_all()), 1)
        self.assertEqual(self.app.message_label.cget("text"), "")

    def test_update_with_blank_date_is_rejected(self):
        rid = self.storage.insert_duel(1, 1, 1, date="2026-10-05")
        self.app.refresh()
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.edit_date.delete(0, "end")
        self.app.update_selected()
        self.assertEqual(self.storage.get_all()[0]["date"], "2026-10-05")
        self.assertIn("留空", self.app.message_label.cget("text"))

    def test_enter_in_list_tab_updates_selected_record(self):
        rid = self.storage.insert_duel(1, 1, 1)
        self.app.refresh()
        self.app.notebook.select(3)
        self.app.record_table.selection_set(str(rid))
        self.app._on_row_select()
        self.app.edit_selections["coin_win"] = 0
        self.app._on_return()
        self.assertEqual(self.storage.get_all()[0]["coin_win"], 0)

    def test_save_reports_unexpected_value_error_generically(self):
        self.app.select("coin_win", 1)
        self.app.select("went_first", 0)
        self.app.select("duel_win", 1)

        def boom(*args, **kwargs):
            raise ValueError("unexpected failure")

        self.storage.insert_duel = boom
        self.assertIsNone(self.app.save())
        message = self.app.message_label.cget("text")
        self.assertIn("unexpected failure", message)
        self.assertNotIn("YYYY-MM-DD", message)

    def test_default_bg_is_the_platform_default(self):
        fresh = tk.Button(self.root)
        default_bg = fresh.cget("bg")
        fresh.destroy()
        self.assertEqual(self.app._default_bg, default_bg)


if __name__ == "__main__":
    unittest.main()
