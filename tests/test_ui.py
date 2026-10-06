# tests/test_ui.py
import os
import tempfile
import unittest
import tkinter as tk

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


if __name__ == "__main__":
    unittest.main()
