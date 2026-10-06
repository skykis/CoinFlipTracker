# tests/test_charts.py
import unittest

from matplotlib.colors import to_rgba
from matplotlib.figure import Figure

import theme
from charts import draw_coin_rate, draw_daily_counts, draw_per_duel


def fresh_axes():
    """每个图表都绘制到一个独立的 Figure 的 Axes 上。"""
    fig = Figure(figsize=(8, 4))
    return fig, fig.subplots()


class ChartsTest(unittest.TestCase):
    def test_empty_coin_rate_shows_placeholder(self):
        _, ax = fresh_axes()
        draw_coin_rate(ax, [])
        self.assertIn("暂无数据", [t.get_text() for t in ax.texts])

    def test_empty_daily_counts_shows_placeholder(self):
        _, ax = fresh_axes()
        draw_daily_counts(ax, [])
        self.assertIn("暂无数据", [t.get_text() for t in ax.texts])

    def test_empty_per_duel_shows_placeholder(self):
        _, ax = fresh_axes()
        draw_per_duel(ax, [])
        self.assertIn("暂无数据", [t.get_text() for t in ax.texts])

    def test_coin_rate_plots_daily_rates(self):
        daily = [
            {"date": "2026-10-05", "total": 4, "coin_wins": 2},
            {"date": "2026-10-06", "total": 4, "coin_wins": 4},
        ]
        _, ax = fresh_axes()
        draw_coin_rate(ax, daily)
        series = [line for line in ax.lines if len(line.get_ydata()) == 2]
        self.assertTrue(series, "no coin-rate series plotted")
        self.assertEqual(list(series[0].get_ydata()), [50.0, 100.0])

    def test_x_labels_are_unique_for_few_days(self):
        daily = [
            {"date": f"2026-10-{d:02d}", "total": 2, "coin_wins": 1}
            for d in (1, 2, 3)
        ]
        for draw in (draw_coin_rate, draw_daily_counts):
            _, ax = fresh_axes()
            draw(ax, daily)
            labels = [l.get_text() for l in ax.get_xticklabels()]
            self.assertEqual(
                len(labels), len(set(labels)), f"duplicate labels: {labels}"
            )

    def test_x_labels_are_unique_when_spanning_years(self):
        daily = [
            {"date": f"{year}-10-01", "total": 2, "coin_wins": 1}
            for year in (2024, 2025, 2026)
        ]
        for draw in (draw_coin_rate, draw_daily_counts):
            _, ax = fresh_axes()
            draw(ax, daily)
            labels = [l.get_text() for l in ax.get_xticklabels()]
            self.assertEqual(
                len(labels), len(set(labels)), f"duplicate labels: {labels}"
            )
            self.assertTrue(any(len(l) == 10 for l in labels), f"year missing: {labels}")

    def test_many_days_use_dates_and_rotated_labels(self):
        daily = [
            {"date": f"2026-09-{d:02d}", "total": 2, "coin_wins": 1}
            for d in range(1, 31)
        ]
        for draw in (draw_coin_rate, draw_daily_counts):
            _, ax = fresh_axes()
            draw(ax, daily)
            labels = ax.get_xticklabels()
            self.assertTrue(labels)
            self.assertEqual(labels[0].get_rotation(), 45)

    def test_per_duel_x_ticks_are_whole_duel_numbers(self):
        records = [{"coin_win": 1, "duel_win": 0}] * 4
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        ticks = list(ax.get_xticks())
        self.assertTrue(
            all(float(t).is_integer() for t in ticks),
            f"non-integer duel ticks: {ticks}",
        )

    def test_axes_use_the_light_palette(self):
        _, ax = fresh_axes()
        draw_coin_rate(ax, [{"date": "2026-10-06", "total": 1, "coin_wins": 1}])
        gridlines = ax.get_xgridlines() + ax.get_ygridlines()
        self.assertEqual(ax.get_facecolor(), to_rgba(theme.CARD))
        self.assertTrue(gridlines, "grid lines should exist")
        self.assertTrue(all(g.get_visible() for g in gridlines), "grid lines should be visible")
        self.assertEqual(gridlines[0].get_color(), theme.GRID)
        self.assertEqual(ax.get_title(), "每日硬币胜率趋势")

    def test_per_duel_chart_plots_each_duel_result(self):
        records = [
            {"coin_win": 1, "duel_win": 0},
            {"coin_win": 0, "duel_win": 1},
            {"coin_win": 1, "duel_win": 1},
        ]
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        per_duel = [line for line in ax.lines if len(line.get_ydata()) == 3]
        self.assertTrue(per_duel, "no per-duel series plotted")
        self.assertEqual(list(per_duel[0].get_ydata()), [100, 0, 100])


if __name__ == "__main__":
    unittest.main()
