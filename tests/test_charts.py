# tests/test_charts.py
import unittest

from matplotlib.figure import Figure

from charts import build_figures


class ChartsTest(unittest.TestCase):
    def test_empty_returns_placeholder_figures(self):
        figures = build_figures([], [])
        self.assertEqual(len(figures), 3)
        for fig in figures:
            self.assertIsInstance(fig, Figure)

    def test_empty_placeholder_text_is_chinese(self):
        figures = build_figures([], [])
        for fig in figures:
            texts = [t.get_text() for t in fig.axes[0].texts]
            self.assertIn("暂无数据", texts)

    def test_with_data_returns_figures(self):
        daily = [
            {"date": "2026-10-05", "total": 3, "coin_wins": 2},
            {"date": "2026-10-06", "total": 4, "coin_wins": 1},
        ]
        records = [
            {"coin_win": 1, "duel_win": 1},
            {"coin_win": 0, "duel_win": 0},
        ]
        figures = build_figures(daily, records)
        self.assertEqual(len(figures), 3)
        for fig in figures:
            self.assertIsInstance(fig, Figure)

    def test_x_labels_are_unique_for_few_days(self):
        daily = [
            {"date": f"2026-10-{d:02d}", "total": 2, "coin_wins": 1}
            for d in (1, 2, 3)
        ]
        for fig in build_figures(daily, []):
            labels = [l.get_text() for l in fig.axes[0].get_xticklabels()]
            self.assertEqual(len(labels), len(set(labels)), f"duplicate labels: {labels}")

    def test_x_labels_are_unique_when_spanning_years(self):
        daily = [
            {"date": f"{year}-10-01", "total": 2, "coin_wins": 1}
            for year in (2024, 2025, 2026)
        ]
        # 前两个图是日期轴图表；第三个图（逐局）的 x 轴是局数
        for fig in build_figures(daily, [])[:2]:
            labels = [l.get_text() for l in fig.axes[0].get_xticklabels()]
            self.assertEqual(len(labels), len(set(labels)), f"duplicate labels: {labels}")
            self.assertTrue(any(len(l) == 10 for l in labels), f"year missing: {labels}")

    def test_per_duel_chart_plots_each_duel_result(self):
        records = [
            {"coin_win": 1, "duel_win": 0},
            {"coin_win": 0, "duel_win": 1},
            {"coin_win": 1, "duel_win": 1},
        ]
        fig = build_figures([], records)[2]
        ax = fig.axes[0]
        per_duel = [l for l in ax.lines if len(l.get_ydata()) == 3]
        self.assertTrue(per_duel, "no per-duel series plotted")
        self.assertEqual(list(per_duel[0].get_ydata()), [100, 0, 100])

    def test_many_days_use_dates_and_rotated_labels(self):
        daily = [
            {"date": f"2026-09-{d:02d}", "total": 2, "coin_wins": 1}
            for d in range(1, 31)
        ]
        figures = build_figures(daily, [])
        for fig in figures[:2]:
            ax = fig.axes[0]
            labels = ax.get_xticklabels()
            self.assertTrue(labels)
            self.assertEqual(labels[0].get_rotation(), 45)


if __name__ == "__main__":
    unittest.main()
