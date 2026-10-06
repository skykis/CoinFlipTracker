# tests/test_stats.py
import unittest

from stats import compute_stats, current_streak, longest_streak


def rec(coin_win, went_first, duel_win):
    return {"coin_win": coin_win, "went_first": went_first, "duel_win": duel_win}


class StatsTest(unittest.TestCase):
    def test_empty(self):
        s = compute_stats([])
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["coin_win_rate"], 0.0)
        self.assertEqual(s["coin_streak"], 0)
        self.assertEqual(s["coin_longest_win"], 0)

    def test_basic_counts_and_rates(self):
        records = [rec(1, 1, 1), rec(0, 0, 1), rec(1, 0, 0)]
        s = compute_stats(records)
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["coin_wins"], 2)
        self.assertEqual(s["coin_losses"], 1)
        self.assertAlmostEqual(s["coin_win_rate"], 2 / 3)
        self.assertEqual(s["first_count"], 1)
        self.assertEqual(s["second_count"], 2)
        self.assertAlmostEqual(s["first_share"], 1 / 3)
        self.assertEqual(s["duel_wins"], 2)
        self.assertAlmostEqual(s["duel_win_rate"], 2 / 3)

    def test_current_streak_single(self):
        self.assertEqual(current_streak([rec(1, 1, 1)], "coin_win"), 1)

    def test_current_streak_all_same(self):
        records = [rec(1, 1, 1), rec(1, 1, 0), rec(1, 0, 1)]
        self.assertEqual(current_streak(records, "coin_win"), 3)

    def test_current_streak_alternating(self):
        records = [rec(1, 1, 1), rec(0, 1, 1), rec(1, 0, 0)]
        self.assertEqual(current_streak(records, "coin_win"), 1)

    def test_longest_streak_spec_example(self):
        # WWLLW -> current streak 1, longest win streak 2
        records = [rec(1, 1, 1), rec(1, 1, 1), rec(0, 0, 0), rec(0, 0, 0), rec(1, 1, 1)]
        self.assertEqual(current_streak(records, "coin_win"), 1)
        self.assertEqual(longest_streak(records, "coin_win", 1), 2)
        self.assertEqual(longest_streak(records, "coin_win", 0), 2)

    def test_duel_streaks_independent_of_coin(self):
        records = [rec(1, 1, 0), rec(0, 1, 1), rec(1, 0, 1)]
        s = compute_stats(records)
        self.assertEqual(s["coin_streak"], 1)
        self.assertEqual(s["duel_streak"], 2)
        self.assertEqual(s["duel_longest_win"], 2)


if __name__ == "__main__":
    unittest.main()
