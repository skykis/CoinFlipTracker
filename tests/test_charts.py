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

    def test_daily_counts_title_says_duels(self):
        _, ax = fresh_axes()
        draw_daily_counts(ax, [{"date": "2026-10-06", "total": 3, "coin_wins": 1}])
        self.assertEqual(ax.get_title(), "每日局数")

    def test_daily_counts_ylabel_says_duels(self):
        _, ax = fresh_axes()
        draw_daily_counts(ax, [{"date": "2026-10-06", "total": 3, "coin_wins": 1}])
        self.assertEqual(ax.get_ylabel(), "局数")

    def test_daily_counts_y_ticks_are_whole_duels(self):
        # 局数是整数，默认刻度会为 total=1 选出 0.25、0.5 这类无意义的刻度
        _, ax = fresh_axes()
        draw_daily_counts(ax, [{"date": "2026-10-06", "total": 1, "coin_wins": 1}])
        ticks = list(ax.get_yticks())
        self.assertTrue(
            all(float(t).is_integer() for t in ticks),
            f"non-integer duel-count ticks: {ticks}",
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

    def test_per_duel_plots_cumulative_win_loss_balance(self):
        # 赢 +1，输 -1，累加成一条净胜分线
        records = [
            {"coin_win": 1, "duel_win": 0},
            {"coin_win": 0, "duel_win": 1},
            {"coin_win": 1, "duel_win": 1},
        ]
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        net = [line for line in ax.lines if len(line.get_ydata()) == 3]
        self.assertTrue(net, "no win-loss series plotted")
        self.assertEqual(list(net[0].get_ydata()), [1, 0, 1])

    def test_per_duel_win_loss_line_is_drawn_as_a_line(self):
        records = [{"coin_win": 1, "duel_win": 0}, {"coin_win": 0, "duel_win": 1}]
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        net = [line for line in ax.lines if len(line.get_ydata()) == 2]
        self.assertTrue(net, "no win-loss series plotted")
        self.assertNotEqual(net[0].get_linestyle(), "None", "net score should be a connected line")

    def test_per_duel_no_longer_plots_raw_win_loss_points(self):
        records = [{"coin_win": 1}, {"coin_win": 0}, {"coin_win": 1}]
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        for line in ax.lines:
            self.assertNotEqual(
                list(line.get_ydata()), [100, 0, 100],
                "raw 0/100 per-duel points should be replaced by the net score",
            )

    def test_per_duel_keeps_cumulative_rate_on_a_second_axis(self):
        fig, ax = fresh_axes()
        records = [{"coin_win": 1}, {"coin_win": 0}, {"coin_win": 1}]
        draw_per_duel(ax, records)
        self.assertEqual(len(fig.axes), 2, "expected a second y axis for the cumulative rate")
        rate_lines = [line for line in fig.axes[1].lines if len(line.get_ydata()) == 3]
        self.assertTrue(rate_lines, "no cumulative-rate series on the second axis")
        self.assertAlmostEqual(list(rate_lines[0].get_ydata())[1], 50.0)

    def test_per_duel_win_loss_axis_is_labelled_and_whole_numbered(self):
        records = [{"coin_win": 1}, {"coin_win": 0}, {"coin_win": 1}]
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        self.assertEqual(ax.get_ylabel(), "赢 − 输")
        ticks = list(ax.get_yticks())
        self.assertTrue(
            all(float(t).is_integer() for t in ticks),
            f"non-integer net-score ticks: {ticks}",
        )

    def test_per_duel_legend_names_the_win_loss_trend(self):
        records = [{"coin_win": 1}, {"coin_win": 0}, {"coin_win": 1}]
        _, ax = fresh_axes()
        draw_per_duel(ax, records)
        # ax.legend() 会重新生成图例并丢掉次轴的条目，必须读已有的图例
        legend_texts = [text.get_text() for text in ax.get_legend().get_texts()]
        self.assertIn("硬币输赢走势（赢 +1 / 输 -1）", legend_texts)
        self.assertIn("累计硬币胜率", legend_texts)


if __name__ == "__main__":
    unittest.main()
