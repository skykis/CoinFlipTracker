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

    def test_many_days_use_dates_and_rotated_labels(self):
        daily = [
            {"date": f"2026-09-{d:02d}", "total": 2, "coin_wins": 1}
            for d in range(1, 31)
        ]
        figures = build_figures(daily)
        for fig in figures:
            ax = fig.axes[0]
            labels = ax.get_xticklabels()
            self.assertTrue(labels)
            self.assertEqual(labels[0].get_rotation(), 45)


if __name__ == "__main__":
    unittest.main()
