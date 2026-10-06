# charts.py
from datetime import datetime

import matplotlib.dates as mdates
from matplotlib.figure import Figure


def build_figures(daily_counts):
    rate_fig = Figure(figsize=(8, 4))
    counts_fig = Figure(figsize=(8, 4))
    rate_ax = rate_fig.subplots()
    counts_ax = counts_fig.subplots()

    if not daily_counts:
        for ax in (rate_ax, counts_ax):
            ax.text(0.5, 0.5, "No data yet", ha="center", va="center")
            ax.axis("off")
        return [rate_fig, counts_fig]

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in daily_counts]
    rates = [d["coin_wins"] / d["total"] * 100 for d in daily_counts]
    totals = [d["total"] for d in daily_counts]

    rate_ax.plot(dates, rates, marker="o")
    rate_ax.axhline(50, linestyle="--", color="gray")
    rate_ax.set_ylabel("Coin win rate (%)")
    rate_ax.set_title("Daily coin win rate")

    counts_ax.bar(dates, totals)
    counts_ax.set_ylabel("Duels")
    counts_ax.set_title("Duels per day")

    for ax in (rate_ax, counts_ax):
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.tick_params(axis="x", rotation=45)

    return [rate_fig, counts_fig]
