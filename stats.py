# stats.py
def current_streak(records: list[dict], field: str) -> int:
    if not records:
        return 0
    streak = 1
    last = records[-1][field]
    for r in reversed(records[:-1]):
        if r[field] == last:
            streak += 1
        else:
            break
    return streak


def longest_streak(records: list[dict], field: str, value: int) -> int:
    best = 0
    run = 0
    for r in records:
        if r[field] == value:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def compute_stats(records: list[dict]) -> dict:
    total = len(records)
    coin_wins = sum(r["coin_win"] for r in records)
    first_count = sum(r["went_first"] for r in records)
    duel_wins = sum(r["duel_win"] for r in records)
    return {
        "total": total,
        "coin_wins": coin_wins,
        "coin_losses": total - coin_wins,
        "coin_win_rate": coin_wins / total if total else 0.0,
        "first_count": first_count,
        "second_count": total - first_count,
        "first_share": first_count / total if total else 0.0,
        "duel_wins": duel_wins,
        "duel_losses": total - duel_wins,
        "duel_win_rate": duel_wins / total if total else 0.0,
        "coin_streak": current_streak(records, "coin_win"),
        "coin_longest_win": longest_streak(records, "coin_win", 1),
        "coin_longest_loss": longest_streak(records, "coin_win", 0),
        "duel_streak": current_streak(records, "duel_win"),
        "duel_longest_win": longest_streak(records, "duel_win", 1),
        "duel_longest_loss": longest_streak(records, "duel_win", 0),
    }
